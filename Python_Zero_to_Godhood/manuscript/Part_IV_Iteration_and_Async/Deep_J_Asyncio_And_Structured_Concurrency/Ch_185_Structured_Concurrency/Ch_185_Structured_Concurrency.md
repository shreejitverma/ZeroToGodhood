# Chapter 104: Structured Concurrency

Chapter 103 ended with a list of obligations: hold every task you create, retrieve every exception, await everything before moving on. Structured concurrency is the 3.11 API that turns those obligations into syntax. A **`TaskGroup`** owns every task created inside it; its `async with` block cannot exit until every child has finished; one child's failure cancels the siblings; and *all* failures arrive together as an **`ExceptionGroup`**, matched with `except*`. Concurrency acquires the property function calls have always had: **what starts inside a block ends inside it.**

The listing proves the lifecycle in deterministic order: the group refusing to exit before its slower child; a failure cancelling a sibling *through* Chapter 103's honest-cancellation contract; two simultaneous failures arriving as one group and dispatching to two `except*` arms, where `gather` would have reported only the first; and `asyncio.timeout` converting its own injected cancellation into `TimeoutError` at its boundary, via the `uncancel` bookkeeping built for exactly this.

The benchmark prices the structure: a deadline that never fires costs **~1.3 us per block** (a timer handle's lifecycle, wear one per request, not per await), and the structured *error* path costs **489x** a plain exception, which is correct economics: failures are rare, and structure exists to make them impossible to lose, not cheap to throw.

**This is a Deep J chapter.**
Chapter 103 owns tasks and the cancellation rail; Volume 15's release chapters own `ExceptionGroup`/`except*` as syntax history. This chapter owns the structured model: ownership by block, failure as a group, and deadlines as boundaries.

## Section index

- **104.1** The lifecycle, proven in order
- **104.2** The model: blocks own tasks, errors are sets, deadlines are boundaries
- **104.3** Measurement: what the structure costs
- **104.4** Edges and failure modes
- **104.5** Connections
- **104.6** Exercises
- **104.7** Summary and cross-references

Listings live under `code/ch185/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 104.1 The lifecycle, proven in order

```python
# code/ch185/l01_structured_concurrency.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the group waits for every child ---
  order   : a-done, b-done, group-exited
  results : ('a', 'b')
  the async with block refused to exit until the slower child
  finished: children cannot outlive their block, so there are no
  orphans to hold references to (Chapter 103's first edge, solved)
--- one failure cancels the siblings ---
  order : sibling-waiting, failer-raises, sibling-cancelled, caught-group-of-1
  the failure did not leak past the block, and it did not leave the
  sibling running: cancellation of the group is the ERROR PATH, and
  it uses Chapter 103's contract (the sibling re-raised, honestly)
--- multiple failures arrive TOGETHER ---
  values: ['bad-value']
  keys: ["'bad-key'"]
  gather(return_exceptions=False) reports only the FIRST failure;
  a TaskGroup collects every failure into one ExceptionGroup, and
  except* runs each matching handler against its selection
--- timeout: cancellation converted at its own boundary ---
  order : worker-sees-CancelledError, caller-sees-TimeoutError
```

**The happy path is a scope rule.**
`group-exited` comes after both children, always: the `async with` is a barrier, and the tasks it created cannot outlive it. That single property retires Chapter 103's first two edges at once, no dropped references (the group holds its children) and no unretrieved exceptions (the group awaits and re-raises them). Results are read off the task objects after the block, exactly like locals after a loop.

**The failure path is cancellation used as infrastructure.**
`failer-raises` then `sibling-cancelled`: the group reacted to the first failure by cancelling every other child, and the sibling's log line shows Chapter 103's contract doing its job, `CancelledError` at the await, cleanup, re-raise. The error then surfaces *at the block* as a group. Note what did not happen: no error leaked to the loop's "never retrieved" reporter, no sibling kept running detached, and the code that handles the failure is textually adjacent to the code that started the work.

**The two-failure block is the semantic upgrade over `gather`.**
Both children failed in the same beat; both exceptions arrived, one `ExceptionGroup` carrying a `ValueError` and a `KeyError`, and `except*` ran *each* matching arm against its selection. `gather` returns failures positionally or raises only the first; a group loses nothing, which matters most in the situation where it matters most, shutdown storms, where the second exception is usually the interesting one.

**And the timeout block shows the `uncancel` machinery earning its keep.**
Inside the boundary, the worker experienced ordinary cancellation, same rail, same contract. At the boundary, `asyncio.timeout` checked whether the `CancelledError` arriving was *its own* (the counter says how many external cancels are outstanding) and converted it to `TimeoutError`; an external cancel landing at the same moment still propagates as cancellation. Deadlines and cancellation compose because 3.11 gave them separate bookkeeping, this is the payoff of Chapter 103's oddest-looking API.

---

## 104.2 The model: blocks own tasks, errors are sets, deadlines are boundaries

**Ownership by block is the whole idea, and it is a *restriction*.**
Unstructured `create_task` builds arbitrary task graphs; a group forbids a child to outlive its block, exactly as a function forbids its locals to outlive its frame. What the restriction buys is reasoning: at any line, the set of running tasks is determined by the enclosing blocks, visible in the indentation, and resource lifetimes (`async with` a connection *around* the group that uses it) nest correctly by construction. Fire-and-forget still exists for the rare true daemon, with Chapter 103's registry obligations; the group makes it the exception that looks like one.

**Errors are sets because concurrency makes them sets.**
Two children can fail in the same beat; any API must either drop one (pre-3.11 `gather`'s first-wins), defer them into data (`return_exceptions=True`, which callers forget to unpack), or represent the plurality honestly. `ExceptionGroup` is the honest representation, and `except*` is its match statement: each arm selects the matching leaves, handles them, and whatever no arm matched re-raises as a smaller group. The old single-exception world remains available at the leaves, an individual task still raises one exception, the group-ness begins where concurrency begins.

**Deadlines are boundaries, not decorations.**
`asyncio.timeout(d)` bounds *everything* inside its block, however deep the await chain, because cancellation propagates down the whole tree of children (each nested group's cancellation cancels *its* children, recursively). Deadlines therefore compose downward for free, and the design that follows is one deadline per meaningful boundary, the request, the batch, the connection attempt, rather than per operation; §104.3 gives the per-block price that makes per-await wrapping wasteful.

**`gather` remains the right tool for exactly one shape**: a fixed, known list of independent awaitables whose results you want positionally and whose failure policy is "give me everything as data" (`return_exceptions=True`). For everything else, dynamic membership, failure containment, cancellation correctness, the group is the default, and the 3.13 addition of `TaskGroup`-based patterns across the stdlib reflects that settlement.

---

## 104.3 Measurement: what the structure costs

**Methodology.** `code/ch185/bench_structured_overhead.py`.
`min` of 5 runs; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. A deadline that never fires.**

| per operation | time |
|---|---|
| bare await | 44 ns |
| wrapped in `asyncio.timeout` | 1,324 ns (**+1,281 per block**) |

The wrapper schedules a timer handle on entry and cancels it on exit, ~1.3 us of Chapter 101 bookkeeping. Per request, invisible; per micro-await, a 30x tax on the 44 ns underneath. One deadline per boundary is both the cleaner semantics (§104.2) and the cheaper arithmetic, a rare alignment worth exploiting.

**b. The error path, plain against structured.**

| raise-and-catch one ValueError | time |
|---|---|
| `try`/`except` | 88 ns |
| `TaskGroup` + failing task + `except*` | 43,238 ns (**489x**) |

The structured error path is a task start (Chapter 103's ~27 us under the default factory), group construction and teardown, sibling bookkeeping, and an `ExceptionGroup` allocation. Chapter 73 taught that the `try` is free and the `raise` is the price; groups raise the price two orders further. The reading is not "avoid groups"; it is **do not use the group's error path as control flow**. Expected, frequent conditions (cache miss, validation failure) should return values or raise *inside* the child and be handled there; the group boundary is for genuine failure, which is rare by definition, and whose cost is dominated by what failed, not by the bookkeeping.

**Book I**'s structured-concurrency cousin is the scoped thread / `std::jthread` + stop-token world: joins at scope exit, cancellation via tokens, and its measurements make the same two points, scope machinery is cheap on the success path, and error propagation across threads costs what marshalling costs. The convergence is recent in both languages, and for the same reason: two decades of leaked-worker bugs.

---

## 104.4 Edges and failure modes

**`except ValueError` does not catch a group's `ValueError`.**
An `ExceptionGroup` is its own type; only `except*` selects into it. Code upgraded from `gather` to `TaskGroup` with unchanged `except` clauses silently stops catching, the migration's one real trap, and the reason to grep for `except (Value` near every group introduction. (An `except*` clause, conversely, also matches a *bare* `ValueError` raised through it, wrapping it, so the new spelling is the safe one in mixed code.)

**Do not catch `ExceptionGroup` wholesale to "unwrap" it.**
`group.exceptions[0]` re-raised discards the siblings and the tracebacks that explain a shutdown storm. Use `except*` per type; use `group.split()` when policy genuinely differs by predicate; log the whole group when in doubt, its rendered traceback shows the tree.

**A failed `create_task` on a closed group raises immediately.**
After the group has begun shutting down (a child failed), further `tg.create_task` calls raise `RuntimeError`. Producers feeding a group must handle the group's death, usually by letting the error propagate, which is the structure working, but surprising inside callback-fed patterns.

**Cancellation inside `except*` is still cancellation.**
Handlers run in the parent task; an external cancel arriving during handling follows Chapter 103's rules. Keep handlers short and idempotent, they are shutdown-path code by construction.

**The suppression trap now has a blast radius.** Chapter 103's swallowed `CancelledError`, inside a group child, stalls the *group*: the block waits for a child that will never acknowledge. The symptom is a shutdown hang with one task in `sleep`; the audit is the same, find the `except CancelledError` without a `raise`.

**Timeout boundaries do not preempt CPU.**
`asyncio.timeout` cancels at awaits (Chapter 101's clause); a child grinding a 10-second computation blows through any deadline. Deadlines bound *waiting*; bounding *computing* requires executors (Chapter 107) whose futures the deadline can abandon, with Chapter 103's shield semantics deciding what "abandon" means for the work.

**And nesting is the intended idiom, not a smell.**
Groups within groups, timeouts within groups within timeouts: cancellation propagates to the leaves, errors aggregate towards the root, and each boundary converts or re-raises per its role. Resist the flat-list instinct inherited from `gather`; the tree is the model, and the code's indentation should look like the process tree you would draw.

---

## 104.5 Connections

**Backward.**
The cancellation rail, `cancelled()` honesty, `uncancel`, and task references are Chapter 103, this chapter is that machinery given syntax. The deterministic schedule the order-proofs rely on is Chapter 101; the exception machinery and zero-cost `try` are Chapter 73; `ExceptionGroup`/`except*` as a 3.11 release event is Volume 15's story.

**Forward.**
The coordination objects children wait on, and the queue patterns groups supervise, are Chapter 105. Streams inside groups, Chapter 106; executors under deadlines, Chapter 107; and Chapter 108's patterns, bounded fan-out, supervisors, graceful shutdown, are all `TaskGroup` compositions, which is why this chapter sits in the volume's middle rather than at its end.

**Across books.**
Structured concurrency's manifesto ("go statement considered harmful") argued that unrestricted spawning is `goto` for control flow, and both books' languages converged on the same repair in the same half-decade: scoped ownership, cancellation trees, aggregated failure. **Book I**'s `jthread`-and-stop-token chapter and this one are the same design document with different keywords, and the shared system's supervisors are literally parallel implementations of one shutdown diagram.

---

## 104.6 Exercises

**1. Reproduce the orders.** Run the listing; then move the `failer`'s `sleep(0)` to `sleep(0.01)` and predict the new order before running. Explain which lines moved and why the determinism survived.

**2. Migrate a gather.** Take a real `gather(*tasks)` call with its `except` clauses; convert to `TaskGroup` + `except*`. Document every behavioural change you observe under single failure, double failure, and external cancellation.

**3. Price your deadlines.** Count timeout blocks per request in a service you know. Measure §104.3a on your machine, compute the per-request deadline overhead, and restructure to one-per-boundary if it exceeds 1% of budget.

**4. Build a supervisor.** A group that restarts failed children up to N times with backoff, converting the terminal failure into a group that names every attempt. Test under deterministic failure injection; assert the order log.

**5. Bound the unboundable.** Wrap a CPU-grinding child in a deadline and show the deadline failing to fire until the grind's next await. Fix it with Chapter 107's `to_thread` plus shield semantics, and show the deadline working while the work survives or dies per your policy, stated explicitly.

**6. The design question.** `except*` is new syntax, added for this feature, the highest-cost move a language can make. Argue the alternatives that were rejected: groups-as-lists with library helpers (loses `finally` composition and re-raise semantics), flattening to the first error (loses the shutdown storm's evidence), and callbacks per failure (loses textual locality). Then state the migration hazard §104.4 opens with, weigh it against the alternatives' permanent losses, and decide whether the syntax was worth it, with the two-failure block's output as your exhibit.

---

## 104.7 Summary and cross-references

- **The model**: a `TaskGroup` owns its children; the block exits only when all have finished; one failure cancels the siblings through Chapter 103's contract; all failures arrive together as an `ExceptionGroup`, matched by `except*`. What starts inside a block ends inside it.
- **Proven in order**: the barrier (`group-exited` last), the sibling cancellation (`failer-raises, sibling-cancelled`), the two-failure aggregation dispatching to two `except*` arms, and `asyncio.timeout` converting its own cancellation to `TimeoutError` via the `uncancel` counter, while external cancels still propagate.
- **Priced**: a never-firing deadline costs **~1.3 us per block** (one per boundary, not per await); the structured error path costs **489x** a plain exception (a task, a group, and an `ExceptionGroup`), fine, because structure is for never losing rare failures, not for throwing cheap ones.
- **The traps**: `except` does not see into groups (`except*` does, and also matches bare exceptions); unwrapping `exceptions[0]` discards evidence; a swallowed `CancelledError` now hangs its whole group; deadlines bound waiting, never computing.
- **`gather` survives** for fixed lists wanting positional results-as-data; the group is the default for everything else, and nesting is the idiom, the code should look like the process tree.

**Cross-references.** Tasks, cancellation, `uncancel` → Chapter 103. The deterministic schedule → Chapter 101. Exception machinery → Chapter 73. `except*` as a release event → Volume 15. Coordination objects → Chapter 105. Streams → Chapter 106. Executors under deadlines → Chapter 107. The patterns → Chapter 108.
