# Chapter 33: Finalizers

Reference counting (Chapter 31) gives Python something most garbage-collected languages lack: prompt, deterministic destruction, an object dies the instant its last reference goes away.
It is tempting to build cleanup on that, put the "close the file, release the handle" logic in `__del__`, and trust it to run at the right moment.
This chapter is about why that temptation is a trap, and what to reach for instead.
`__del__` is Python's *finalizer*, and it is the least reliable of the three cleanup tools, an exception inside it is silently swallowed, its timing is unspecified for objects in cycles, it can resurrect the object it was meant to clean up, and, as the measurement shows, merely defining it makes every instance of the class **1.45x** more expensive to destroy.

The two reliable alternatives are the point of the chapter.
For cleanup tied to a *scope*, the **context manager** (`with`) is deterministic by construction and has no per-object cost, it is the correct default.
For cleanup tied to an object's *lifetime* (when you genuinely need "do this when the object is collected"), **`weakref.finalize`** is the robust tool: it runs exactly once, at collection or at interpreter exit, is idempotent, reports whether it has run, and does not keep the object alive.
The rule that falls out is blunt: **prefer `with`; use `weakref.finalize` when you need lifetime-based cleanup; avoid `__del__`.**

**This is the canonical home for finalization.**
It builds on Chapter 31 (`__del__` fires at refcount zero, and is delayed for cycles), Chapter 30 (finalizers in cycles), and Chapter 29 (`weakref`, which `finalize` is built on). It complements the context-manager protocol (`__enter__`/`__exit__`) taught with `with`.

## Section index

- **33.1** `__del__`'s pitfalls, and `weakref.finalize`'s guarantees
- **33.2** The three cleanup tools, ranked
- **33.3** Measurement: the cost of defining `__del__`
- **33.4** Edges and failure modes
- **33.5** Connections
- **33.6** Exercises
- **33.7** Summary and cross-references

Listings live under `code/ch122/` and are re-executed by `make verify` on both verification interpreters.

---

## 33.1 `__del__`'s pitfalls, and `weakref.finalize`'s guarantees

```python
# code/ch122/l01_finalizers.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- __del__ pitfall: an exception in __del__ is SWALLOWED ---
  the ValueError went to stderr, not raised : True
  program continued normally             : True
--- weakref.finalize: a reliable, once-only finalizer ---
  finalize registered, alive : True
  del r (drops the last reference):
  finalize ran: cleaning up db
  finalize alive after del   : False   (it ran)
--- weakref.finalize is idempotent: calling again does nothing ---
  finalize ran: cleaning up cache
  second explicit call returned : None   (already finalized)
--- the rule ---
  prefer 'with' for deterministic cleanup; use weakref.finalize for
  reliable at-collection cleanup; avoid __del__ (fragile, swallows errors)
```

**`__del__` swallows exceptions.**
A `ValueError` raised inside `Fragile.__del__` does not propagate, it is printed to `stderr` as "Exception ignored in..." and the program continues as if nothing happened.
The listing captures that `stderr` to confirm the error was written there, not raised.
This is by necessity (an exception during destruction has nowhere sane to go, the destroying operation may be deep in the interpreter), but the consequence is that **a bug in `__del__` fails silently**: your cleanup did not happen, and nothing told you.
For cleanup that *matters*, silent failure is the worst possible mode.

**`weakref.finalize` is reliable.**
`weakref.finalize(obj, func, *args)` registers `func` to run when `obj` is collected.
It is everything `__del__` is not: it runs **exactly once**, its `.alive` attribute tells you whether it has run yet, calling it **explicitly** runs it early (and a second call is a harmless no-op, returning `None`), and it does **not** keep `obj` alive (it holds a weak reference).
The output shows it firing at `del r`, reporting `alive = False` afterward, and being idempotent on the second explicit call.
Because the finalizer's function and arguments are stored *separately* from the object (not as a method on it), it also avoids a classic `__del__` trap: a `__del__` method that references `self` participates in any cycle the object is in, whereas a `finalize` callback with plain arguments does not.

The `finalize` callback also runs **at interpreter exit** for any object still alive, giving a reliable "clean up at the end" hook that `__del__` does not reliably provide (objects alive at shutdown may not have `__del__` called).

---

## 33.2 The three cleanup tools, ranked

Finalization in Python is a choice among three tools, and they rank clearly by reliability.

