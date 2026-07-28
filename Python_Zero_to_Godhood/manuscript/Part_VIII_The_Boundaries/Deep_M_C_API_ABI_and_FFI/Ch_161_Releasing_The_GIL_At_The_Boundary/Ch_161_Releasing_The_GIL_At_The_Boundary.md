# Chapter 80: Releasing the GIL at the Boundary

A C function that sorts an array, hashes a buffer, or waits on a socket does not touch a single Python object.
Nothing it does requires the Global Interpreter Lock, and if the caller **releases** the GIL for the duration of the call, every other Python thread keeps running while it works.
If the caller holds the GIL, the entire interpreter is stopped for the length of that call.

This is the single most important property of the C boundary, and it is why threads are the right tool for hashing, compression, and I/O in CPython even in a build that still has a GIL.
It is not a subtle heuristic. Measured here: the same C sleep in four threads takes **as long as one** when the GIL is released and **four times as long** when it is held, and `hashlib.sha256` over 64 MB scales **3.6x** across four threads while the equivalent pure-Python loop scales **1.0x**, which is the definition of no parallelism at all.

In `ctypes` the choice is not a convention or a documentation note. It is **one bit** in the function's flags.

**This is a Deep M boundary chapter.**
It is about who releases the GIL, how you can tell, what it buys, and the three ways getting it wrong crashes rather than merely slows.

## Section index

- **80.1** One flag bit, and an observation that proves it
- **80.2** The rule, the exception, and the failure modes
- **80.3** Measurement: what the release is worth in threads
- **80.4** Edges and failure modes
- **80.5** Connections
- **80.6** Exercises
- **80.7** Summary and cross-references

Listings live under `code/ch161/` and are re-executed by `make verify` on both verification interpreters.

---

## 80.1 One flag bit, and an observation that proves it

```python
# code/ch161/l01_releasing_the_gil.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the choice is one flag bit, not a convention ---
  _FUNCFLAG_PYTHONAPI (hold the GIL)  : 4
  CDLL        flags=1  ->  releases it for the call
  PyDLL       flags=5  ->  holds the GIL for the call
  CFUNCTYPE   flags=1  ->  acquires the GIL on entry
  PYFUNCTYPE  flags=5  ->  assumes the GIL is held
  ctypes.pythonapi is a PyDLL         : True
--- observation: does another thread run while C runs? ---
  CDLL  : main thread ran during the C call : True
  PyDLL : main thread ran during the C call : False
  both eventually executed Python           : True
```

**The bit.**
`ctypes._FUNCFLAG_PYTHONAPI` is `0x4`, and it means "this call reaches into the CPython C-API, so do not release the GIL". `ctypes.CDLL` has flags `1`; `ctypes.PyDLL` has flags `5`, which is `1 | 4`. That is the whole distinction between the two loaders, and it explains why `ctypes.pythonapi`, the handle on CPython's own C functions from Chapter 45, is a `PyDLL`: those functions manipulate `PyObject*`, so calling them without the GIL would be a data race on refcounts.

The same bit governs callbacks. A `CFUNCTYPE` callback is entered *from C*, possibly on a thread that does not hold the GIL, so it acquires the GIL on entry and releases it on return. A `PYFUNCTYPE` callback assumes the GIL is already held, which is correct only when the C code calling it was itself invoked through a `PyDLL`.

**The observation.**
Flags are a claim; the second block is the check. A worker thread spends 300 milliseconds inside `usleep`, and the main thread tries to execute Python during that window. Under `CDLL` it does, and the whole sequence finishes in about 100 ms. Under `PyDLL` it cannot execute a single bytecode until the C call returns, and the same sequence takes about 400 ms. The listing reports booleans against a threshold at the midpoint of those two outcomes, so the result is stable while the underlying quantity is a wall-clock time; §80.3 reports the times.

