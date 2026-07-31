# Chapter 287: Interpreters

## The constraint

CPython has two routes to *true* parallelism - running Python bytecode on multiple cores at once, which the GIL historically prevented.
One is to remove the GIL entirely: the free-threaded build (Chapter 26), where threads share memory and run in parallel.
The other is *subinterpreters*: run several independent interpreters in one process, each with its *own* GIL, so they execute in parallel without a shared lock.

Subinterpreters existed at the C level for years, and the per-interpreter GIL (Chapter 23) made them genuinely parallel.
But using them required writing C - there was no Python-level API - so the model was out of reach for ordinary code.
Meanwhile the two approaches embody *opposite* trade-offs.
Free-threading shares memory, which is powerful and fast but reintroduces data races - the shared-mutable-state hazards that the GIL had masked.
Subinterpreters *isolate*: each has its own modules, globals, and GIL, and they share nothing by default, so there are no data races - at the cost of having to pass data explicitly between them.

The constraint Python 3.14 (2025, PEP 734) answered: **put the subinterpreter model in the standard library**, so parallelism-through-isolation is reachable from Python without the C API.

This is a two-track chapter.
The full free-threading-versus-subinterpreters story - the mechanisms, the trade-offs, when each wins - is Deep Volume L's subject.
What this chapter owns is the release: the day subinterpreters became a Python-level tool.

## What shipped

`concurrent.interpreters` provides `create()` (a fresh isolated interpreter), `Interpreter.exec()` (run code in it), a `Queue` for passing shareable data, `is_shareable()` to test what can cross, and `close()` to release it.
Listing 287.1 shows the model on the 3.14 builds (it is gated to 3.14+, since the module is new).

Verified output (CPython 3.14.6):

```text
--- create() gives a fresh, isolated interpreter ---
  created interpreter, distinct id from main : True
  each subinterpreter has its OWN import state, its own globals, and
  (since Chapter 23's per-interpreter GIL) its own GIL - so several
  can run Python bytecode in genuine parallel within one process
--- exec() runs code inside the subinterpreter ---
  ran `result = sum(range(10))` inside the subinterpreter
  the code executed in ITS world - the variable 'result' lives in the
  subinterpreter's namespace, not this one
--- isolation: the subinterpreter's globals do NOT leak to main ---
  set 'secret_config' in the subinterpreter
  does main see 'secret_config'? : False
  isolation is the whole point: no shared mutable globals, so one
  interpreter cannot corrupt another's state. that is the SAFETY the
  subinterpreter model buys - the opposite trade from shared-memory threads
--- pass data with a Queue: the sanctioned channel between them ---
  subinterpreter computed 6*7 and put it on the queue
  main received : 42
  because memory is NOT shared, data crosses through an explicit
  Queue of SHAREABLE objects. you pass messages, you do not share
  variables - the discipline that makes the isolation safe
--- only shareable objects cross; arbitrary objects do not ---
  is an int shareable across interpreters? : True
  is an open file object shareable?        : False
  primitives, str/bytes, and some special types (like Queue) are
  shareable; general mutable objects are not - the boundary keeps the
  interpreters truly independent
--- close() releases the subinterpreter when you are done ---
  a subinterpreter is a real resource (its own runtime state), so you
  close it explicitly. create, use, close - lifecycle you control
--- the constraint answered ---
  true parallelism needed either the C API for subinterpreters or the
  no-GIL build. concurrent.interpreters (3.14, PEP 734) put the
  subinterpreter model in the standard library: create isolated
  interpreters, exec code in them, exchange shareable data by Queue.
  parallelism through ISOLATION - the message-passing alternative to
  free-threading's shared memory (Deep L)
```

## Why each part answers the constraint

**An isolated interpreter.**
The first block shows `create()` returning an interpreter with a distinct id from the main one.
Each subinterpreter has its own import state, its own globals, and - since the per-interpreter GIL of Chapter 23 - its own GIL, so several can execute Python bytecode in genuine parallel within a single process.

**Code runs in its world.**
The second block shows `exec("result = sum(range(10))")` running inside the subinterpreter, where the variable lives in *its* namespace, not the main one.
The subinterpreter is a separate execution environment, not a shared scope.

**Isolation is the model.**
The third block demonstrates the defining property: a global `secret_config` set in the subinterpreter is *not* visible in the main interpreter.
No shared mutable globals means one interpreter cannot corrupt another's state.
This is the safety the subinterpreter model buys, and it is exactly the opposite trade from shared-memory threads - where any thread can touch any object.

**Data crosses by Queue.**
The fourth block shows the sanctioned channel: the subinterpreter computes `6 * 7` and `put`s it on a `Queue`, and the main interpreter `get`s `42`.
Because memory is not shared, data crosses through an explicit queue of shareable objects.
You *pass messages*, you do not *share variables* - the discipline that makes the isolation safe, and the same message-passing model that makes multiprocessing and actor systems robust.

**Only shareable objects cross.**
The fifth block shows the boundary: an `int` is shareable across interpreters, an arbitrary object is not.
Primitives, `str`/`bytes`, and special types like `Queue` can cross; general mutable objects cannot.
This restriction is what keeps the interpreters truly independent - you cannot accidentally share a mutable object and reintroduce the data races isolation was meant to prevent.

**Explicit lifecycle.**
The sixth block shows `close()` releasing the subinterpreter.
A subinterpreter is a real resource with its own runtime state, so you manage its lifecycle explicitly: create, use, close.

## The two-track note

The deep comparison - free-threading's shared memory versus subinterpreters' isolation, how each achieves parallelism, the performance and complexity trade-offs, when to choose which - is Deep Volume L's to develop, and it is the heart of the concurrency reckoning.
What the timeline records is the release act: in 3.14, PEP 734 exposed subinterpreters in the standard library as `concurrent.interpreters`, making parallelism-through-isolation reachable from Python.
The modern consequence, verified above, is that Python now offers *two* parallelism models in the standard toolkit - shared-memory free-threading and isolated subinterpreters - and the choice between them is a real architectural decision: isolation (safer, message-passing) versus shared memory (faster data exchange, but you own the synchronization).

## Where this lands

`concurrent.interpreters` is one of the most significant additions of the concurrency-reckoning era, because it makes a whole parallelism model available without C.
Reach for subinterpreters when you want CPU parallelism with *isolation* - independent workers that share nothing and communicate by message, avoiding data races by construction.
Reach for free-threading (or threads) when the work needs shared memory and you are prepared to manage the synchronization.
Pass only shareable data across the boundary, use queues as the channel, and close interpreters when done.
Deep Volume L explains the full free-threading-versus-subinterpreters story; this chapter is the record of the release that put subinterpreters within Python's reach.
