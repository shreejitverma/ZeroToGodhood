# Chapter 99: Correct on Both Builds

Chapter 93 stated the volume's ground rule: the free-threaded build raises the frequency of losses that unlocked compound operations always risked; it does not create the obligation to lock them. This chapter puts numbers on "frequency", and the numbers rearrange the whole testing story.

The unlocked `box.n += 1`, four threads, four hundred thousand increments: on the free-threaded build it loses **84,000 to 132,000 updates per run**, a quarter to a third, every single time. On the GIL build it loses **zero, in every trial, at every switch interval**, and that zero is structural, not lucky: the modern GIL is released only at safe points, loop back-edges and calls, so a call-free bytecode sequence is never split. Put a Python call inside the sequence and shake the switch interval, and the GIL build loses 45% too.

Read those three facts together and the conclusion writes itself: **the build you develop on is structurally incapable of showing you most of your races.** A free-threaded CI leg is not an optimisation check; it is the only honest stress test threaded Python has ever had.

The rest of the chapter is the discipline that makes the test boring: patterns that are exact on every build by construction, and the measured price of each. The cheapest one wins by a landslide: partition-and-merge did the lab's 400,000 increments correctly in **1.5 ms** on the free-threaded build, where a shared `Lock` paid **48 ms** of contention for the same answer.

**This is a Deep L chapter.**
Chapter 46 owns the race and the lock; Chapter 51 owns GIL-era atomicity and flagged that it "changes under free-threading"; this chapter is that change, measured, plus the construction rules and the testing prescription that survive every build.

## Section index

- **99.1** Correct by construction, verified
- **99.2** The rules: ownership, edges, and what "atomic" means now
- **99.3** Measurement: the race lab
- **99.4** Edges and failure modes
- **99.5** Connections
- **99.6** Exercises
- **99.7** Summary and cross-references

Listings live under `code/ch180/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 99.1 Correct by construction, verified

```python
# code/ch180/l01_correct_by_construction.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- partition and merge: the pattern that cannot race ---
  4 private counters, summed after join : 400,000
  no shared mutable state exists during the work, so there is
  nothing to protect; join() is the synchronisation edge that makes
  the final reads safe. exact on every build, and the FASTEST
  correct pattern in the benchmark
--- hand-off through a Queue: sharing with the lock built in ---
  1,000 items produced, consumed : 1,000, sum 499,500
  a Queue is a lock, a buffer, and a happens-before edge in one
  object: whatever the producer did before put() is visible to the
  consumer after get(). ownership transfers; it is never shared
--- publish with an edge, never with time ---
  50 rounds of set-then-wait, reader always saw the write : True
  Event, Lock, Queue, Barrier, and join() are ordering edges; a
  sleep() is a bet. Python has no formal memory model, so the
  portable rule is: no shared read is ordered unless an edge orders it
--- the discipline, in four lines ---
  1  do not share: partition and merge, or isolate (Chapter 98)
  2  share immutables: constants, frozen data, immortals (Chapter 94)
  3  mutate behind ONE owner: a Lock, a Queue, or a single thread
  4  test on the free-threaded build: the GIL build cannot surface
     call-free races AT ALL, at any switch interval (the benchmark)