**The senior-engineer contrast.**
In a Java or Go program this question does not arise: there is no global lock to drop, and a blocking syscall parks a thread or a goroutine without stopping anything else. CPython's model is closer to a cooperative runtime with one big lock, where every native call must decide, explicitly, whether it is safe to let the world run. The upside of the explicitness is that you can see the decision, in a flag, in a loader class, in a `Py_BEGIN_ALLOW_THREADS` macro. The downside is that the decision is *per call site* and getting it wrong is silent in one direction and fatal in the other.

---

## 80.2 The rule, the exception, and the failure modes

**The rule.**
Release the GIL for any C call that does not touch Python objects. In a hand-written extension that is the `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` pair around the C work; in `ctypes` it is the default and you get it by not asking for `PyDLL`.

**The exception, stated precisely.**
Hold the GIL when the C code will call into the CPython C-API: create, inspect, or destroy a `PyObject`, raise a Python exception, or invoke a Python callable. Refcounts are not atomic in the default build, so a refcount incremented without the GIL is a corrupted refcount, and a corrupted refcount is either a leak or a use-after-free, discovered much later and somewhere else.

**What the standard library does.**
This is not a `ctypes` peculiarity. `hashlib` releases the GIL around its digest loop for buffers above a small threshold; `zlib` and the compression modules release it around compress and decompress; the `io` layer and `socket` release it around the syscall; `time.sleep` releases it, which is why a sleeping thread does not stop the process. The pattern is uniform: the C code that does not need Python drops the lock, and everything that does not drop it is a place where your threads will serialise.

**The three failure modes, in increasing order of how much they hurt.**

- **Holding when you could release.** The program is correct and does not scale. This is the invisible one: nothing crashes, and the four-thread version simply takes four times as long as it should. §80.3's `PyDLL` row is exactly this failure, staged.
- **Releasing while touching Python objects.** Two threads mutate refcounts concurrently. In the default build this is a data race with no diagnostic; it manifests as a segfault or a wrong refcount hours later. This is why the safe default in a hand-written extension is to keep the release window as small and as obviously object-free as possible.
- **Calling back into Python from a released-GIL context without reacquiring.** A C library that invokes a callback from a worker thread must acquire the GIL with `PyGILState_Ensure` before touching anything Python. `CFUNCTYPE` does this for you; a hand-written extension does not get it for free. Chapter 44's `qsort` comparator is the version of this that `ctypes` handles correctly and slowly.

**Where the boundary interacts with the rest of the volume.**
Chapter 43 measured the per-call cost of the boundary and concluded: cross once, with the whole buffer. This chapter adds the reason that advice compounds. A single call over a whole buffer is not merely cheaper than a million small calls; it is also the shape that can release the GIL for a long, useful window. A million tiny calls each release and reacquire the GIL, which is overhead with no parallelism to show for it. **One big call over a `memoryview` (Chapter 79), with the GIL released, is the shape that gets both properties at once**, and it is the shape the seam with **Book I** uses.

---

## 80.3 Measurement: what the release is worth in threads

**Methodology.** `code/ch161/bench_gil_release.py`.
Each row does one unit of work in one thread, then one unit in each of four threads, and reports `(1-thread time x 4) / 4-thread time`. 4.00x is perfect scaling; 1.00x is complete serialisation. Wall-clock threading measurements are noisier than the microbenchmarks elsewhere in this book, so each configuration is the minimum of 7 runs.
CPython 3.13.5, Apple M3 Pro, macOS 27.0 (12 cores), arm64.

| case | 1 thread | 4 threads | speedup |
|---|---|---|---|
| C sleep via `CDLL` (GIL released) | 101 ms | 105 ms | **3.9x** |
| C sleep via `PyDLL` (GIL held) | 103 ms | 419 ms | **1.0x** |
| `sha256` over 64 MB (GIL released) | 22 ms | 24 ms | **3.6x** |
| pure-Python loop (GIL held) | 52 ms | 205 ms | **1.0x** |

