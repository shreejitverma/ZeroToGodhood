# Chapter 92: The Escape Decision

Deep K has spent seven chapters making Python faster from inside. This chapter closes the volume with the two questions that remain when those chapters have been applied: **when to stop**, and **where to go** if stopping is not allowed.

Both answers are arithmetic before they are measurements. Amdahl's law caps what optimising the hot path can ever buy, a function that is 90% of runtime made infinitely fast yields **10x** and not one factor more. And Chapter 78's floor prices what staying pure Python costs: at 3.4 ns per instruction and 8 instructions per element, ten million elements cost **272 ms per pass** before the loop does anything you asked for.

When the budget collides with that floor, the escape has two rungs, and the standard library ships both. Moving only the **loop** into C, `math.sumprod` against an explicit loop, measured **3.9x**. Moving the **data** out of Python objects as well, `bytes.count` against a loop over the buffer, measured **28x**, at 0.3 ns per byte. Same answers, different executors, checked below.

**This is a Deep K chapter, and it closes Deep K.**
Chapter 84 (Deep M) owns how to design the crossing once you go; Deep T owns NumPy, the industrialised second rung. This chapter owns the decision itself, and the discipline of not making it too early.

## Section index

- **92.1** The ceiling, the floor, and the procedure
- **92.2** The decision: stop rules, then escape rules
- **92.3** Measurement: the two rungs, priced
- **92.4** Edges and failure modes
- **92.5** Connections, and the volume closed
- **92.6** Exercises
- **92.7** Summary and cross-references

Listings live under `code/ch173/` and are re-executed by `make verify` on both verification interpreters.

---

## 92.1 The ceiling, the floor, and the procedure

```python
# code/ch173/l01_when_to_stop.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- Amdahl: what optimising the hot path can ever buy ---
   hot-path share   made 10x faster   made infinite
              50%              1.8x              2x
              90%              5.3x             10x
              99%              9.2x            100x
  the profile's share (Chapter 86) caps the win: past a point the hot
  path is no longer the program, and the next factor must come from
  somewhere else - or from stopping
--- the interpreter's floor, priced with Chapter 78's constant ---
  model: 3.4 ns per instruction x 8 instructions per element
             n  floor per pass  passes per second
         1,000           27 us             36,765
       100,000          2.7 ms                368
    10,000,000          272 ms                  4
  the floor is paid before the loop does anything you asked for; when
  the budget and the floor collide, no rewrite INSIDE the formulation
  removes it - the formulation itself has to change (Chapters 78, 84)
--- the escape changes the executor, not the answer ---
  sum of squares: loop == genexp == math.sumprod : True
  zero bytes    : manual loop == bytes.count     : True
  same answers, different executors: the C rows run ZERO Python
  instructions per element, so their constant differs in kind, and
  bench 173.1 prices the difference
--- Deep K, as the decision procedure it has been building ---
  1  measure honestly, or do nothing                    (Chapter 85)
  2  find the hot path, and note its share              (Chapter 86)
  3  fix the exponent before the constant               (Chapter 87)
  4  pick the container for the access pattern          (Chapter 88)
  5  price the memory; pack or slot what is big         (Chapter 89)
  6  cache what repeats, bounded                        (Chapter 90)
  7  stream what should never be held; fuse hot stages  (Chapter 91)
  8  requirement met? stop. floor hit? escape           (Chapters 92 and 84)
```

**Amdahl's table is the stop rule with the rhetoric removed.**
The number that matters is not how much faster the hot function got; it is the function's **share** of runtime, which Chapter 86's profile reported and which most optimisation stories omit. A 10x win on a 50% hot path is a 1.8x program. Chasing the same function further is spending effort where the ceiling is lowest, and the table is why re-profiling after every change (Chapter 86) is not bureaucracy: the shares move.

**The floor table is the escape rule, priced with constants this volume measured.**
`3.4 ns x k x n` is Chapter 78's formula, and it is a *floor*: interpreter dispatch alone, before the arithmetic. Steps 3 through 7 of the procedure shrink `k` and the number of passes; nothing inside Python shrinks the 3.4. When the requirement is 60 passes per second over ten million elements and the floor says 4, the formulation has to change, which is what "escape" means precisely: stop paying per-element interpreter cost, either by moving the loop or by moving the loop *and* the data.

