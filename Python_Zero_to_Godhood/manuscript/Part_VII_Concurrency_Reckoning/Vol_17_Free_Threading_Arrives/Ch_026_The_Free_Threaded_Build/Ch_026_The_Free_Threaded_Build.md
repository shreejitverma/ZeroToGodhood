# Chapter 26: The Free-Threaded Build (Python 3.13-3.14)

Every concurrency chapter in this book so far has been shaped by one constraint. Chapter 8 measured
that four threads give no CPU speedup because of the GIL. Chapter 23 routed around it with
subinterpreters, each with its own GIL. Chapter 8's escape hatch was processes, paying a serialization
tax. All of these are workarounds for a lock that has been part of CPython since the beginning, and the
free-threaded build is the first serious attempt to remove it rather than route around it.

**PEP 703** introduced a *separate build* of CPython in which the GIL is gone, replaced by fine-grained
per-object locking and biased reference counting. In that build, `read(o)` across four threads gives
real CPU parallelism with *shared memory*, the one thing subinterpreters cannot offer. **PEP 779**
(Python 3.14) moved this build from experimental to *officially supported but still optional*. It is the
largest change in CPython's history, it is happening incrementally in public, and its failure modes are
visible. This chapter introduces the model and states honestly what this book can and cannot verify
about it.

> **A candor note this chapter is obligated to make.** The free-threaded interpreter is a *separate
> build* (`python3.14t`), and it is not installed on this book's verification machine. Every claim in
> this chapter that could be checked by running code, the detection API, the immortal-object
> foundation, is verified on the ordinary build and shown. Every claim about the free-threaded build's
> *performance*, its single-threaded overhead and its multi-threaded speedup, is **cited to the CPython
> team's published figures and PEP 779, not measured here**, and is tracked in the book's verification
> queue. When a `python3.14t` build is added to the verification matrix, this chapter's numbers become
> measured; until then they are labeled as cited. The canonical, fully-measured treatment is **Deep L**.

## Section index

- **26.1** The problem: one lock, forty years
- **26.2** What the free-threaded build changes
- **26.3** Detecting the build, and the immortal-object foundation
- **26.4** The performance trade (cited)
- **26.5** The rollout, and what it means for your code
- **26.6** Edges and failure modes
- **26.7** Connections
- **26.8** Exercises
- **26.9** Summary and cross-references

The listing lives under `code/ch026/` and is re-executed by `make verify` on both interpreters (both
are ordinary, GIL-enabled builds).

---

## 26.1 The problem: one lock, forty years

The GIL exists (Chapter 8) because CPython's reference counting needs it: without a global lock, every
`INCREF`/`DECREF` on a shared object would need to be atomic or individually locked, and every object
operation touches a refcount (Chapter 19). The GIL buys single-threaded speed and implementation
simplicity by serializing all bytecode execution. The cost is the recurring theme of this book's
concurrency chapters: threads cannot parallelize CPU work.

Removing the GIL is not a matter of deleting a lock. It means making every one of those refcount
operations safe under concurrency, making the memory allocator thread-safe, making dict and list
mutation safe, and doing all of it without wrecking single-threaded performance, which is what the vast
majority of Python code cares about. That is why it took the better part of a decade and a from-scratch
implementation (the "nogil" fork that became PEP 703), and why it ships as a separate build rather than
flipping a switch.

---

## 26.2 What the free-threaded build changes

The free-threaded build replaces the single global lock with several mechanisms working together. The
central one is **biased reference counting**: the common case, an object touched only by the thread
that created it, uses a fast non-atomic refcount owned by that thread, while cross-thread references use
a separate atomic count. Most objects are never shared across threads, so most refcount operations stay
fast; only genuinely shared objects pay the atomic cost. Alongside it, **immortal objects** (PEP 683,
Chapter 19) remove refcounting entirely from the objects every thread touches constantly (`None`,
`True`, small integers, interned strings), so those never contend. And the containers gain fine-grained
per-object locks so two threads can mutate different dicts without serializing.

The result is the one capability no other model in this book provides: **CPU parallelism with shared
mutable memory**. Threads in the free-threaded build run bytecode simultaneously *and* see each other's
objects, so a parallel algorithm over a large shared data structure, which subinterpreters (Chapter 23)
would have to copy or message-pass, runs in place. That is the payoff, and §26.4 states its cost.

---

## 26.3 Detecting the build, and the immortal-object foundation

