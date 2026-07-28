# Chapter 78: The Evaluation Loop and Its Ceiling

Every chapter in this volume has been measuring one quantity from a different angle: **how many times the evaluation loop runs**.
A code object is a sequence of instructions (Chapter 54); a call pushes a frame and starts the loop over it (Chapter 55); constant folding removes instructions before the loop ever sees them (Chapter 56); a zero-cost `try` adds none (Chapter 73); `join` replaces a quadratic allocation pattern with one that runs fewer times (Chapter 74); a name read is one trip (Chapter 75); a builtin's C loop is zero trips per element (Chapter 76); an inlined comprehension is one fewer frame's worth of trips (Chapter 77).

This chapter names the thing they were all measuring, prices it, and states the ceiling it implies.
The price on this machine is **about 3.4 nanoseconds per bytecode instruction**.
The ceiling is the direct consequence: a loop that executes 8 instructions per element over 10 million elements has a floor of roughly **0.27 seconds** of pure interpreter overhead, before it does anything you asked for, and no amount of tuning inside that formulation removes it.

There are exactly two ways under the floor. Change the algorithm so there is no per-element work, or leave the interpreter so the per-element work is not bytecode. Everything else is a constant factor.

**This is the closing chapter of Deep H.**
It gives the dispatch model, the measured price of a trip, the two exits, and an honest account of what the JIT has and has not delivered.

## Section index

- **78.1** Fetch, dispatch, execute, repeat
- **78.2** Five formulations, one task, and the exponent
- **78.3** Measurement: the price of one trip around the loop
- **78.4** Edges and failure modes
- **78.5** Connections
- **78.6** Exercises
- **78.7** Summary and cross-references

Listings live under `code/ch159/` and are re-executed by `make verify` on both verification interpreters.

---

## 78.1 Fetch, dispatch, execute, repeat

The interpreter's core is a loop in `Python/ceval.c` over the current frame's instruction array. Each iteration reads the next instruction, jumps to the C code that implements that opcode, runs a bounded amount of work, and returns to the top. Three properties of that shape explain most of this volume.

**The unit of work is the instruction, and it is bounded.**
Between two instructions the interpreter can check the *eval breaker*: has a signal arrived, has another thread asked for the GIL, is a garbage collection pending, has an asynchronous exception been set. This is why a `KeyboardInterrupt` lands promptly in a Python loop and does not land at all in the middle of a single long C call, and why the interpreter's thread switch interval, `sys.getswitchinterval()`, is expressed in seconds but enforced at instruction boundaries. The listing prints it: **0.005** seconds, identical on both verification interpreters.

**The dispatch mechanism is a build choice, not a language property.**
A portable build compiles the loop as a `switch` over the opcode. A build with computed gotos (a GCC/Clang extension) puts a jump table at the end of *each* opcode's implementation, so the branch predictor sees a separate indirect branch per opcode rather than one shared branch it can never predict. The difference is real and it is invisible from Python, except through `sysconfig`.

This book's own two verification interpreters differ on exactly this flag, and it is worth stating plainly because it is the reason the harness refuses to compare across them:

| | CPython 3.13.5 (Anaconda) | CPython 3.14.6 (Homebrew) |
|---|---|---|
| `USE_COMPUTED_GOTOS` | `1` | `0` |
| `OPT` | `-DNDEBUG -O2 -Wall` | `-DNDEBUG -g -O3 -Wall` |
| tail-call interpreter | not built | `Py_TAIL_CALL_INTERP = 0` |
| JIT | not built | `sys._jit.is_available()` is `False` |

Two builds of the same language, one dispatching through a jump table and one through a switch, at different optimisation levels. Any cross-version ratio drawn from these two would be measuring Anaconda against Homebrew, not 3.13 against 3.14. Every table in this book is therefore within a single interpreter, and this is the concrete reason why.

**The frame stack has a ceiling too.**
`sys.getrecursionlimit()` is **1000** on both interpreters: a thousand Python frames, not a thousand C stack frames, though the two are related closely enough that raising the limit far is a way to segfault the process rather than a way to recurse deeper. The recursion limit is the loop's other fixed parameter, and Chapter 55 measured what each of those frames costs.

**What the specializing interpreter and the JIT are trying to do.**
Everything CPython has done for performance since 3.11 attacks the *per-trip* cost rather than the trip count. Specialization (PEP 659) rewrites a warm instruction into a variant that assumes the types it has been seeing and guards the assumption, so the trip does less work. The copy-and-patch JIT (PEP 744) goes further and removes the dispatch itself for hot traces, stitching pre-compiled machine-code templates together. Both make each trip cheaper. Neither makes a trip stop happening, which is why the ceiling in §78.2 is where it is.

---

## 78.2 Five formulations, one task, and the exponent

