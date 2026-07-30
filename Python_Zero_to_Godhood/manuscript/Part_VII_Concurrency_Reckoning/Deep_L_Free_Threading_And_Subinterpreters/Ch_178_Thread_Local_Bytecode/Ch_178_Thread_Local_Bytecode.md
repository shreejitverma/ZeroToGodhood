# Chapter 97: Thread-Local Bytecode and the Single-Threaded Bill

Volume 15 and Deep H told the story of CPython teaching its bytecode to rewrite itself: the specializing adaptive interpreter, hot instructions replacing themselves with type-specialized forms and inline caches. That mechanism is **self-modifying shared state**, which is precisely the kind of thing this volume has been re-engineering, and it is where the free-threaded build's single-threaded reputation was made and unmade: 3.13t simply **disabled** the specializer, and most of that build's infamous ~40% overhead was the disablement, not the locks. 3.14t turned it back on with a design worth this chapter: **bytecode is now thread-local**. Each thread specializes its own copy, so no thread ever races another on an inline cache.

The design is observable from pure Python, twice over. `dis(adaptive=True)` on a function made hot *only by a worker thread* shows specialized instructions on the GIL build and a **cold copy on the free-threaded build**, because `dis` reports the calling thread's view. And timing closes the loop: worker-only code runs at exactly the speed of main-warmed code, **1.00x**, proving the worker's private copy specialized even though main's never did.

With the specializer back, what remains of the single-threaded bill is itemisable, and this chapter itemises it: per-op costs on 3.14.6's two builds differ by **+17% on mutations** (the per-object lock), **+10% on arithmetic**, **+6% on calls**, and **+2% on attribute reads**, mixing, by workload, into PEP 779's ~10% suite average, or into Chapter 93's measured -10% on an allocation-heavy loop.

**This is a Deep L chapter.**
Volume 15 owns the specializer as a release event; Deep H owns tiers, inline caches, and the JIT; Chapter 27 owns copy-and-patch. This chapter owns what the adaptive interpreter became without its one-thread assumption, and where the remaining single-threaded cost lives.

## Section index

- **97.1** The thread-local copy, made visible
- **97.2** The machinery: why caches could not be shared, and what the breaker does now
- **97.3** Measurement: the itemised bill, and the equality that proves the design
- **97.4** Edges and failure modes
- **97.5** Connections
- **97.6** Exercises
- **97.7** Summary and cross-references

Listings live under `code/ch178/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 97.1 The thread-local copy, made visible

```python
# code/ch178/l01_specialization_per_thread.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- warmed in the main thread, inspected from the main thread ---
  BINARY_OP_ADD_INT          : True
  LOAD_ATTR_INSTANCE_VALUE   : True
  FOR_ITER_RANGE             : True
  the adaptive interpreter is ACTIVE on every build in the matrix,
  including free-threaded 3.14, where 3.13t had disabled it entirely
--- warmed ONLY in a worker thread, inspected from the main thread ---
  BINARY_OP_ADD_INT          : True
  LOAD_ATTR_INSTANCE_VALUE   : True
  FOR_ITER_RANGE             : True
```

On the free-threaded build the first block is identical, the specializer is active, and the second block inverts. Verified output (CPython 3.14t):

```text
--- warmed ONLY in a worker thread, inspected from the main thread ---
  BINARY_OP_ADD_INT          : False
  LOAD_ATTR_INSTANCE_VALUE   : False
  FOR_ITER_RANGE             : False
