# Chapter 84: Choosing a Boundary

Every chapter of this volume produced a constant.
A bytecode instruction costs about **3.4 nanoseconds** (Chapter 78). A Python function call costs about **11** (Chapter 81). A `ctypes` call costs about **142** (Chapter 83). A callback from C into Python costs about **283** (Chapter 83).

Put them together and the question this volume opened with, *where should the boundary between Python and C go*, stops being a matter of experience or taste and becomes arithmetic. There are four possible designs for a per-element operation, each with a cost that is a straight line in `n`, and three of the four lose to a plain Python loop under conditions you can compute in advance.

The conclusion is sharp enough to state before the evidence: **the boundary is worth crossing exactly once per batch. If your design crosses per element, the boundary is in the wrong place**, and no choice of FFI technology repairs it.

**This closes Deep M.**
It collects the volume's constants into a model, checks the model against a real operation, and turns it into a decision procedure that includes the option the volume has been circling: do not cross at all.

## Section index

- **84.1** Four designs, priced
- **84.2** Choosing the technology, once the design is right
- **84.3** Measurement: does the model predict
- **84.4** Edges and failure modes
- **84.5** Connections
- **84.6** Exercises
- **84.7** Summary and cross-references

Listings live under `code/ch165/` and are re-executed by `make verify` on both verification interpreters.

---

## 84.1 Four designs, priced

```python
# code/ch165/l01_choosing_a_boundary.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the constants this volume measured, on this machine ---
  one bytecode instruction :    3.4 ns
  one Python call          :   11.0 ns
  one ctypes call          :  142.0 ns
  one callback into Python :  283.0 ns
--- four designs, modelled at k = 8 instructions per element ---
  design                                  n=1         n=10        n=100     n=10,000  n=1,000,000
  1  pure Python loop                 27 ns       272 ns       2.7 us     272.0 us      27.2 ms
  2  FFI call per element            142 ns       1.4 us      14.2 us       1.4 ms     142.0 ms
  3  FFI once, whole buffer          143 ns       152 ns       242 ns      10.1 us       1.0 ms
  4  C loop, Python callback         283 ns       2.8 us      28.3 us       2.8 ms     283.0 ms
--- the break-even points that matter ---
  FFI-per-element beats a Python loop only above 42 instructions per element
  real loop bodies measured in this book : 6 to 14
  so FFI-per-element is never the answer : True
  one whole-buffer call beats a Python loop above n = 5
  and its advantage grows without limit, because the slopes differ
--- the same conclusion, as a decision procedure ---
  is the per-element work expressible as one C operation over a buffer?
    yes -> design 3: cross once, pass a memoryview, release the GIL
    no, it needs a Python callable per element -> stay in Python (design 1)
    no, and it must be fast -> write the per-element code in C too
```

**Design 2 is the one people write first, and it is never right.**
"Python is slow, so I will call C" naturally produces a loop that calls a C function per element. The model prices it: it beats a Python loop only when the Python body would have cost more than a crossing, which needs **42 bytecode instructions per element**. Chapter 77 measured real loop bodies at 6 to 14. There is no realistic body in that gap, and the row at `n = 1,000,000` says what the mistake costs: 142 milliseconds against the Python loop's 27.

**Design 4 is design 2 with extra steps.**
A C library that takes a callback per element pays the crossing *and* the Python frame, at 283 nanoseconds measured. Chapter 83's `qsort` result, 112x slower than `list.sort()`, is this row observed rather than modelled.

**Design 3 is the only one with a different slope.**
Its fixed cost is a single 142-nanosecond call, and its per-element cost is C's, which for simple work is on the order of a nanosecond. That is why it beats a Python loop from about **n = 5** onwards and why the gap keeps widening: the other three designs have a Python-sized slope and this one has a C-sized slope. Everything Chapters 44, 79 and 80 recommend, pass a `memoryview`, cross once, release the GIL, is this row.

