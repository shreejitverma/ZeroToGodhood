# Chapter 63: Import Caching

A developer worried about startup time moves an expensive table-building computation out of module level and
into a function "so it does not run on every import," and makes the program *slower*, because now the table is
rebuilt on every *call* instead of once. The misunderstanding is about what `import` does. `import X` does not
"run X.py"; it ensures `X` is in `sys.modules`, executing the module body **only if it is not already there**. A
module's top-level code is a *one-time initializer*: it runs once per interpreter, on first import, and every
later `import` of the same module is a `sys.modules` dictionary lookup returning the same object. Measured, a
cached import is **224 ns** (a dict lookup), while re-executing the module body (via `reload`) is **~56 us**,
**249x** slower, and that gap widens with how heavy the body is. Expensive import-time work is paid *once*;
moving it into a per-call function pays it *every time*.

This chapter opens **Deep G** (the import system) with import caching: how `sys.modules` makes import idempotent,
why module-level code is a one-time initializer, and the design consequences. It builds on the module and
namespace mechanics touched throughout the book and underlies circular imports, lazy imports, and startup-time
tuning (the rest of Deep G).

## Section index

- **63.1** `import` runs the body once
- **63.2** Why module-level code is a one-time initializer
- **63.3** Measurement: cached import vs re-execution
- **63.4** Edges and failure modes
- **63.5** Connections
- **63.6** Exercises
- **63.7** Summary and cross-references

Listings live under `code/ch063/` and are re-executed by `make verify` on both interpreters.

---

## 63.1 `import` runs the body once

```python
# code/ch063/l01_import_caching.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- first import runs the body ---
  body executions so far : 1
  in sys.modules         : True
  TOTAL computed at import: 332833500
--- repeated imports are cache hits: the body does NOT re-run ---
  same module object     : True
  body executions so far : 1 (still 1)
--- reload is the only way to re-run the body ---
  body executions so far : 2 (now 2)
  a cached import is a sys.modules lookup; the body cost is paid once
```

The helper module increments a counter each time its *body* actually executes. The first `import` runs the body
(counter = 1), computes its `TOTAL` at import time, and registers the module in `sys.modules`. **Repeated
imports do not re-run the body**: a second `import` statement, and `importlib.import_module`, all return the
*same module object* (identity is `True`) and the counter stays at 1. The module's code ran exactly once, no
matter how many times it is imported. Only `importlib.reload` forces the body to execute again (counter = 2),
which is why `reload` exists as an explicit, rarely-needed operation.

The mechanism is simple and worth stating precisely: `import X` checks `sys.modules["X"]`; if present, it binds
the name and stops; if absent, it *finds and loads* the module, runs its body, stores it in `sys.modules`, and
then binds the name. So `sys.modules` is a process-wide cache of loaded modules, and import is *idempotent*, ten
imports cost the same module-body execution as one.

---

## 63.2 Why module-level code is a one-time initializer

The consequence reframes how to think about module-level code. It is **not** run "on every import"; it is run
**once**, the first time anything imports the module, and its results, module-level names, become shared state
that every importer sees. This makes module level the *correct* home for expensive one-time setup: compiling a
regular expression, loading a data file, building a lookup table, establishing a constant, precisely the work the
chapter-opening developer wrongly moved into a function.

The trade is the reverse of the usual "avoid work at import." Work at module level is paid **once and shared**;
work in a function is paid **on every call**. So a table built at module level and referenced by many calls is
built once; the same table built inside the function that uses it is rebuilt per call, which is the slower
pattern §63.3 makes concrete. The guidance: **put expensive, call-invariant setup at module level (or behind a
module-level cache) so import caching pays for it once.** The costs of a heavy import are real (they affect
*startup* latency, addressed by lazy imports later in Deep G), but they are not per-*use* costs, and confusing the
two leads to exactly the pessimization the chapter opened with.

This also explains why import order and circular imports matter (a module half-way through its body is already in
`sys.modules`, so a circular import sees a *partially initialized* module, a Deep G topic), and why global mutable
state in a module is shared across all importers (the module object is a singleton).

---

## 63.3 Measurement: cached import vs re-execution

**Methodology.** `code/ch063/bench_import_cache.py`. `importlib.import_module` on an already-loaded module (a
`sys.modules` hit) versus `importlib.reload` (which re-executes the module body, here building a 1000-element
list). `min` per call; ratio relative to the cached import. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | min per call | ratio |
|---|---|---|
| cached import (`sys.modules` hit) | **225 ns** | 1.00x |
| `reload` (re-runs the body) | **~56,000 ns** | **249x** |

A cached import is **225 ns**, a dictionary lookup returning the existing module object, and this cost is
*independent* of how expensive the module was to load. Re-running the body via `reload` costs **~56 us** here,
**249x** more, and that figure is only as large as the helper's modest body (1000 squares); a module that loads a
data file or compiles many regexes would make the gap far larger. The measurement is the point of §63.2 made
concrete: the body cost is a *one-time* charge, and after that, import is free.