You can tell which build you are running, and see the foundation the free-threaded build stands on,
from an ordinary interpreter:

```python
# code/ch026/l01_detect_gil.py
import sys, sysconfig
print("  sys._is_gil_enabled():", sys._is_gil_enabled())
print("  Py_GIL_DISABLED build var:", sysconfig.get_config_var("Py_GIL_DISABLED"))
print("  ABI flags:", repr(sys.abiflags))
```

Verified output (CPython 3.13.5):

```text
--- is the GIL enabled on this interpreter? ---
  sys._is_gil_enabled(): True
  Py_GIL_DISABLED build var: 0
  ABI flags: '' (a 't' suffix marks a free-threaded build)
```

This is a default build: `_is_gil_enabled()` is `True`, `Py_GIL_DISABLED` is `0`, and the ABI flags are
empty. On a free-threaded build the first would be `False`, the build var `1`, and the ABI flags would
end in `t` (the interpreter is `python3.14t`). Both builds run the same source; you select the behavior
at build/install time, not in code. The listing also shows the immortal-object sentinel from Chapter 19,
`refcount(None)` reading a large constant the interpreter never modifies (`4294967295` on 3.13,
`3221225472` on 3.14, both recorded); that immortality is precisely what keeps `None` from becoming a
cross-thread contention point in the free-threaded build.

---

## 26.4 The performance trade (cited)

**These figures are cited to PEP 779 and the CPython team's published tracking, not measured on this
book's machine (verification queue item 2).**

The free-threaded build makes two opposite trades against the default build:

- **Single-threaded overhead**, cited: the free-threaded build runs single-threaded code somewhat
  slower, because biased reference counting and per-object locking add work the GIL made unnecessary. In
  the 3.13 experimental phase this overhead was around 40%; PEP 779 reports it reduced to roughly **10%**
  by 3.14 and sets a **15% hard ceiling** on the pyperformance suite as a condition of supported status.
- **Multi-threaded CPU speedup**, cited: CPU-bound work across threads scales close to linearly with
  cores, the thing the GIL forbade. Published benchmarks report roughly **4x** on four threads for
  suitable workloads, in contrast to the **1.01x** this book measured for threads on the default build
  (Chapter 8).
- **Memory**, cited: the free-threaded build uses somewhat more memory per object (the per-object lock
  state), reported around **15-20%** higher.

The shape of the trade is the honest summary: you pay a single-threaded tax (around 10%, capped at 15%)
and a memory tax (15-20%) to unlock multi-core CPU parallelism with shared memory. Whether that is worth
it depends entirely on whether your workload is threaded CPU-bound work that shares state, exactly the
case every prior chapter had to route around.

---

## 26.5 The rollout, and what it means for your code

PEP 779 (Final) frames the transition in three phases. **Phase I** (3.13) made the free-threaded build
*available but experimental*. **Phase II** (3.14) makes it *officially supported but still optional*: it
ships as a separate binary, the GIL-enabled build remains the default, and the ecosystem is expected to
add free-threading support. **Phase III**, not yet scheduled, would make the free-threaded build the
*default*. The GIL is not gone; it is on a multi-year, publicly-staged path out, and the default build
you run today still has it, as §26.3 confirmed.

For your code, the practical implications now are: the free-threaded build exists and is supported, but
you opt into it deliberately by installing `python3.14t`; a C extension must be built and declared
free-threading-safe to load in it (many are not yet); and code that was implicitly relying on the GIL
for atomicity (for example, assuming `list.append` from multiple threads needs no lock) may have latent
races that the GIL was hiding. Do not assume your threaded code is correct under free-threading just
because it worked under the GIL; the GIL was providing a coarse mutual exclusion your code may have been
depending on without knowing it.

---

## 26.6 Edges and failure modes

**Assuming the default build is free-threaded.** §26.3. It is not; `sys._is_gil_enabled()` is `True` on
an ordinary build. The free-threaded build is a separate install (`python3.14t`). Verify before relying
on GIL-free execution.

**Latent races the GIL hid.** §26.5. Code that relied on the GIL for implicit atomicity may race under
free-threading. The GIL serialized bytecode, so many unsynchronized operations were accidentally safe;
they are not safe without it. Audit shared-state mutation.

**Extension-module incompatibility.** A C extension must declare free-threading support (via the
appropriate module slot) to load in the free-threaded build. Loading one that does not is unsafe or
refused. Check your native dependencies.