```

**Partition-and-merge shares nothing while the work runs.**
Each thread accumulates in a local, writes once into a private slot, and `join()` is the synchronisation edge that makes the main thread's final reads safe. There is no protected region because there is nothing to protect, which is why §99.3 prices it at almost nothing, and why it is byte-identical across the matrix: correctness that does not depend on any build's mercy.

**The Queue is sharing with the lock, the buffer, and the ordering built in.**
`put` and `get` are the edges; whatever the producer did before `put` is visible to the consumer after `get`. The working discipline is *ownership transfer*: an object put on a queue belongs to the consumer now, and the producer keeping a reference to mutate is the bug (Chapter 90's shared-cached-list edge, wearing overalls).

**And the Event round is the memory-model paragraph made executable.**
Python has no formal memory model; what it has, on every build, is the guarantee that its synchronisation objects establish ordering. Write, then `set()`; `wait()`, then read: fifty rounds, the reader always sees the write. Replace the `Event` with a `sleep()` and the same test becomes a bet whose odds vary by build and by machine. **No shared read is ordered unless an edge orders it** is the only portable sentence, and every correct pattern in this chapter is an application of it.

---

## 99.2 The rules: ownership, edges, and what "atomic" means now

**Rule 1: prefer designs where the question cannot arise.**
Partition-and-merge for divisible work; subinterpreters (Chapter 98) when isolation should be structural; immutable and immortal data for whatever is genuinely shared (Chapter 94: sharing immutables is not only safe but *fast*, no refcount contention if the references are held right, Chapter 96's hoist). The measured order of preference in §99.3d is the same as the safety order, which is rare and worth exploiting.

**Rule 2: what remains shared gets exactly one owner.**
A `Lock` makes the critical section the owner; a `Queue` makes the consumer the owner; a dedicated writer thread makes that thread the owner. All three are correct; they differ in price and in failure modes (deadlock for locks, unbounded buffers for queues, latency for single writers), and Deep E's chapters on each remain the reference. What no build provides is compound atomicity by default, and what no correct design does is rely on the scheduler.

**Rule 3: recalibrate the word "atomic".**
Chapter 51's careful GIL-era table, which single operations are atomic, survives: single container operations remain atomic on both builds (Chapter 96, by lock instead of by GIL). What changed is the *penumbra*: sequences that were never guaranteed but never failed. The lab shows that penumbra is wide on the GIL build, `+=` on an attribute cannot be split there at all today, and gone on the free-threaded build. Code relying on the penumbra was always wrong by contract; now it is wrong in production, at 25 to 33% per run.

**Rule 4: test where the races are visible.**
The prescription, from the lab's three distributions: run the suite on 3.14t (the only build that surfaces call-free races); on GIL builds, `sys.setswitchinterval(1e-6)` in the stress harness shakes out the call-bearing ones; and treat any test that fails once in fifty runs as a fire, not a flake. A thread-sanitizer CPython build is the heavier tool when C extensions are in the mix; for pure Python, the free-threaded leg is cheaper and closer to production.

---

## 99.3 Measurement: the race lab

**Methodology.** `code/ch180/bench_race_lab.py`.
Races are distributions, so the lab reports **sorted results over 7 trials**, never a single number. Fix timings are `min` of 5. Within-build only.
CPython 3.14.6, both builds; Apple M3 Pro, macOS 27.0, arm64.

**a. Unlocked `box.n += 1`, four threads, 400,000 increments.**

| build | lost updates, 7 trials |
|---|---|
| GIL | 0, 0, 0, 0, 0, 0, 0 |
| free-threaded | 83,928 ... 132,357 (**21% to 33%**) |

**b. The same, with a Python call inside the sequence, switch interval 1 us.**

| build | lost updates, 7 trials |
|---|---|
| GIL | 180,134 ... 192,458 (**~45 to 48%**) |
| free-threaded | 182,412 ... 221,570 |

**c. Check-then-act on a shared dict, 1,000 keys**: GIL, seven zeros; free-threaded, 2 to 19 double-initialisations per run.

**The three tables define what the GIL build can and cannot teach you.**
Row a's zeros are structural: the eval breaker runs at loop back-edges and calls, both *after* the store, so a call-free read-modify-write is indivisible on today's GIL builds, at any switch interval. Row b breaks the spell the moment a call, any call, a logging statement, a property, an `__eq__`, sits inside the sequence. So the GIL build shows you none of your call-free races and only shows call-bearing ones under provocation, while the free-threaded build shows both classes on every run. A latent race that shipped years ago on the GIL build is not "exposed by" 3.14t; it is *finally observable*, which is a gift, received best in CI rather than production.

**d. The fixes, priced, for the same exact 400,000.**

| correct pattern | GIL build | free-threaded |
|---|---|---|
| one shared `Lock` | 25.2 ms | 48.0 ms |
| partition and merge | 4.8 ms | **1.5 ms** |

The `Lock` is correct everywhere and pays Chapter 96's contention arithmetic in user code, four threads queueing on one cache line, costing *more* on the parallel build than the serial one. Partition-and-merge is correct everywhere and **32x cheaper** on the free-threaded build, because it deletes the sharing instead of guarding it, and the parallel build rewards exactly that. The safety ranking and the speed ranking coincide, which is the volume's friendliest result: the discipline is not a tax.

**Book I** has run this lab for decades under TSan and helgrind, and its conclusions are the same sentences with different nouns: data races are undefined behaviour, test under the tools that see them, and the fastest mutex is the one the design removed. The shared system's Python side adopts the C++ side's CI habit wholesale: every threaded suite runs once on the GIL build for speed and once on 3.14t for truth.

---

## 99.4 Edges and failure modes

**The GIL build's zeros are an implementation detail, not a contract.** §99.3a.
Back-edge-only release is how current CPython behaves; no document promises it, and it has changed before. Code passing the GIL-build lab proves nothing; the contract remains "compound operations need an owner", and only the free-threaded lab tests the contract.

**Any call re-opens the sequence.** §99.3b.
"Call-free" is fragile: adding a debug log, turning an attribute into a property, or a `__iadd__` that does work converts row a into row b silently. Never reason "this sequence has no calls, so it is safe"; reason "this sequence has no lock, so it is wrong".

**Races hide in `+=` on *anything* shared**: attributes, dict slots, list elements, class variables, module globals. The lab used an instance attribute; the distribution is the same shape for every spelling, and the class-variable spelling (`Counter.total += 1`) additionally contends on a single hot object (Chapters 94, 96).

**`nonlocal`/closure accumulation across threads is the same bug wearing a scope.**
The listing's consumer uses `nonlocal` safely because exactly one thread writes it; two consumers would race it. Ownership is per-variable, and "one owner" must survive refactors that add workers.

**Queues can be unbounded, and edges can deadlock.**
Correctness patterns have their own failure modes, owned by Deep E: bounded queues with backpressure (Chapter 49), lock ordering (Chapter 53), and timeouts on every `wait`. This chapter's rules choose *which* pattern; Deep E's chapters keep the pattern healthy.

**Flaky tests are the race lab running in production miniature.**
A threaded test that fails 1-in-50 is reporting a distribution tail, and re-running until green is sampling until the evidence goes away. Pin it: run the failing test 500x on 3.14t, and treat the loss counts as this chapter treats them, sorted, not averaged.

**And the free-threaded lab is necessary, not sufficient.**
21-33% loss rates make *frequent* races visible in seconds; rare interleavings still need volume (many trials, varied thread counts) and, where C extensions participate, a TSan build. Absence of failures is evidence, never proof; construction (§99.2) is the proof.

---

## 99.5 Connections

**Backward.**
The race and the lock are Chapter 46; queues and backpressure, Chapter 49; deadlock and ordering, Chapter 53; the GIL-era atomicity table this chapter recalibrates is Chapter 51, whose "changes under free-threading" flag is hereby resolved. The machinery that sets the new loss rates is Chapters 94 (refcounts), 96 (container locks and contention), and 97 (what the breaker still does); the pattern that deletes the problem class entirely is Chapter 98.

**Forward.**
Chapter 100 closes the volume by folding this chapter's discipline and prices into the architecture choice: the four-way table's "correctness burden" column is this chapter compressed to a row.

**Across books.**
C++ made data races undefined behaviour and built a memory model with acquire/release edges; Python has no formal model, and its portable subset is smaller and simpler: synchronisation objects order, everything else does not. **Book I**'s testing chapter and this one give identical prescriptions, sanitize in CI, design for ownership, distrust green runs, because the underlying physics, caches, buffers, and schedulers, never spoke either language.

---

## 99.6 Exercises

**1. Run the lab.** Both builds, 7 trials. Then vary thread count through 2, 8, 16 on the free-threaded build and report how the loss fraction moves. Explain the direction.

**2. Find your penumbra.** Grep a codebase you own for `+= ` on attributes, globals, and subscripts reachable from threads. Classify each: partitioned, locked, single-owner, or penumbra. Run the suite on 3.14t and report what the penumbra entries did.

**3. Price your fix.** For the hottest penumbra entry from exercise 2, implement the Lock fix and the partition fix, measure both on both builds, and write the three-line justification for the one you keep.

**4. Break the Event.** Replace the listing's `Event` with a `time.sleep(0.01)` publish and measure the failure rate over 1,000 rounds on both builds. Then explain why a passing sleep-based test is worse than a failing one.

**5. Shake a real flake.** Take a threaded test that has ever flaked in a project you know. Run it 500x on 3.14t with `pytest -x`, capture the failure distribution, and fix it by construction (§99.2). Report before/after distributions.

**6. The design question.** CPython could add an opt-in atomic type (`atomic_int`, compare-and-swap) rather than asking users to choose between locks and restructuring. Argue both sides: what lock-free counters would buy the lab's workload (row d suggests: less than partitioning), why a memory-model commitment is the true cost of shipping atomics (every future interpreter change constrained by it), and what the existing portable subset (edges order, nothing else does) preserves for PyPy and future CPythons. Conclude with which of this chapter's patterns an atomic type would actually retire, and whether that retirement pays for a memory model.

---

## 99.7 Summary and cross-references

- **Measured loss rates for the unlocked read-modify-write**: free-threaded, **21-33% per run, every run**; GIL build, **structurally zero** for call-free sequences (safe-point-only release), and ~45-48% once a call sits inside and the interval is shaken.
- **Therefore: the GIL build cannot surface most races.** A free-threaded CI leg is the only honest stress test; `setswitchinterval(1e-6)` helps only for call-bearing sequences; sorted distributions, never averages; a 1-in-50 flake is a fire.
- **The discipline**: share nothing (partition-and-merge, or Chapter 98's isolation); share immutables; give every remaining mutable exactly one owner (Lock, Queue, or a single thread); order every shared read with an edge, `Event`, `Lock`, `Queue`, `join`, never with time.
- **The prices coincide with the safety ranking**: partition-and-merge did the lab's work in **1.5 ms** on 3.14t where the shared `Lock` paid **48 ms** of contention. The fastest lock is the one the design removed.
- **"Atomic" recalibrated**: single container ops hold on every build (Chapter 96); the GIL-era penumbra of accidentally-safe sequences is an implementation detail there and gone on 3.14t; contract-relying code is unchanged, penumbra-relying code is now visibly broken.

**Cross-references.** The race and the lock → Chapter 46. Queues → Chapter 49. Atomicity's old table → Chapter 51. Deadlock → Chapter 53. Refcount machinery → Chapter 94. Container locks and contention → Chapter 96. The breaker and safe points → Chapter 97. Isolation → Chapter 98. The architecture decision → Chapter 100.