The rule: **do expensive, call-invariant setup once, at module level, and let import caching amortize it to
nothing across all importers and all calls.** Do not move module-level initialization into a per-call function to
"speed up import", that trades a one-time cost for a per-call one. When *startup* latency (the one-time cost
itself) matters, the tool is a *lazy* import (defer the import until first use, Deep G), not relocating the work
into a hot path. And never rely on re-import to re-run initialization; import is idempotent, use an explicit
`reload` (rare) or a function if you genuinely need repeatable setup.

---

## 63.4 Edges and failure modes

**Moving module-level setup into a per-call function.** §63.3. Trades a one-time cost for a per-call one. Keep
call-invariant setup at module level (or in a `functools.cache`d function, Chapter 34).

**Expecting re-import to re-run code.** §63.1. `import` is idempotent; a second import is a cache hit and does
*not* re-run the body. Use `importlib.reload` (deliberately, rarely) to re-execute, and know it can leave stale
references in code that imported names directly.

**Circular imports seeing a half-initialized module.** Because a module is added to `sys.modules` *before* its
body finishes, a circular import can retrieve a module whose names are not all defined yet, raising
`ImportError` or `AttributeError`. Restructure to break the cycle (import inside a function, or split the shared
part into a third module), a Deep G topic.

**Module-level side effects.** Since the body runs on first import, side effects at module level (opening files,
network calls, printing, mutating globals) happen at import time, sometimes surprisingly early or in the wrong
process. Keep import-time work to pure setup; defer side effects to explicit calls.

**Mutable module-level state is shared.** The module object is a process-wide singleton, so a mutable global is
shared by every importer. This is a feature (shared config, caches) and a hazard (accidental cross-module
coupling). Prefer immutable module-level constants; make shared mutable state explicit.

**`reload` does not update existing references.** `importlib.reload(m)` rebinds names *in* `m`, but code that did
`from m import thing` still holds the *old* `thing`. `reload` is a development aid, not a hot-swap mechanism; do
not build reload-based live updates casually.

---

## 63.5 Connections

**Backward.** The `dict` that `sys.modules` is, and its O(1) lookup, are Chapter 32 and Deep P. The one-time-
setup-then-reuse pattern is the memoization theme of Chapter 34 (`functools.cache`), applied at module scope. The
namespace and name-binding mechanics are Chapters 2-3 (LEGB) and the object model of Chapter 4.

**Forward.** The rest of **Deep G**: the finder/loader machinery and `sys.path` (how a module is *located*),
packages and namespace packages, circular imports in depth, and lazy imports for startup latency. The bytecode
cache (`.pyc` files in `__pycache__`) that speeds re-parsing is a related Deep G/Deep J topic.

**Across books.** Import caching is how Book II pays for heavy setup once on the way to **Book III**. A
**Book III** service loads models, compiles prompts/regexes, and builds lookup tables at module import (or behind
a module-level cache), so the cost is paid once at startup and every request shares the result, rather than
rebuilding per request. The §63.3 one-time-vs-per-call distinction is the reason initialization lives at module
level and hot paths stay lean. **Deep U** owns the service-startup seam.

---

## 63.6 Exercises

**1. Prove the one-time body.** Write a module that increments a counter in its body and import it several ways;
show the counter stays at 1 and all imports return the same object. Then `reload` and show the counter advance.
Explain the `sys.modules` mechanism.

**2. Reproduce the cost gap.** Run §63.3's benchmark and confirm a cached import is far cheaper than re-running
the body. Make the module's body heavier and show the gap widens. Explain why the cached import cost is
independent of the body's weight.

**3. Pessimize on purpose.** Build a table at module level and time a function that uses it; then move the table-
building inside the function and time again. Show the second is slower per call. Explain the one-time-vs-per-call
trade.

**4. Trip a circular import.** Create two modules that import each other at top level and observe the
`ImportError`/`AttributeError` from the half-initialized module. Fix it by importing inside a function. Explain
what `sys.modules` contained at the moment of failure.

**5. The design question.** `import` is idempotent and caches modules in `sys.modules`, making module-level code a
one-time initializer. Argue why this is the right design. Your answer must use the §63.3 measurement, explain why
moving setup into a per-call function is usually wrong, and distinguish import-time (startup) cost from per-call
cost.

---

## 63.7 Summary and cross-references

- **`import X` runs the module body only once**, on first import, then caches the module in `sys.modules`; every
  later import is a **dict lookup** returning the same object. Import is **idempotent**.
- **Module-level code is a one-time initializer:** its results are shared by all importers. Expensive, call-
  invariant setup belongs there (paid once), not in a per-call function (paid every call).
- **Measured:** a cached import is **225 ns** (independent of the module's load cost); re-running the body
  (`reload`) is **~249x** more, and the gap grows with the body's weight.
- **Edges:** `import` does not re-run code (use `reload`, deliberately); circular imports see a half-initialized
  module; module-level side effects run at import time; mutable module globals are shared singletons.

**Cross-references.** `dict`/`sys.modules` → Chapter 32; Deep P. Memoization → Chapter 34. Namespaces/LEGB →
Chapters 2-3. Finders/loaders, packages, circular imports, lazy imports → the rest of Deep G. `.pyc` cache → Deep
J. The service-startup seam → Deep U.