**And the equivalence block is the discipline of escaping.**
An escape changes the executor, never the answer, and that is checked, not assumed, because §92.4 has a real caveat about floating point. The procedure block is the volume in eight lines; it is deliberately ordered so that the cheap, reversible moves come first and the one that costs a dependency or a second language comes last.

---

## 92.2 The decision: stop rules, then escape rules

**Stop rules, in order of authority.**

1. **The requirement is met.** "Fast enough" is a number in the spec, a latency budget, a throughput target, a cost ceiling, or it is nobody's requirement and the work is hobby work. Optimising past the requirement spends clarity, which the next maintainer pays, on speed nobody asked for.
2. **The share is exhausted.** When the former hot path is 20% of runtime, its ceiling is 1.25x. Re-profile; either a new hot path emerged, or the program is now uniformly warm, and uniformly warm programs are done, or they escape.
3. **The next rung costs more than it pays.** Every rung of Deep K's ladder has a price in generality: `__slots__` freezes attributes, a cache adds staleness, a packed array forbids `None`, an escape adds a boundary. The moment the price exceeds the requirement gap, stop.

**Escape rules, only after the stop rules failed to fire.**

| condition | met by |
|---|---|
| the remaining cost is the floor | `k` is already small; the profile is flat inside the hot loop |
| the work is per-element, over large `n` | reductions, scans, transforms, membership at scale |
| a C executor expresses the **whole loop** | builtin, `str`/`bytes` method, `math.sumprod`, `sort`, Deep T |
| the data can reach it **without a per-element crossing** | already packed (Chapter 89), or packable once per batch |

The first rung, **the loop leaves Python**, is nearly free to take: it is a rewrite from an explicit loop to a builtin or a C-implemented function, the data stays as it was, and §92.3 prices it at 3.9x. The second rung, **the data leaves Python too**, requires the packed representations of Chapter 89 and pays Chapter 84's rule, one crossing per batch, never per element, and prices at another factor of seven here.

**What is deliberately not on the list: a Python callable per element.**
`map(f, ...)` with a Python `f`, a C library calling back into Python, `ctypes` per element, all pay a crossing or a frame per element and remove nothing; Chapter 91 measured the first and Chapter 84 measured the other two (283 ns per callback). An escape that keeps Python in the per-element path is a costume, not an escape.

**And the destination ladder beyond the stdlib is one line each**, because they are other volumes' subjects: NumPy when the per-element work is arithmetic (Deep T), a C extension or FFI when it is not (Deep M), and parallelism, which is not an escape from per-element cost but a multiplier on whatever per-element cost remains, with its own cost model (Deep E, Deep L).

---

## 92.3 Measurement: the two rungs, priced

**Methodology.** `code/ch173/bench_the_escape.py`.
Standard library only, deliberately: both rungs ship with Python. `min` of 7 batches (5 for the slow rows).
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**Rung one: the loop leaves Python; the data stays.**

| sum of squares, 100,000 ints | time | per element | vs loop |
|---|---|---|---|
| explicit loop | 2.15 ms | 21 ns | 1.00x |
| `sum(x*x for x in data)` | 2.16 ms | 22 ns | 1.01x |
| `math.sumprod(data, data)` | 0.55 ms | 5.5 ns | **3.9x** |

The elements are unchanged, the same hundred thousand `int` objects get multiplied and added, and only the loop moved: no dispatch, no frame, no `LOAD`/`STORE` per element. 3.9x is what the interpreter's share of that loop was, and it is available any time a C-implemented function expresses the whole loop. This is Chapter 76's move, restated as the first rung of the final decision.

**Rung two: the data leaves Python as well.**

| count zero bytes in 1 MB | time | per byte | vs loop |
|---|---|---|---|
| Python loop over the buffer | 8.40 ms | 8.4 ns | 1.00x |
| `buffer.count(0)` | 0.30 ms | **0.3 ns** | **28x** |