**The first two rows are the same C function.**
The identical `usleep(100000)`, called through two loaders that differ in one flag bit. Released: four threads finish in the time one takes, a 3.9x speedup and within 4% of perfect. Held: four threads take four times as long, 1.0x, no parallelism whatsoever. Nothing about the C code changed. This is as clean an isolation of a single variable as this book contains.

**`sha256` is the same result inside the standard library.**
64 MB hashed four times in four threads takes 24 ms against 22 ms for one, a 3.6x speedup. `hashlib` releases the GIL around its digest loop, and the consequence is that CPython threads give real parallel throughput on hashing today, in a GIL build, with no special measures. The same holds for `zlib`, for file and socket I/O, and for any well-written extension.

The 3.6x rather than 3.9x is worth naming rather than rounding away: hashing is memory-bandwidth-bound at this size, four threads compete for the same bandwidth, and that ceiling is real physics rather than a GIL artifact. A speedup below the thread count is not automatically evidence of lock contention.

**The last row is the control.**
The same shape of work with no C boundary at all. Four threads take four times as long as one. The GIL is doing exactly what it is designed to do, and no amount of threading helps, which is the result that sends CPU-bound Python work to `multiprocessing` (Deep E), to a C extension (this volume), or to a free-threaded build (Deep L).

**The conclusion in one sentence.**
Threads in CPython are not a general parallelism mechanism; they are a mechanism for overlapping **time spent outside the interpreter**, and the C boundary is where you decide how much time that is.

---

## 80.4 Edges and failure modes

**`PyDLL` is not a performance choice, it is a correctness requirement.** §80.2.
Use it when the C function touches the CPython C-API, and never otherwise. Reaching for it to "be safe" converts a scaling program into a serialised one, silently.

**Releasing the GIL does not make your data thread-safe.**
It makes other Python threads run. If two threads pass overlapping `memoryview`s of the same buffer to a C function that writes into them, the release is precisely what lets them race. The export count of Chapter 79 protects the buffer's *address*, not its contents.

**The released window must not touch Python objects, including implicitly.**
Reading a `PyObject*` field, calling `Py_DECREF`, raising an exception, or logging through a Python logger inside a released window is a data race in the default build. In a free-threaded build (Deep L) refcounts are atomic, which changes the failure mode but not the requirement.

**A callback re-crosses the boundary and re-acquires the lock.** §80.2.
`qsort` with a Python comparator (Chapter 44) pays a GIL acquisition per comparison, which is why it is slower than sorting in Python. If the C library you are calling takes a callback that fires per element, the parallelism you gained by releasing is spent reacquiring.

**Short calls are not worth releasing.**
Releasing and reacquiring the GIL costs on the order of a hundred nanoseconds. For a C call that takes less than that, the release is pure loss; this is why `hashlib` applies a size threshold rather than releasing unconditionally, and why per-element FFI calls should not be redesigned around the GIL.

**Speedup below the thread count is not always the GIL.** §80.3.
Memory bandwidth, hyperthreading, thermal limits, and the machine's other work all cap scaling. Diagnose with a control row that is known to scale, as this benchmark does, before blaming a lock.

**`time.sleep` releases the GIL, `usleep` through `PyDLL` does not.**
A surprising amount of code busy-waits or sleeps through an FFI call. If a "sleep" in your program stops the whole interpreter, this flag bit is where to look.

---

## 80.5 Connections

**Backward.**
The per-call cost of the FFI boundary, and the cross-once argument this chapter compounds, is Chapter 43. Whole-buffer calls are Chapter 44. `ctypes.pythonapi` as a `PyDLL`, and why it must be one, is Chapter 45. The `memoryview` that makes a long single call possible without copying is Chapter 79. The GIL itself, threads, and the switch interval are Deep E.

**Forward.**
Reference counting across the boundary, which is *why* the C-API case must hold the lock, is Chapter 81. The stable ABI, which constrains what an extension may call, is Chapter 82. Compiled extensions and where they put their release windows are Chapter 83. Free-threading, which makes refcounts atomic and changes this chapter's exception clause without removing it, is Deep L. Process-based parallelism, the answer when there is no C boundary to release at, is Deep E.

