# Chapter 294: The Free-Threaded Frontier

## The frontier

Volume 17 introduced the free-threaded (no-GIL) build as a landmark of the concurrency reckoning.
Here at the frontier, the question turns practical: *how do you know you are on it, and what does your code owe that world?*

For thirty years, the Global Interpreter Lock let Python threads share memory freely while quietly serializing their execution of bytecode.
That serialization was a limitation - it prevented pure-Python code from using multiple cores - but it was also a *convenience*: because a thread rarely lost the CPU in the middle of a short bytecode sequence, a great deal of unsynchronized shared-state code *happened* to work.
Not because it was correct, but because the GIL made the race unlikely to surface.

On a free-threaded build, that convenience is gone.
`sys._is_gil_enabled()` returns `False`, threads run bytecode in genuine parallel, and code that got away with unsynchronized updates can now *race* and lose data.
The discipline the frontier demands is the one C and Java programmers have always owed: guard shared mutable state with a lock, or design to share nothing.

This is the practitioner's companion to Deep Volume L, which owns the full model.

## What this looks like

Listing 294.1 detects the build and demonstrates the locking discipline.
It runs only on the free-threaded build (gated by `# requires: free-threaded`).

Verified output (CPython 3.14t):

```text
--- detecting the free-threaded build ---
  sys._is_gil_enabled() : False
  sysconfig Py_GIL_DISABLED : 1
  the GIL is OFF: threads execute Python bytecode truly in parallel.
  these two checks are how code detects the build at runtime and at
  build-configuration time respectively
--- the contract: shared mutable state now needs explicit locking ---
  8 threads x 10000 locked increments = 80000
  the total is exactly correct : True
  `with lock:` serialises the read-modify-write, so no update is lost
  even with 8 threads running in parallel. this is the discipline the
  no-GIL world requires - protect shared mutable state yourself
--- why it matters: the GIL used to hide the race ---
  `counter += 1` is load, add, store - THREE bytecode steps. under the
  GIL, a thread rarely lost the CPU mid-sequence, so unsynchronised
  increments usually (not always) worked. with the GIL gone, two
  threads can interleave those steps and lose updates. the lock was
  ALWAYS the correct fix; free-threading makes skipping it visibly wrong
--- the frontier trade, stated plainly ---
  free-threading buys real multi-core parallelism for pure-Python
  CPU-bound work - the thing the GIL denied for 30 years. the price is
  that you now owe the same thread-safety discipline as C or Java:
  locks, or immutable/shared-nothing designs (the subinterpreter path,
  Chapter 287). the GIL's convenience is gone with its limitation
--- the constraint answered ---
  at the frontier, free-threading is real: detect it with
  sys._is_gil_enabled(), and honour its contract by synchronising
  shared mutable state - the GIL no longer does it for you. genuine
  parallelism in exchange for genuine thread-safety responsibility.
  Deep L develops the model; this is the practitioner's version
```

## Why each part matters

**Detecting the build.**
The first block shows the two checks: `sys._is_gil_enabled()` returns `False` at runtime, and `sysconfig.get_config_var("Py_GIL_DISABLED")` is `1` at build-configuration time.
These are how code knows it is on a no-GIL build - the runtime check for adapting behavior, the build-config check for tooling and packaging.
On this build, the GIL is off and threads execute Python bytecode truly in parallel.

**The locking contract.**
The second block runs the correct pattern: eight threads each perform 10,000 `counter += 1` increments *under a lock*, and the total is exactly 80,000.
`with lock:` serializes the read-modify-write, so no update is lost even with eight threads running in parallel.
This is the discipline the no-GIL world requires - you protect shared mutable state yourself, because nothing else does.

**Why the GIL hid the race.**
The third block explains what changed.
`counter += 1` is three bytecode steps - load, add, store - and under the GIL a thread rarely lost the CPU mid-sequence, so unsynchronized increments *usually* (not always) worked.
With the GIL gone, two threads can interleave those steps and lose updates.
The crucial point: the lock was *always* the correct fix.
Free-threading did not create the bug; it removed the accident that hid it, making the missing synchronization *visibly* wrong instead of latently wrong.

**The trade, plainly.**
The fourth block states the bargain.
Free-threading buys real multi-core parallelism for pure-Python CPU-bound work - the thing the GIL denied for thirty years.
The price is that you now owe the same thread-safety discipline as C or Java: locks, or immutable and shared-nothing designs (the subinterpreter path of Chapter 287).
The GIL's convenience departs with its limitation - you cannot have the parallelism without the responsibility.

## Where this lands

The free-threaded frontier is where Python's oldest concurrency limitation is finally lifting, and it comes with a shift in what correct code looks like.
Detect the build with `sys._is_gil_enabled()` when your code's correctness or performance depends on it.
Honor the contract: guard every shared mutable object with a lock, or choose a design that shares nothing - message-passing, immutability, or subinterpreters.
The reflex that "the GIL protects me" is retiring; the reflex that "shared mutable state needs synchronization" is the one to carry forward, because it was always the true one.
Deep Volume L develops the full free-threading model; this chapter is the frontier practitioner's version - detect the build, respect its contract, and take the parallelism the language spent thirty years working toward.