**Design 1 is the default, and defaults deserve respect.**
A pure Python loop is the fastest of the four at `n = 1`, is within a factor of the best at small `n`, requires no build system, no ABI decision, no lifetime discipline, and cannot segfault. The model says to leave it alone unless design 3 is genuinely available.

---

## 84.2 Choosing the technology, once the design is right

The technology question is downstream of the design question, and it is much less important. If you are crossing once per batch, all four options below are fast enough; the choice is about build complexity, distribution, and how much C you want to own.

| | what it is | build step | ships as | best when |
|---|---|---|---|---|
| **stdlib C** | `hashlib`, `zlib`, `re`, `struct`, `bisect`, `array` | none | already there | **always the first question** |
| **`ctypes`** | stdlib FFI, no compiler | none | pure Python | a stable C library exists and you call it rarely |
| **`cffi`** | FFI that parses C declarations | optional | pure Python or compiled | the same, but with real headers and fewer hand-written signatures |
| **Cython** | Python-like language compiled to C | yes | per-version wheels | the per-element work is yours and must be fast |
| **C-API extension** | hand-written C | yes | per-version or `abi3` | you need full control, or you are wrapping a large surface |

**The first question is not "which FFI".**
It is "is this already in the standard library, or in NumPy". `hashlib` releases the GIL and hashes at memory bandwidth (Chapter 80). `re` is a compiled engine. `array` and `memoryview` give you contiguous buffers with no third-party dependency. §84.3's benchmark makes the point in one row: `bytes.index(0)` is the same C scan as `libc.strlen` and is reached without any of ctypes' machinery.

**`ctypes` versus `cffi`.**
`ctypes` requires you to hand-declare `argtypes` and `restype`, and Chapter 83 showed that getting them wrong is a silent wrong answer. `cffi` parses actual C declarations, which removes that class of error, and its API mode compiles a small shim that is faster than `ctypes` and no longer pure Python. Neither is available in this book's harness on both interpreters, so no measurement of `cffi` appears here; the structural argument, that declarations parsed from headers cannot disagree with the headers, stands without one.

**Cython and hand-written C are the same decision at different granularity.**
Both mean you own compiled code, a build system, and a wheel matrix (Chapter 82) or the limited API's constraints. Cython buys you Python-like source for most of it; the C-API buys you exact control. Both are the right answer when the per-element work is *yours* rather than an existing library's, which is design 3's third branch: write the per-element code in C too.

**And the option the whole volume points at.**
For numerical per-element work, the answer is usually none of the above: it is NumPy (Deep T), which is design 3 with the boundary already built, the buffers already contiguous, and the C loops already vectorised. Reaching for `ctypes` to speed up arithmetic over a list is skipping the tool built for exactly that.

---

## 84.3 Measurement: does the model predict

**Methodology.** `code/ch165/bench_boundary_designs.py`.
One task, find the first zero byte in a buffer, implemented as designs 1, 2 and 3, plus the stdlib's own C scan as the floor. Design 4 is not re-measured; it was measured directly in Benchmark 164.1 at 283 ns per callback, which is the constant the model uses. `min` of 9 batches (5 for the large size).
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| find the first zero byte | n = 100 | n = 100,000 | growth |
|---|---|---|---|
| 1 Python loop | 1.19 us | 1,459 us | 1,175x |
| 2 FFI call per element | 15.8 us (**13.4x worse**) | 16,206 us | 1,023x |
| 3 FFI once, whole buffer | 0.12 us (**0.10x**) | 1.73 us | 14.7x |
| stdlib `bytes.index(0)` | 0.024 us (**0.02x**) | 1.62 us | 67.7x |

**The model's shape holds exactly.**
Design 2 is worse than design 1 at both sizes, by roughly the ratio the constants predict, and it is worse *at every size* because both are linear and one has a far larger slope. Design 3 is better than both at both sizes. Nothing in the table crosses over, which is what the break-even calculation said would happen: design 2's break-even needs a 42-instruction body and this body has about 8.