```python
# code/ch159/l01_the_ceiling.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- one task, five formulations: all agree ---
  explicit loop          332833500 == reference : True
  sum([comprehension])   332833500 == reference : True
  sum(genexpr)           332833500 == reference : True
  sum(map(lambda))       332833500 == reference : True
  closed form            332833500 == reference : True
--- bytecode instructions executed per element ---
  explicit loop            8
  sum([comprehension])     6
  sum(genexpr)             7
  sum(map(lambda))         3
  closed form              0
--- the budget: instructions the interpreter must dispatch for n = 10,000,000 ---
  explicit loop            80,000,000
  sum([comprehension])     60,000,000
  sum(genexpr)             70,000,000
  sum(map(lambda))         30,000,000
  closed form                       0
--- the loop's own parameters, which do not depend on your code ---
  recursion limit (frames)        : 1000
  thread switch interval (seconds): 0.005
```

**The first four rows are the same program.**
They compute the sum of squares below `n` by visiting every element. They differ in how much bytecode each visit costs, from 8 instructions down to 3, and that range, a factor of under three, is the entire space that rewriting the loop can explore. Every technique in this volume lives inside that factor.

**The fifth row is a different program.**
`(n - 1) * n * (2 * n - 1) // 6` is the closed form of the same sum. It executes **zero** instructions per element because it has no elements. The budget line makes the consequence arithmetic rather than rhetorical: at ten million elements the four looping formulations require between 30 and 80 million trips around the evaluation loop, and the closed form requires none.

**Why this is the right way to end a volume about the interpreter.**
Chapters 54 through 77 are all techniques for reducing the constant. They are worth knowing, they are worth applying, and the measurements say they buy between 10% and 6x depending on which one and where. The closed form buys 76,000x (§78.3), and it buys it by not being a loop. A volume that taught the constants without stating their ceiling would have taught the reader to optimise carefully in the wrong place, which is the failure mode this chapter exists to prevent.

**The two exits, stated precisely.**

- **Change the algorithm.** Fewer elements visited, or none. A closed form, a better data structure that avoids the scan (Deep K), an index that turns a linear search into a hash lookup, an early exit that stops at the first match. This changes the exponent.
- **Leave the interpreter.** The per-element work still happens, but not as bytecode: a NumPy ufunc over a contiguous array (Deep T), a C extension over a shared buffer (Deep M), a compiled kernel. This keeps the exponent and cuts the constant by one to two orders of magnitude rather than by a factor of three.

The order matters. The algorithm change is almost always cheaper to implement, always portable, and cannot be undone by an interpreter upgrade. Reach for the second exit when the first is genuinely unavailable, which for the shared order-book system's matching path it is, and which is why **Book I** owns that path.

---

## 78.3 Measurement: the price of one trip around the loop

**Methodology.** `code/ch159/bench_the_ceiling.py`.
The five formulations at `n = 200,000`, then each row's time divided by the number of bytecode instructions it executed (its slope from §78.2, times `n`). If the dispatch model is right, that quotient should be roughly constant across rows that have per-element bytecode. The closed form is measured with its own batch size, because five calls per batch of a 70 ns function is below the timer's useful resolution. `min` of 7 batches for the loops, 15 for the closed form.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| sum of squares below 200,000 | time | vs loop | instructions | ns per instruction |
|---|---|---|---|---|
| `sum([comprehension])` | 5.12 ms | 0.95x | 1,200,000 | 4.3 |
| explicit loop | 5.38 ms | 1.00x | 1,600,000 | **3.4** |
| `sum(genexpr)` | 5.47 ms | 1.02x | 1,400,000 | 3.9 |
| `sum(map(lambda))` | 6.64 ms | 1.23x | 600,000 | 11.1 |
| closed form | **70 ns** | **0.000013x** | 0 | n/a |

**The model holds for three rows out of four.**
The explicit loop, the comprehension, and the generator expression agree on 3.4 to 4.3 nanoseconds per instruction. They execute different amounts of bytecode and take almost the same total time, and the quotient is stable, which is the model saying: these are different quantities of the same unit of work. The comprehension's slightly higher figure is its allocation, it materialises a 200,000-element list that the other two never build, and that memory traffic is charged to a smaller instruction count.

**The `map` row breaks the model, and the break is the informative part.**
11.1 nanoseconds per instruction is three times the others. Its 3 instructions per element are only the lambda's body; the C-level machinery that calls the lambda once per element, building the call, entering and leaving a frame, is real work that a bytecode counter cannot see. This is Chapter 76's boundary restated at the level of the dispatch loop: the instruction count is blind to C-level cost *added*, and when the derived ns-per-instruction figure disagrees with its neighbours, the disagreement is pointing at exactly that.

**The ceiling, in the form worth remembering.**
At 3.4 ns per instruction, a loop that visits `n` elements at `k` instructions each cannot finish faster than `3.4 * k * n` nanoseconds.