**1. Context managers (`with`), the default.**
`__enter__`/`__exit__` give **deterministic** cleanup bound to a *scope*: the resource is released when the `with` block exits, on success *or* exception, at a point you can see in the source.
There is no dependence on when the object is collected, no per-object cost, and no silent failure (an exception in `__exit__` propagates).
For anything with a clear acquire/release lifetime, a file, a lock, a connection, a transaction, `with` is the right and idiomatic tool.
Most cleanup should be here.

**2. `weakref.finalize`, for lifetime-based cleanup.**
When cleanup is genuinely tied to the object's *lifetime* rather than a scope, the object may outlive many scopes and be held by various owners, `weakref.finalize` is the robust choice.
It is reliable, once-only, idempotent, runs at collection or interpreter exit, and (per §33.1) does not entangle itself in the object's reference graph.
Use it for "release this OS resource whenever this object finally goes away."

**3. `__del__`, rarely and carefully.**
`__del__` is the low-level finalizer the others are better than.
Its problems, silent exception swallowing (§33.1), unspecified timing and ordering for objects in cycles (Chapter 30), the ability to resurrect the object, and a per-object cost (§33.3), make it a poor default.
It is occasionally the only option (a C-extension type, a case where `weakref` is unavailable), but for ordinary Python code the other two dominate it.

The rule: **`with` for scope-based cleanup; `weakref.finalize` for lifetime-based cleanup; `__del__` almost never.**
The instinct to write `__del__` for cleanup is usually a `with` or a `finalize` in disguise.

---

## 33.3 Measurement: the cost of defining `__del__`

Beyond its unreliability, `__del__` is not free, and the cost is per-object, on every instance of the class.

**Methodology.** `code/ch122/bench_del_cost.py`.
Create-and-destroy churn of a `__slots__` class *with* an (empty) `__del__` versus an identical class *without* one, `min` of 5 runs, 2,000,000 lifecycles.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| create + destroy | ns/lifecycle | vs no `__del__` |
|---|---|---|
| no `__del__` | 52.5 | 1.0x |
| with `__del__` | 75.8 | **1.45x** |

Merely *defining* `__del__`, even an empty one, makes each object **1.45x** more expensive over its lifecycle (1.49x on 3.14.6).
The reason is that destroying an object with a finalizer is not a plain deallocation: the interpreter must invoke the finalizer (with the machinery to catch and report any exception, §33.1), and objects with `__del__` historically required special handling in cyclic collection (Chapter 30).
So a class with a `__del__` taxes *every* instance's destruction, whether or not the finalizer does anything useful.

The finding sharpens the ranking of §33.2.
`__del__` is not only *unreliable* (silent failures, cyclic-timing issues) but also *costly* (1.45x per object), a rare case where the fragile tool is also the slow one, so there is no axis on which it wins for ordinary cleanup.
A **context manager** has *zero* per-object cost (the cleanup is scope code, not object machinery) and is deterministic, the best of both.
**`weakref.finalize`** puts the cost only on the objects you actually register a finalizer for, not on every instance of a class, and is reliable.
So the performance argument and the correctness argument point the same way: reach for `with` first, `weakref.finalize` when lifetime-based, and leave `__del__` for the rare cases nothing else covers.
This is the recurring shape of Deep A/B, the tempting-but-magical tool (here `__del__`) costs more and does less than the explicit alternatives.

---

## 33.4 Edges and failure modes

**`__del__` swallows exceptions.** §33.1.
A failing `__del__` writes to `stderr` and continues, your cleanup silently did not happen. Never rely on `__del__` for cleanup that must succeed.

**`__del__` timing is unspecified in cycles.** §33.2, Chapter 30.
For an object in a reference cycle, `__del__` runs only when the cyclic collector reclaims the cycle (later, unspecified order). It is not prompt for cyclic objects.

**`__del__` can resurrect the object.**
If `__del__` stores `self` somewhere reachable, the object comes back to life, and `__del__` will run *again* when it dies once more (unlike `weakref.finalize`, which runs once). This is a subtle source of double-cleanup bugs.

**`weakref.finalize` requires a weak-referenceable object.**
The object must support weak references (Chapter 29), which classes do by default but `__slots__` classes do *not* unless they include `"__weakref__"`. Some built-in types (`int`, `str`, plain `tuple`) are not weak-referenceable.

**Do not reference the object from its own finalizer callback.**
Passing `self` (or a bound method of the object) as the finalizer callback keeps the object alive (a strong reference), defeating the point. Pass the *data the cleanup needs* as plain arguments, not the object, exactly as §33.1 does.

**Context managers do not help object-lifetime cleanup.**
If a resource's lifetime does not match a lexical scope (it is stored in a long-lived structure, passed around, owned by different code over time), `with` cannot express it, that is when `weakref.finalize` is right.