**The growth column is where the model earns its keep.**
Multiplying `n` by 1,000 multiplies the two per-element designs by about 1,000, as a linear cost in `n` must. It multiplies the whole-buffer call by only **14.7**, because most of its cost at `n = 100` was the fixed 142-nanosecond crossing, and only the C scan grew. That is not a constant-factor advantage; it is a different curve, and it is the entire argument for crossing once.

**The last row is the one to take away.**
`bytes.index(0)` is the same C scan as `libc.strlen`, reached with no `ctypes`, no `argtypes`, no lifetime discipline and no chance of a segfault, and it is the fastest row at small `n` by a factor of five. Every boundary decision should begin by asking whether the standard library already made it. The FFI is for the case where the answer is no.
**Book I**'s role in the shared system is the case where the answer is genuinely no: the matching engine's per-element work is not in any Python library, must be measured in microseconds, and is therefore written in C++ and entered once per batch across a `memoryview`. That is design 3's third branch, chosen deliberately, with this table as the justification.

---

## 84.4 Edges and failure modes

**The constants are this machine's.** §84.1.
3.4 ns per instruction and 142 ns per `ctypes` call are an M3 Pro with these builds. The *ratios* are more portable than the absolutes, and the break-even calculations depend on the ratio. Re-derive them before making a decision that matters; each is a few lines.

**The model assumes the C per-element cost is small.**
`ffi_whole_buffer` uses 1 ns per element. A C routine doing real work per element (a cryptographic round, a decompression step) has a much larger slope, and design 3's advantage over design 1 shrinks accordingly. The model is a floor for the C design, not a promise.

**Amdahl's law applies to the whole program, not the loop.**
Turning a loop that is 5% of your runtime from design 1 into design 3 makes the program 4.8% faster at best, in exchange for a build system and a class of memory-safety bugs. Profile first (Deep K); this volume's constants tell you what a boundary *could* buy, not whether it is worth buying.

**"Rewrite it in C" often loses to "use a better algorithm".**
Chapter 78's closed-form row was 76,000x faster than the loop. No boundary choice reaches that, because it is a change of exponent and these are all changes of constant. Exhaust the algorithmic option first.

**Every compiled option adds a distribution problem.** §84.2.
Cython and C-API extensions mean wheels per version per platform (Chapter 82), or the limited API's constraints, or a compiler on your users' machines. `ctypes` and `cffi`'s ABI mode stay pure Python. For a library with many users on many platforms, this is frequently the deciding factor and it has nothing to do with speed.

**A wrong `argtypes` is a silent wrong answer, and it does not go away with scale.** §84.2.
Design 3 reduces the *number* of crossings, not the correctness burden of each one. One badly declared call over a whole buffer can corrupt more memory than a million well-declared small ones.

**Do not model a callback as a call.** §84.1.
Design 4's 283 ns is not 142 ns plus rounding; it is the crossing plus a Python frame plus the GIL handling `CFUNCTYPE` performs on entry. Measure it separately, as Chapter 83 did, rather than assuming it is a crossing.

---

## 84.5 Connections

**Backward, and this is the volume's summary.**
Calling C at all, and the `argtypes`/`restype` discipline, is Chapter 43. Whole-buffer calls, the first statement of design 3, are Chapter 44. The C-API reached from Python is Chapter 45. `memoryview`, which is how the buffer crosses without a copy, is Chapter 79. Releasing the GIL, which is what makes one long call parallelisable, is Chapter 80. Reference lifetime across the boundary is Chapter 81. The ABI and the wheel matrix that every compiled option inherits are Chapter 82. Error models and the callback tax are Chapter 83.

**Forward.**
Profiling, which tells you whether any boundary is worth crossing in your program, is Deep K. Vectorised numerical work, which is design 3 with the boundary pre-built, is Deep T. Packaging a compiled extension, wheels, tags and the `abi3` decision in practice, is Deep N. Free-threading, which changes what releasing the GIL is worth, is Deep L.