| per-element slope | 1 million elements | 10 million elements |
|---|---|---|
| 3 (a tight `map`) | 10 ms | 0.10 s |
| 6 (a comprehension) | 20 ms | 0.20 s |
| 8 (an explicit loop) | 27 ms | 0.27 s |
| 14 (a loop with `.append`) | 48 ms | 0.48 s |

These are floors, not estimates: they exclude the work the loop is actually doing. If your budget is 10 milliseconds and your input is ten million elements, no Python-level formulation fits, and the question is which of §78.2's two exits you are taking. That is a design conversation, and having the number turns it from an argument about style into arithmetic.

**76,000x, and what it is not.**
The closed form is roughly 76,000 times faster than the loop at this input size, and that ratio *grows with n*, because one side is O(1) and the other is O(n). Quoting it as a speedup is close to meaningless; quoting it as evidence that constants and exponents are different currencies is the point. No plausible interpreter improvement, not specialization, not the JIT, not removing the GIL, moves a row by four orders of magnitude. Changing what the program does moves it by four orders of magnitude routinely.

**On the JIT, honestly.**
Neither verification interpreter has the copy-and-patch JIT built (§78.1), so this book has no measurement of it and does not offer one. What the primary source says, and this book will say no more than its source, is that PEP 744 describes the JIT as currently "about as fast as the existing specializing interpreter", roughly neutral rather than a clear win, with continuation gated on a future gain of around 5%. Secondary reports of 10-30% are workload-specific microbenchmarks, not a broad-suite net speedup. The 3.14 tail-call interpreter has a similar history: initially reported as a large gain, then substantially revised after the comparison baseline was found to be affected by an LLVM 19 code-generation regression. This book does not cite a corrected figure because it has not verified one; the entry stays open in the verification queue.

The reason to state this carefully rather than enthusiastically is the chapter's argument. Even a JIT that delivered a clean 30% would move the 0.27-second floor to 0.19 seconds. It would not move it to 70 nanoseconds.

---

## 78.4 Edges and failure modes

**3.4 ns per instruction is this machine, this build, this workload.** §78.3.
It is an M3 Pro, an `-O2` computed-goto build, and instructions that are mostly integer arithmetic and local reads. A build without computed gotos, an older CPU, or a workload dominated by attribute lookups and dict operations will give a different number. Re-derive it on your hardware before budgeting with it; the technique in the benchmark is three lines.

**The instruction count is blind to C-level cost.** §78.3.
It mispredicts `map` here and mispredicted it in Chapter 76. When the derived ns-per-instruction disagrees between rows, believe the timing and use the disagreement to find what the count is missing.

**Never compare timings across the two interpreters.** §78.1.
They differ in computed gotos and in optimisation level. The harness enforces this; the reason is now concrete rather than a general caution.

**`sys.setrecursionlimit` does not give you deeper recursion, it gives you a different crash.**
The Python limit and the C stack are coupled. Raising the limit past what the C stack supports converts a clean `RecursionError` into a segmentation fault. If you need depth, restructure to an explicit stack, which is also the change that removes the per-frame cost of Chapter 55.

**The eval breaker means a long C call is not interruptible.** §78.1.
`sum(range(10**10))` cannot be interrupted by `Ctrl-C` until it finishes, because there is no instruction boundary inside it. This is the cost of the zero-instructions-per-element property that Chapter 76 recommends, and it is the reason a long-running C-level operation in a server should be bounded by size, not by a timeout.

**A closed form is not always available, and looking for one is not always time well spent.**
The sum of squares has one. Most real loops do not. The productive version of this chapter's advice is not "find the closed form" but "know that you are inside a factor-of-three space, and check whether the problem admits a different exponent before spending a week on the constant".

**Do not budget with the floor alone.**
The floors in §78.3 exclude the actual work. A loop whose body does real computation will be slower than its floor, sometimes far slower. The floor tells you when a formulation is *definitely* infeasible, which is a one-sided but useful test.

---

## 78.5 Connections

**Backward, and this is the volume's summary.**
Code objects and frames, Chapter 54: the instruction array the loop walks and the state it walks it with. Function call overhead, Chapter 55: what starting a new walk costs. Constant folding, Chapter 56: instructions removed before the loop runs. Zero-cost exceptions, Chapter 73: a guard that adds no instructions. Immutability and accumulation, Chapter 74: an allocation pattern that changes how many times the loop runs. Name lookup, Chapter 75: the price of one trip, measured. Pushing the loop into C, Chapter 76: trips per element reduced to zero. Comprehensions and the inlined frame, Chapter 77: a frame's worth of trips removed by the compiler.