Here no element was ever a Python object: `bytes.count` scans raw memory at cache speed. Sub-nanosecond per byte is a different kind of constant, not a different size, and it is only reachable because the representation was already packed, which is Chapter 89's decision rule, choose the representation from what consumes the data, arriving at its destination. The stdlib ships this rung for bytes, hashing, compression, translation, and sorting; NumPy industrialises it for arithmetic (Deep T).

**The two rungs compose with the whole ladder below them.**
The 28x here multiplies the 5,373x of a fixed exponent (Chapter 88), the caching of what repeats (Chapter 90), and the O(1) memory of streaming (Chapter 91), because they remove different costs. **Book I**'s side of the shared system is what full composition looks like: the tick path is packed (rung two) end to end, and Book II's side calls it once per batch across Chapter 84's boundary. The escape decision was made in the design, which is where it is cheapest; this chapter's procedure is how to make it correctly when it was not.

---

## 92.4 Edges and failure modes

**Escapes can change floating-point answers.**
The listing checks equivalence on `int`s deliberately. Over `float`s, an explicit loop, `sum`, `math.fsum`, and `math.sumprod` may differ in the last units of precision, because summation order and internal precision differ, `fsum` and `sumprod` are *more* accurate, not less. An escape that must be bit-identical to the old path needs a tolerance policy first (Chapter 84's cross-boundary testing, and Deep O on comparing floats).

**The callable-per-element trap, one more time.**
It is the single most common failed escape, and it appears in every costume: `map` with a Python lambda, a vectorised-looking API fed a Python function, `qsort` with a Python comparator (112x slower than `list.sort`, Chapter 83). If a Python frame runs per element, the floor was not escaped.

**Packing to escape is a pass you must amortise.**
Converting a list to an `array` or `bytes` costs one full Python-level pass. An escape used once may not repay it; the design answer is upstream, produce the packed form in the first place, from the file, the socket, the parser (Chapters 79, 89), so the escape starts amortised.

**The floor is per interpreter, per build.**
3.4 ns is this machine and these builds; the specializing interpreter moved it (Volume 15), the JIT moves it again (Volume 16, Deep H), and free-threaded builds price differently (Deep L). The *procedure* survives all of them; the constants do not, which is Chapter 85's cross-build rule wearing its last hat: re-derive, never transplant.

**Amdahl's share must come from the production shape.**
A hot path measured on a synthetic workload (Chapter 86's warning) yields a synthetic share, and the ceiling computed from it is fiction. Profile the shape you are paid for, including the I/O the microbenchmark deleted.

**Stopping has failure modes too.**
"Fast enough on my machine" ignores the oldest laptop in the fleet; "fast enough today" ignores that `n` grows (Chapter 87's exponent decides *how fast* it stops being enough); and a requirement met at p50 may be missed at p99, where the GC, the allocator, and the cache misses live. A stop rule is a measurement against a stated distribution, or it is a mood.

**And every escape narrows the code.**
`sumprod` wants numbers; `array` holds one type and no `None`; a C extension holds the ABI (Chapter 82). The generality being spent is the same generality Chapter 89 priced at 24 bytes per integer, and spending it is often right, but it is a spend, and the procedure's order exists so it is spent last.

---

## 92.5 Connections, and the volume closed

**Backward, through the volume this chapter closes.**
Honest measurement (Chapter 85) made every number here citable; the profile's share (Chapter 86) feeds Amdahl's table; the exponent (Chapter 87) and the container (Chapter 88) come before any constant, including the escape's; memory as a cost model (Chapter 89) is what makes rung two reachable; caching (Chapter 90) and streaming (Chapter 91) are the deliberate trades that often make escaping unnecessary. The floor formula is Chapter 78's; the crossing design, once you go, is Chapter 84's; pushing a loop into C was Chapter 76's move and is rung one's mechanism.

**Forward.**
NumPy, rung two with algebra attached, is Deep T. Writing the C yourself is Deep M, already behind you if you are reading in order. Parallelism as a further multiplier, and what the free-threaded runtime does to these constants, is Deep L. The interpreter's own attack on the floor, the specializer and the JIT, is Volumes 15 and 16 and Deep H, and it is the reason this volume measured discipline rather than folklore: the constants will keep moving, and the procedure is what you keep.

**Across books, one last time for Deep K.**
The shared trading system is this chapter deployed: Book II owns strategy, orchestration, and everything measured in milliseconds; **Book I** owns the paths measured in nanoseconds; and the seam between them sits exactly where this chapter's escape rules put it, batch-granular, buffer-shaped, crossed once. Neither book is the fast one or the slow one. They are the two sides of a decision this volume has now taught you to make with numbers.

---

## 92.6 Exercises

**1. Compute your ceiling.** Profile a real program (Chapter 86), take the top function's share, and compute Amdahl's cap for a 2x, 10x, and infinite improvement to it. State whether the cap alone changes what you would work on.

**2. Derive your floor.** Re-derive Chapter 78's constant on your machine, then price a loop you own with `k` from `dis` and your real `n`. Compare the floor with the loop's measured time and explain the gap.

**3. Take rung one.** Find a hot explicit loop in code you maintain that a builtin or `math.sumprod` can express whole. Measure the rewrite, and check the answers agree, with a stated float tolerance if floats are involved.

**4. Price the packing.** For rung two on a list of a million ints, measure: the pass that packs it into an `array`, and the per-use saving of `bytes`/`array`-level operations after it. Compute how many uses amortise the packing, and say where upstream the packed form should have been produced instead.

**5. Fail an escape on purpose.** Reproduce the callable-per-element trap: take a working rung-one escape and reintroduce a Python callable into the per-element path. Measure how much of the win survives. Explain, in terms of frames and crossings, why the answer is almost none.

**6. The design question.** CPython could, in principle, auto-vectorise: detect a loop over uniform floats and execute it at rung two without being asked. Argue why it does not: what arbitrary dunder methods and aliasing do to the legality of the transform (Deep A, Deep C), what the C-API's per-object contract promises extensions (Chapters 81, 82), and how the specializing interpreter (Volume 15) is exactly this idea executed at the only granularity the semantics allow. Conclude with why explicit escapes, chosen by the engineer holding a profile, are a design position and not a deficiency.

---

## 92.7 Summary and cross-references

- **Two questions close the volume: when to stop, where to go.** Both are arithmetic before they are measurements.
- **Stop when the requirement is met, the share is exhausted, or the rung costs more than it pays.** Amdahl: a 90% hot path made infinite yields 10x; the share caps everything, and it moves after every change, so re-profile.
- **The floor is `3.4 ns x k x n`** on this machine: 272 ms per pass at ten million elements, paid before the loop does anything. Steps 3 to 7 of the procedure shrink `k` and the passes; only escaping removes the 3.4.
- **The escape has two rungs, both in the stdlib**: the loop leaves Python (`math.sumprod`, measured **3.9x**), then the data leaves too (`bytes.count`, measured **28x**, 0.3 ns per byte). The second requires Chapter 89's packed representations and pays Chapter 84's one-crossing-per-batch rule.
- **A Python callable per element voids the escape**, in every costume: `map` with a lambda, callbacks, per-element FFI.
- **Escapes narrow the code and can move floating-point answers**; pack upstream so the conversion pass is already amortised; and re-derive every constant per interpreter and build, because the specializer and the JIT keep moving them.
- **Deep K, complete:** measure honestly; find the hot path; fix the exponent; pick the container; price the memory; cache what repeats; stream what should never be held; then stop, or escape. The constants in this volume will age; the procedure is the part to keep.

**Cross-references.** Honest measurement → Chapter 85. The profile's share → Chapter 86. The exponent → Chapter 87. Containers → Chapter 88. Memory and packing → Chapter 89. Caching → Chapter 90. Streaming → Chapter 91. The floor formula → Chapter 78. Pushing loops into C → Chapter 76. Crossing design → Chapter 84. NumPy → Deep T. Free-threading → Deep L.