**Across books.**
This is the property that makes the two-book split pay off at runtime rather than only in source. **Book I**'s matching engine is entered once per batch with the GIL released, so while it runs the Python side continues to parse the next frames off the tick buffer. The seam is designed for exactly the shape §80.3's first row measures: a long C call, no Python objects touched, the whole interpreter free for its duration.

---

## 80.6 Exercises

**1. Find the bit.** Reproduce §80.1's first block. Then check the flags on `ctypes.pythonapi` and explain, from Chapter 45, why it must hold the GIL.

**2. Stage the failure.** Reproduce §80.3's first two rows on your machine. Then change the sleep duration to 1 ms and re-measure. Explain why the `CDLL` advantage shrinks, and estimate the call duration below which releasing is not worth it.

**3. Find a scaling library call.** Measure the four-thread speedup of `zlib.compress`, `hashlib.sha256`, and `json.dumps` over the same input size. Predict which scale before measuring, and explain any surprise from where the C work is.

**4. The bandwidth ceiling.** Reproduce the `sha256` row at 1 MB, 8 MB, and 64 MB per thread. Explain why the speedup changes with the buffer size, and argue whether the limit at 64 MB is the GIL or the memory system.

**5. The callback tax.** Sort an array with `libc.qsort` and a Python comparator, and with `list.sort`. Explain the result in terms of GIL acquisitions per comparison, and say what shape of C API avoids the problem.

**6. The design question.** CPython could release the GIL automatically around any C call whose extension declares itself object-free, rather than requiring the extension author to bracket it. Argue why the decision is left to the author: what the runtime would have to prove, what a wrong declaration costs, and how free-threading (PEP 703) changes the calculus without removing the need for the declaration.

---

## 80.7 Summary and cross-references

- A C call that touches no Python objects does not need the GIL. **Releasing it lets every other Python thread run for the duration of the call**; holding it stops the interpreter.
- In `ctypes` the choice is **one flag bit**: `_FUNCFLAG_PYTHONAPI` (`0x4`). `CDLL` has flags `1` and releases; `PyDLL` has flags `5` and holds. `CFUNCTYPE` callbacks **acquire** the GIL on entry; `PYFUNCTYPE` callbacks assume it is held. `ctypes.pythonapi` is a `PyDLL` because C-API functions manipulate `PyObject*`.
- **Measured on 3.13.5, 4 threads on 12 cores:** the same C sleep scales **3.9x** through `CDLL` and **1.0x** through `PyDLL`; `hashlib.sha256` over 64 MB scales **3.6x**; the pure-Python control scales **1.0x**. One flag bit, four times the throughput.
- **The rule:** release for C work that does not touch Python objects. **The exception:** hold when the C code calls the CPython C-API, because refcounts are not atomic in the default build.
- **Three failure modes:** holding when you could release (correct, does not scale, invisible); releasing while touching objects (a refcount data race, fatal and delayed); calling back into Python from a released context without reacquiring (`CFUNCTYPE` handles it, hand-written extensions do not get it free).
- **Compounding with Chapter 43:** cross the boundary once with the whole buffer, *and* release the GIL for that one long call. A million small calls pay the release overhead with no parallelism to show for it.
- **Edges:** the release does not make data thread-safe; short calls are not worth releasing (hence `hashlib`'s size threshold); a speedup below the thread count may be memory bandwidth rather than a lock; threads in CPython overlap time spent *outside* the interpreter and nothing else.

**Cross-references.** FFI per-call cost → Chapter 43. Whole-buffer calls → Chapter 44. `ctypes.pythonapi` → Chapter 45. `memoryview` → Chapter 79. Refcounts across the boundary → Chapter 81. The stable ABI → Chapter 82. Compiled extensions → Chapter 83. The GIL, threads, and the switch interval → Deep E. Free-threading → Deep L.