**Forward.**
Measurement discipline, profiling, and how to find out which loop matters before optimising any of them are Deep K, which is the correct next volume for a reader who wants to apply this one. Vectorized bulk operations, the first exit's most common form in numerical code, are Deep T. The C boundary and the buffer protocol, the second exit, are Deep M. Free-threading, which changes what the eval breaker does but not what a trip costs, is Deep L. The specializing interpreter as a release event is Volume 15; the copy-and-patch JIT as a release event is Chapter 27.

**Across books.**
The division of labour between the two books is this chapter's conclusion applied to one system. **Book I** owns the matching engine because its inner loop is exactly the case where neither exit is optional: the per-element work is irreducible and the budget is microseconds, so the work cannot be bytecode. Python owns everything around it, where the per-element counts are small, the budgets are milliseconds, and the readability is worth more than the constant. The buffer protocol is the seam, and it exists so that choosing the right side for each loop does not cost a copy.

---

## 78.6 Exercises

**1. Derive your own constant.** Reproduce §78.3 on your machine and record your nanoseconds per instruction. Compare the figure derived from the explicit loop with the one derived from the generator expression, and say what a large disagreement between them would mean.

**2. Build the floor table.** Using your constant, compute the floor for the hottest loop in a program you maintain. State whether the loop's actual time is close to its floor, and what that tells you about where its time is going.

**3. Find the model's blind spot.** Add a row to the benchmark whose per-element work is a C-level call the bytecode counter cannot see, and show the derived ns-per-instruction diverging. Explain the divergence without appealing to the count.

**4. Both exits on one problem.** Take a loop that computes a running statistic over a list. Implement it three ways: as written, with an algorithmic improvement (an incremental update rather than a rescan), and with NumPy. Measure all three and place them on §78.2's two-exit framing.

**5. The eval breaker.** Write a Python loop and a single long C-level call that take about the same wall time, and try to interrupt each with `Ctrl-C`. Explain the difference from §78.1, and say what it implies for a request handler that calls a C library.

**6. The design question.** CPython's evaluation loop could, in principle, be replaced wholesale by an ahead-of-time compiler for the subset of Python whose types are statically known. Argue why this has repeatedly been attempted and repeatedly not been adopted into CPython: what the subset excludes, what breaks when a name is rebound at runtime, and why the copy-and-patch JIT's design (templates plus guards, PEP 744) is the shape that survives those constraints.

---

## 78.7 Summary and cross-references

- The evaluation loop is **fetch, dispatch, execute, repeat**, and every measurement in Deep H is a count of how many times it runs. Between instructions the interpreter checks the **eval breaker** (signals, GIL handoff, GC), which is why `sys.getswitchinterval()` (**0.005 s**) is enforced at instruction boundaries and why a single long C call is not interruptible.
- **Dispatch strategy is a build flag, not a language property.** This book's two verification interpreters differ on it: 3.13.5 has `USE_COMPUTED_GOTOS = 1`, 3.14.6 has `0`, at different optimisation levels, with no JIT and no tail-call interpreter on either. That is the concrete reason every table here is within a single interpreter.
- **Measured on 3.13.5: about 3.4 ns per bytecode instruction.** The explicit loop, the comprehension, and the generator expression all derive 3.4 to 4.3 ns per instruction from wildly different instruction counts, which is the dispatch model holding. `sum(map(lambda))` derives 11.1 ns, because its 3 instructions per element hide a C-level call the counter cannot see.
- **The ceiling:** a loop at `k` instructions per element over `n` elements has a floor of `3.4 * k * n` ns. Eight instructions over ten million elements is **0.27 seconds** of interpreter overhead before any real work.
- **One task, five formulations:** 8, 6, 7, and 3 instructions per element for the four looping forms, and **0** for the closed form. Rewriting the loop explores a factor of under three; the closed form is **76,000x** faster at 200,000 elements and the ratio grows with `n`.
- **Two exits, and only two:** change the algorithm so there is no per-element work, or leave the interpreter so the per-element work is not bytecode. Everything in Chapters 54 to 77 is a constant factor inside those.
- **On the JIT, what the source supports and no more:** PEP 744 describes the copy-and-patch JIT as currently about as fast as the specializing interpreter, gated on a future ~5% gain. The 3.14 tail-call interpreter's initial figures were revised after an LLVM 19 regression was found in the baseline; no corrected figure is cited here because none has been verified. Neither is built into this book's interpreters.

**Cross-references.** Code objects and frames → Chapter 54. Call overhead → Chapter 55. Constant folding → Chapter 56. Zero-cost exceptions → Chapter 73. Accumulation → Chapter 74. Name lookup → Chapter 75. C-level loops → Chapter 76. Comprehension inlining → Chapter 77. Profiling and measurement discipline → Deep K. Vectorization → Deep T. The C boundary → Deep M. Free-threading → Deep L. The specializing interpreter as a release → Volume 15. The copy-and-patch JIT as a release → Chapter 27.