```

**The first block settles the headline question**: the adaptive interpreter runs on 3.14t. The three markers, a specialized binary op, a specialized attribute load, a specialized range iteration, appear after an ordinary main-thread warm-up on every interpreter in the matrix, where 3.13t would have shown none.

**The second block is the design leaking, usefully, into an introspection tool.**
On the GIL build there is one copy of the bytecode; the worker's warm-up specialized it, and `dis` from main sees the result. On the free-threaded build the worker specialized *its own* copy; main's copy never ran and shows cold. `dis(adaptive=True)` is therefore reporting a **per-thread view** on 3.14t, which is both the proof of the mechanism and a tooling gotcha (§97.4): the instrument shows the caller's tier, not "the function's".

**And a methodological confession that belongs in the chapter it improved.**
The first reading of this experiment inferred "only the main thread may specialize", a plausible design. The timing measurement (§97.3's 1.00x) falsified it: worker-only code is exactly as fast as main-warmed code, so the worker's copy *did* specialize, invisibly to main's `dis`. One instrument lied by omission; a second instrument caught it. That is Chapter 85's whole doctrine, executed on this book's own hypothesis.

---

## 97.2 The machinery: why caches could not be shared, and what the breaker does now

**An inline cache is a write into the instruction stream.**
When `BINARY_OP` observes ints twice, it overwrites itself with `BINARY_OP_ADD_INT` and stashes version tags in adjacent cache slots (Deep H). Under the GIL, "one thread at a time" made those writes free. Without it, two threads executing the same hot function would race on every cache write, and every cache read would need synchronisation ordered against the writes. Locking each cache access would cost more than specialization saves; Chapter 96 priced exactly that class of trade.

**3.13t chose absence; 3.14t chose copies.**
Disabling the specializer was correct-by-construction and cost the ~40% single-threaded gap PEP 779 recorded. The 3.14 design gives each thread executing a code object its own specialized instruction array, thread-local bytecode: each copy is warmed by its own thread's observations, written only by that thread, raced by nobody. The costs are two: **memory**, one specialized copy per thread per hot code object, and **cold starts per thread**, since a new thread begins on the unspecialized tier for every function it runs (§97.4).

**The eval breaker kept its price and changed its meanings.**
Chapter 78 measured the per-instruction cost and noted the breaker check rides along free on modern hardware; Chapter 159's forward note promised free-threading "changes what the breaker does, not what a trip costs". Delivered: on 3.14t the breaker is also how a thread notices a stop-the-world request (Chapter 95's safe points) and services the machinery that used to be GIL handoffs. The dispatch loop's arithmetic, and Deep K's floor formula, survive on both builds; §97.3's arithmetic row shows the residual at about +10%.

**The JIT is not part of this story yet.**
The copy-and-patch JIT (Chapter 27) builds on tier-2 traces of specialized code and is not available on the free-threaded build in 3.14; the interaction of thread-local tiers with trace compilation is exactly the frontier 3.15's development is negotiating. This book measures what ships: on 3.14t, tier 1 is back and tier 2 is absent.

---

## 97.3 Measurement: the itemised bill, and the equality that proves the design

**Methodology.** `code/ch178/bench_single_thread_overhead.py`.
Six single-threaded 1,000-iteration micro-workloads, `min` of 9. The two builds match on every dispatch-critical flag except `Py_GIL_DISABLED` (`make interpreters` verifies), so, under Chapter 93's standing caveat, per-row cross-build gaps are attributed to the free-threading machinery itself.
CPython 3.14.6, both builds; Apple M3 Pro, macOS 27.0, arm64.

| workload (1,000 iterations) | 3.14 GIL | 3.14t | t / GIL |
|---|---|---|---|
| arithmetic loop | 16.1 us | 17.7 us | **+10%** |
| attribute reads | 13.5 us | 13.8 us | **+2%** |
| list appends | 13.8 us | 16.1 us | **+17%** |
| dict writes | 18.9 us | 22.1 us | **+17%** |
| function calls | 15.5 us | 16.4 us | +6% |
| genexp sum | 16.4 us | 17.5 us | +7% |

**The rows separate the suspects.**
Mutations pay the most, +17%, an uncontended per-object lock acquire/release per operation (Chapter 96), which is the price of keeping `append` atomic for the installed base. Arithmetic pays ~10%: allocation of result ints through the new allocator plus the biased-refcount checks on every incref (Chapter 94). Attribute reads are nearly free, +2%, the deferred stack references doing precisely their job on the hottest read path. Calls at +6% carry the frame and stack-reference machinery. A real program is a mix of these rows, which is how PEP 779's ~10% suite average, Chapter 93's -10% allocation-heavy outlier, and this table are all the same fact in different proportions: **the overhead is per-operation-class, not per-program, and your number depends on your mix.**

**And the equality that proves §97.1's mechanism.**

| worker-thread loop, 3.14t | time |
|---|---|
| function warmed only in the worker | 27.0 ms |
| function warmed in main first | 27.0 ms |
| ratio | **1.00x** |

If worker-only code ran on the adaptive tier forever, the first row would be tens of percent slower (the 3.13t gap). It is not, so the worker's thread-local copy specialized. The `dis` result and the timing result together pin the design from two sides, which is the only way this book accepts a mechanism claim it cannot read in a struct.

---

## 97.4 Edges and failure modes

**`dis(adaptive=True)` shows the calling thread's copy.** §97.1.
Inspecting from main a function that is hot only in workers shows a cold copy on 3.14t. Benchmark tooling, tutorials, and specialization-checking tests written on the GIL build will misreport; inspect from the thread that runs the code, or trust timing.

**Every new thread starts cold, for every function.**
Thread-local copies mean per-thread warm-up: the first several hundred executions of each hot function in each new thread run unspecialized. A thread-per-task architecture pays that warm-up on every task; a **thread pool** pays it once per worker and amortises. This quietly strengthens the standard advice to pool threads, with an interpreter-tier reason stacked on the OS-cost one (Deep E).

**Hot code times hot memory times threads.**
The memory cost of thread-local bytecode is per thread per hot code object. A 64-worker pool running a large hot module multiplies specialized instruction arrays accordingly. It is bounded and usually small against the heap, but it is new accounting, and a process with thousands of threads and thousands of hot functions should measure it (RSS, not `tracemalloc`, which does not see instruction storage).

**Do not benchmark in an unwarmed worker.**
A microbenchmark that spawns a fresh thread and times immediately measures the adaptive tier, not the specialized one, on 3.14t only, which makes cross-build comparisons silently unfair. Warm inside the measuring thread (this chapter's benchmark does; the harness's warm-up convention exists for exactly this class of trap).

**The specializer's *set* of specializations differs by build and version.**
Some specialization families arrived later on the t-build than the GIL build, and 3.15 continues to converge them. The markers this chapter tests are present on both 3.14 builds; a chapter like this one written against 3.13t would have found none, and one against 3.15 should re-run the listing rather than trust this table.

**The JIT rows do not exist yet.** §97.2.
Any 3.14 benchmark claiming JIT effects on the free-threaded build is measuring something else; tier 2 and copy-and-patch are GIL-build-only in this release.

**And the bill can be negative.** Chapter 93's headline workload ran 10% *faster* on 3.14t. Allocation-heavy code credits mimalloc more than the locks debit it. The itemised table is the reconciliation: know your row mix before predicting your sign.

---

## 97.5 Connections

**Backward.**
The specializer, inline caches, and tiers are Volume 15 and Deep H (Chapters 54 to 56 for code objects, calls, and folding; Chapter 27 for the JIT). The per-instruction floor and the eval breaker are Chapter 78. Biased refcounts and deferred stack references, the +10% and +2% rows' mechanisms, are Chapter 94; the per-object lock behind the +17% rows is Chapter 96; the allocator credited in negative bills is Chapter 95. The honest-measurement doctrine the falsified hypothesis illustrates is Chapter 85.

**Forward.**
Subinterpreters sidestep this chapter entirely, each interpreter keeps single-threaded semantics and a private specializer, at the price Chapter 98 measures. The correctness rules for the code these threads run are Chapter 99. Chapter 100 weighs the whole bill, this chapter's percentages against Chapter 93's multiples, into the architecture decision.

**Across books.**
Thread-local bytecode is Python discovering what JIT runtimes (HotSpot, V8) learned decades ago: profile-guided machinery must either synchronise its profiles or partition them, and partitioning wins when profiles are cheap and races are expensive. **Book I**'s compiler does its specialization at build time, per translation unit, no runtime profiles at all, which is the same partition taken to its static extreme, and the shared system's seam again splits the trade: static specialization on one side, per-thread adaptive on the other.

---

## 97.6 Exercises

**1. Reproduce both instruments.** Run the listing and the benchmark on your matrix. If you have a 3.13t build, add it and observe the specializer's absence directly (all markers False even main-warmed, and the worker ratio far above 1.00x).

**2. Itemise your own bill.** Pick your hottest module, classify its operations against §97.3's rows (mutation-heavy? attribute-heavy?), predict your t/GIL gap, then measure the module on both builds and compare with your prediction.

**3. Price the cold start.** On 3.14t, time a function's first 50 in-thread calls against its steady state, per fresh thread. Compute how many tasks a thread-per-task design must run before the warm-up tax exceeds 1% of total time, and state the pool size at which it vanishes.

**4. Watch the copies specialize.** Run one function hot in three threads; from each thread, capture `dis(adaptive=True)` into a queue and diff the three views against main's. Report which threads' copies specialized which instructions.

**5. Cross-build fairness audit.** Take any published "free-threading is X% slower" microbenchmark you can find and check it against this chapter's traps: was the measuring thread warmed; was the GC state stated (Chapter 95); do the builds match on dispatch-critical flags; is the workload one row or a mix?

**6. The design question.** Thread-local bytecode spends memory to avoid synchronisation; the alternative was shared bytecode with atomic cache updates and racy-read tolerance, which other runtimes do ship. Argue CPython's choice: what a racy inline-cache read may observe on weakly-ordered hardware (a version tag from one specialization and a pointer from another), what guarding against that costs on every dispatch (Chapter 78's budget), and why per-thread copies also happen to give per-thread *profiles*, which specialize better for thread-specialised workloads. Then find the workload where shared caches would win (many short-lived threads over one hot function) and reconcile it with this chapter's pool advice.

---

## 97.7 Summary and cross-references

- **The specializing interpreter is back on the free-threaded build (3.14), via thread-local bytecode**: each thread specializes its own copy of hot code, so inline caches are raced by construction never. 3.13t's ~40% overhead was mostly the specializer's absence, not locking.
- **Proven from two sides**: `dis(adaptive=True)` shows a worker-warmed function cold from main on 3.14t only (per-thread views), and worker-only code times at **1.00x** of main-warmed code (the private copy specialized). An initial "only main specializes" hypothesis was falsified by the second instrument, Chapter 85 in action.
- **The itemised single-threaded bill (3.14.6, t vs GIL, caveated cross-build)**: mutations **+17%** (per-object lock), arithmetic **+10%**, calls +6%, genexps +7%, attribute reads **+2%**. Workload mixes reproduce PEP 779's ~10% average or Chapter 93's -10% outlier; the sign depends on your rows.
- **New accounting**: per-thread warm-up (pool your threads), per-thread bytecode memory (measure via RSS at scale), `dis` reporting the caller's tier, and no JIT on the t-build in 3.14.
- **The eval breaker's trip still costs the same** (Chapter 78 holds); it now also services stop-the-world safe points.

**Cross-references.** The specializer and tiers → Volume 15, Deep H. The JIT → Chapter 27. The instruction floor and the breaker → Chapter 78. Refcount machinery → Chapter 94. The allocator → Chapter 95. Per-object locks → Chapter 96. Honest measurement → Chapter 85. Subinterpreters → Chapter 98. Correctness → Chapter 99. The decision → Chapter 100.