**Across books.**
This chapter is the formal statement of why the series is split. **Book I** owns the work whose per-element cost must be C's; Book II owns everything around it, where the per-element counts are small and the readability is worth more than the constant. The seam is design 3 by construction: a `memoryview` over a tick buffer, one call per batch, the GIL released for its duration. Both books' halves are chosen by the arithmetic in §84.1 rather than by preference, which is what makes the split defensible rather than stylistic.

---

## 84.6 Exercises

**1. Re-derive the constants.** Measure the four constants of §84.1 on your machine, using the benchmarks from Chapters 78, 81 and 83. Recompute the break-even points. Say which conclusions changed.

**2. Predict, then measure.** Pick a loop from your own code, count its per-element instructions with the technique from Chapter 77, and predict each of the four designs' cost at your real `n`. Then implement design 3 if it is available and check the prediction.

**3. Find the crossover that does not exist.** Try to construct a per-element loop body expensive enough that design 2 beats design 1. Report what it took, and whether that body is something you would ever write.

**4. Ask the first question.** Take three operations you would reach for `ctypes` to accelerate and find, for each, whether the standard library or NumPy already does it in C. Measure the stdlib version against your FFI version.

**5. Price the distribution.** For a hypothetical library with a compiled extension, enumerate the wheels you would have to build for the currently supported Python versions on three platforms, and then the same list under `abi3`. Say what that changes about the technology choice.

**6. The design question.** This volume's arithmetic says design 2 is never right, yet it is the design most first attempts produce. Argue why: what mental model makes "call C for each item" seem natural, what feedback the programmer is missing at the moment they write it, and what a language or library could do to make the correct design the obvious one. Use NumPy's ufuncs as an example of a design that did exactly that.

---

## 84.7 Summary and cross-references

- The volume's constants, on this machine: **3.4 ns** per bytecode instruction, **11 ns** per Python call, **142 ns** per `ctypes` call, **283 ns** per callback into Python. From them the boundary decision is arithmetic rather than taste.
- **Four designs, each linear in `n`:** a Python loop (`n·k·3.4`), an FFI call per element (`n·142`), one FFI call over the whole buffer (`142 + n·c`), and a C loop with a Python callback (`n·283`).
- **FFI-per-element is never right.** It beats a Python loop only above **42 instructions per element**, and real loop bodies measured in this book are **6 to 14**.
- **Crossing once is the only design with a different slope**, so it wins from about `n = 5` and its advantage grows without limit.
- **Measured on 3.13.5**, finding the first zero byte in a buffer: at `n = 100` the per-element FFI is **13.4x worse** than a Python loop and the whole-buffer call is **0.10x**; at `n = 100,000` multiplying `n` by 1,000 multiplied the per-element designs by about **1,000** and the whole-buffer call by only **14.7**. The model's shape held exactly.
- **The first question is not "which FFI" but "is this already in C somewhere I can reach".** `bytes.index(0)` is the same scan as `libc.strlen`, with none of the machinery, and is five times faster at small `n`.
- **The technology choice is downstream and mostly about distribution:** stdlib C (no build), `ctypes`/`cffi` ABI mode (pure Python), Cython or a C-API extension (a wheel matrix, or the limited API's constraints).
- **Edges:** the constants are machine-specific but the ratios travel; the model assumes cheap C per-element work; Amdahl's law applies to the program, not the loop; a change of algorithm can beat every design here by orders of magnitude; correctness burden per crossing does not fall just because there are fewer crossings.

**Cross-references.** Calling C and `argtypes`/`restype` → Chapter 43. Whole-buffer calls → Chapter 44. The C-API from Python → Chapter 45. `memoryview` → Chapter 79. Releasing the GIL → Chapter 80. References across the boundary → Chapter 81. ABI and wheels → Chapter 82. Errors and callbacks → Chapter 83. Profiling → Deep K. Vectorisation → Deep T. Packaging → Deep N. Free-threading → Deep L.