**Paying the single-threaded tax for nothing.** §26.4. If your workload is not threaded CPU-bound work
with shared state, the free-threaded build costs ~10% single-threaded and 15-20% memory for a
parallelism you will not use. Use the default build unless you need shared-memory CPU parallelism.

**Citing these numbers as measured.** This chapter's performance figures are cited, not measured here
(§26.4). Do not present them as this book's own measurements; they are PEP 779's and the CPython team's,
pending a `python3.14t` in the verification matrix.

---

## 26.7 Connections

**Backward.** The GIL, and the threads-vs-processes measurement the free-threaded build finally changes,
are Chapter 8. The reference counting that made the GIL necessary is Chapter 19, and immortal objects
(the foundation of §26.2) are measured there. Subinterpreters, the other GIL escape, are Chapter 23, and
this chapter's §26.2 contrasts the two directly.

**Forward.** The full, measured treatment of the free-threaded build, biased reference counting in
detail, the memory model, and the `Py_GIL_DISABLED` C-API rules, is **Deep L**, the canonical home; this
chapter is the timeline introduction. The C-API changes free-threading forces on extensions are **Deep
M**.

**Across books.** Free-threading is the model that lets a Book II analytics layer parallelize CPU-bound
Python over a *shared* in-memory structure, an order book, a large index, without the copy that
subinterpreters or processes require. It also changes the **Book I** boundary: a C++ extension called
from free-threaded Python must itself be thread-safe and declare it, where under the GIL it could assume
serialized entry. The order-book capstone's choice between free-threading and subinterpreters is a
design decision this chapter and Chapter 23 together frame. **Deep L** and **Deep M** own the mechanics.

---

## 26.8 Exercises

**1. Detect your build.** Run the §26.3 listing and confirm your interpreter's GIL status. If you can
install `python3.14t`, run it there and observe the difference in `_is_gil_enabled()` and the ABI flags.
Explain what each field tells you.

**2. Find a hidden race.** Write a threaded program that increments a shared counter without a lock,
which "works" under the GIL because the operations happen to serialize. Reason about (or, on a
free-threaded build, observe) how it can lose increments without the GIL. Explain what implicit guarantee
the GIL was providing.

**3. Reason about the trade.** Given the cited ~10% single-threaded overhead and ~4x four-thread speedup,
compute the crossover: at how many threads of CPU-bound work does the free-threaded build beat the
default build for a given workload? State your assumptions.

**4. Audit an extension.** Pick a C extension you depend on and determine whether it declares
free-threading support. Explain what would happen if you imported it under `python3.14t`, and what the
maintainer would need to change.

**5. The design question.** CPython is shipping *both* the free-threaded build and subinterpreters
(Chapter 23) as answers to the GIL, and making free-threading opt-in with a years-long rollout rather
than flipping it on. Argue why the incremental, dual-track approach is right. Your answer must address
the single-threaded-performance risk to the majority of Python code, the ecosystem's need to become
thread-safe, and why subinterpreters and free-threading serve different workloads (Chapter 23, §23.4).

---

## 26.9 Summary and cross-references

- The **free-threaded build** (PEP 703) is a *separate build* of CPython with the **GIL removed**,
  replaced by **biased reference counting**, immortal objects (Chapter 19), and per-object locks. It
  provides **CPU parallelism with shared mutable memory**, which no other model in this book does.
- **PEP 779 (Final)** made it **officially supported but optional** in Python 3.14 (Phase II); the
  GIL-enabled build remains the default, and `sys._is_gil_enabled()` is `True` on an ordinary build.
- **Cited (not measured here):** single-threaded overhead is roughly **10%** in 3.14 (down from ~40% in
  3.13), with a **15% ceiling**; multi-threaded CPU work scales close to linearly (~**4x** on four
  threads); memory is ~**15-20%** higher. These are PEP 779 and CPython-team figures, in the
  verification queue pending a `python3.14t` build.
- Code that relied on the GIL for implicit atomicity may have **latent races** under free-threading, and
  C extensions must declare free-threading support.

**Cross-references.** The GIL and threads-vs-processes → Chapter 8. Reference counting and immortal
objects → Chapter 19. Subinterpreters, the other escape → Chapter 23. The full measured free-threading
treatment, biased refcounting, and the C-API rules → Deep L. The extension boundary → Deep M.