**Cleanup at interpreter exit is best-effort.**
`weakref.finalize` callbacks run at exit, but module teardown order at shutdown can make some resources already-invalid. For critical shutdown cleanup, prefer explicit teardown (or `atexit`) over relying on finalization.

**A `__del__` defined for one instance affects the class.**
Special methods are looked up on the type (Chapter 20), so `__del__` is a class-level concern, and its 1.45x cost applies to *every* instance, not just ones you care about finalizing.

---

## 33.5 Connections

**Backward.**
`__del__` firing at refcount zero (and its delay for cycles) is Chapters 31 and 30. `weakref.finalize` is built on weak references (Chapter 29), which is why it does not keep the object alive. `__del__` being looked up on the type is Chapter 20. The context-manager alternative is the `with`/`__enter__`/`__exit__` protocol.

**Forward.**
`contextlib` (`@contextmanager`, `ExitStack`, `closing`) for building context managers ergonomically is a **Deep** library topic. `atexit` for program-shutdown hooks, and the module-teardown ordering issues at interpreter exit, connect to the runtime-services volume. Finalizers in cyclic structures and PEP 442 (safe finalization of cycles) are Chapter 30.

**Across books.**
Deterministic cleanup is a reliability requirement in **Book I**: an order that must be acknowledged, a lock that must be released, a market-data subscription that must be cancelled, all use `with` so that cleanup happens exactly when the scope ends, even on an exception, rather than "whenever the object is collected." The order-book system manages its OS resources (sockets, memory maps, file handles) with context managers for scope-bound lifetimes and `weakref.finalize` for the few resources whose lifetime is tied to a long-lived object's, and it avoids `__del__` entirely, both for the §33.1 reliability and the §33.3 per-object cost on the millions of small objects its hot path creates.

---

## 33.6 Exercises

**1. See the swallow.** Reproduce §33.1's `Fragile`: raise in `__del__`, capture `stderr`, and confirm the exception was written there, not raised. Explain why the interpreter must swallow it, and why that makes `__del__` unsafe for real cleanup.

**2. Use `finalize`.** Register a `weakref.finalize` on an object, confirm `.alive`, drop the object and confirm the callback ran and `.alive` is now `False`. Call it explicitly on a second object and show the second call is a no-op. Explain the once-only guarantee.

**3. Compare the three.** Implement the same "release a resource" cleanup three ways (context manager, `weakref.finalize`, `__del__`). Show the context manager is deterministic, `finalize` is reliable-but-at-collection, and `__del__` swallows a raised error. State which you would ship and why.

**4. Measure the tax.** Reproduce §33.3. Confirm defining `__del__` adds ~1.45x per lifecycle. Explain what the interpreter must do at destruction for a `__del__` object that it skips for a plain one.

**5. The design question.** Python offers three finalization tools of decreasing reliability (`with` > `weakref.finalize` > `__del__`). Argue why `__del__` exists at all given its problems, and when it is genuinely the only option. Then argue why `with` should be the default, using both the determinism of §33.2 and the cost of §33.3.

---

## 33.7 Summary and cross-references

- **`__del__` is a fragile finalizer:** it **swallows exceptions** (silent cleanup failure), has **unspecified timing in cycles**, can **resurrect** the object, and (measured) makes every instance **1.45x** more expensive to destroy. Avoid it for real cleanup.
- **`weakref.finalize(obj, func, *args)`** is reliable: runs **once**, at collection or interpreter exit, is **idempotent**, reports `.alive`, and does **not** keep the object alive (pass data, not `self`).
- **Rank the tools:** **context managers (`with`)** for scope-based cleanup (deterministic, zero per-object cost, the default) > **`weakref.finalize`** for lifetime-based cleanup > **`__del__`** almost never.
- **The performance and correctness arguments agree:** `with` is deterministic and free, `finalize` is reliable and costs only registered objects, `__del__` is unreliable *and* taxes every instance.
- **Edges:** `finalize` needs a weak-referenceable object (`__slots__` needs `"__weakref__"`); never pass `self` as the callback; interpreter-exit cleanup is best-effort; `__del__` is a class-level cost.

**Cross-references.** `__del__` at refcount zero and cyclic delay → Chapters 31, 30. `weakref` (what `finalize` builds on) → Chapter 29. Special-method lookup on the type → Chapter 20. `contextlib`, `atexit`, shutdown ordering → runtime-services volume. Safe finalization of cycles (PEP 442) → Chapter 30.
