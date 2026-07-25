# Chapter 64: Circular Imports

Two modules grow to depend on each other, `models.py` imports `db.py` and `db.py` imports `models.py`, and the
program crashes at startup with a baffling error: `partially initialized module 'models' has no attribute
'User' (most likely due to a circular import)`. The name `User` obviously exists in `models.py`; why can't `db`
see it? Because of Chapter 63's mechanism: `import X` adds `X` to `sys.modules` *before* running its body, so
when `models`'s body imports `db`, and `db`'s body imports `models`, `db` receives a *half-initialized*
`models`, one whose later names (`User`) have not been defined yet. Using such a name *at import time* fails.
The fix is to not *need* the other module's names at import time: **defer the cross-import into the function
that uses it**, by which point both modules are fully loaded. That deferral costs a `sys.modules` cache-hit
lookup per call, ~51 ns measured, a negligible price for breaking the cycle.

This chapter continues **Deep G** with circular imports: why they fail, the deferred-import fix and its small
cost, and the deeper restructuring that removes the cycle. It is the direct consequence of Chapter 63's
"registered before the body finishes" fact.

## Section index

- **64.1** The half-initialized module
- **64.2** Breaking the cycle
- **64.3** Measurement: the cost of a deferred import
- **64.4** Edges and failure modes
- **64.5** Connections
- **64.6** Exercises
- **64.7** Summary and cross-references

Listings live under `code/ch064/` and are re-executed by `make verify` on both interpreters.

---

## 64.1 The half-initialized module

```python
# code/ch064/l01_circular.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- circular import that uses names at import time: FAILS ---
  raised              : AttributeError
  is a circular-import error : True
  names the missing attr     : True
--- the fix: defer the cross-import into the function that needs it ---
  good_a.combined()   : 'AB'
  both modules load; the import happens at call time, fully initialized
```

The listing has two module pairs. The **broken** pair (`circ_bad`) has `mod_a` and `mod_b` each import the other
*and use its names at module level* (`TITLE = "..." + mod_b.b_value()`). Importing `mod_a` runs its body, which
imports `mod_b`, which runs *its* body, which imports `mod_a`, but `mod_a` is already in `sys.modules`
(half-done), so `mod_b` gets the partial module and its `mod_a.a_value()` at import time raises `AttributeError:
partially initialized module ... has no attribute 'a_value'`. The listing confirms the error is exactly this
(`'partially initialized' in msg` and `'a_value' in msg` are both `True`; the full message is not shown because
it contains a machine-specific path).

The **fixed** pair (`circ_good`) works: `good_a.combined()` returns `'AB'`. The difference is *when* the cross-
module name is used, §64.2. The key realization: a circular *import* is not itself an error, Python handles the
cycle by returning the partial module. The error comes from *using a name that is not defined yet*. So the cure
is to defer the *use* (and the import) until after both modules finish loading.

---

## 64.2 Breaking the cycle

There are three ways to break a circular import, in rough order of preference.

**Restructure to remove the cycle (best).** A cycle usually signals that the two modules share something that
belongs in a *third*. Extract the shared types/functions into a `common.py` that both import, and the cycle
disappears. This is the real fix, the cycle is a design smell, and removing it makes the dependency graph a
DAG.

**Defer the import into the function (the listing's fix).** If restructuring is not practical, move the
`import` from module level into the *function* that uses the other module. By the time that function is
*called*, both modules are fully loaded, so the name exists. The listing's `combined()` does `from
ch064.circ_good import mod_a` *inside* the function, and it works. This is the pragmatic, minimal-change fix,
and it costs a per-call `sys.modules` lookup (§64.3).

**Import the module, not its names, and use late binding.** `import models` (then `models.User` at *use* time)
is more cycle-tolerant than `from models import User` (which needs `User` to exist *now*). Because attribute
access is resolved when the code *runs*, not when it is imported, `import models` at top level often survives a
cycle where `from models import User` would fail, provided you only touch `models.User` inside functions.

The principle unifying all three: **do not require the other module's names at import time.** The cycle is safe
as long as every cross-module *use* happens after both bodies have finished, at call time, not at import time.
Prefer restructuring; use deferral when you must.

---

## 64.3 Measurement: the cost of a deferred import

**Methodology.** `code/ch064/bench_deferred_import.py`. A function using a module imported at *top level* (a
global reference) versus one that imports the module *in-function* on every call (a `sys.modules` cache hit).
`min` per call; ratio relative to the top-level version. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| import style | min per call | ratio |
|---|---|---|
| top-level import + use | **24 ns** | 1.00x |
| deferred (in-function) | **75 ns** | **3.16x** |

The in-function import adds **~51 ns per call** (24 ns to 75 ns), the cost of the `sys.modules` cache-hit lookup
(Chapter 63) that runs every call, plus binding the name locally. In *relative* terms it is 3.16x, but the
*absolute* cost is tens of nanoseconds, negligible for the vast majority of code, a function called thousands of
times a second pays microseconds total.

The rule: **deferring an import to break a cycle is cheap; do it without hesitation for correctness.** The 51 ns
matters only on a genuinely hot path called millions of times, and even there the fix is not to accept a
circular-import crash but to **bind the reference once** (import after both modules load and cache the name) or,
better, **restructure to remove the cycle** so no deferral is needed. The measurement's purpose is to retire the
worry: the pragmatic fix has a bounded, tiny price, so choose correctness (defer or restructure) over a fragile
top-level cycle every time.

---

## 64.4 Edges and failure modes

**Using a cross-module name at import time in a cycle.** §64.1. Raises `partially initialized module ... has no
attribute`. Defer the use (and import) to call time, or restructure.

**`from X import name` in a cycle.** More fragile than `import X`, because it binds `name` at import time (when
it may not exist yet). Prefer `import X` and `X.name` at use time when a cycle is unavoidable.

**Deferred import on a hot path.** §64.3. ~51 ns per call. Fine almost always; on a millions-of-calls path, bind
the reference once instead of importing every call, or remove the cycle.

**A cycle hidden by import order.** A circular import may *work* when modules are imported in one order and
*fail* in another (whichever module is imported first finishes its body). This makes the bug order-dependent and
intermittent, appearing only via a particular entry point. Do not rely on import order; fix the cycle.

**Cycles through package `__init__.py`.** A package's `__init__` that imports its submodules, which import from
the package, creates a cycle through `__init__`. Keep `__init__` minimal (or use lazy attribute access, PEP 562
`__getattr__`) to avoid it.

**"Fixing" by moving imports to the bottom of the file.** Placing an `import` at the end of a module (after the
names it needs are defined) sometimes works but is fragile and confusing, it depends on definition order and
breaks silently on edits. Defer into functions or restructure instead; do not rely on bottom-of-file imports.

---

## 64.5 Connections

**Backward.** The "added to `sys.modules` before the body finishes" mechanism that causes the half-initialized
module is Chapter 63, this chapter is its direct consequence. The name-binding at import (`from X import name`)
versus attribute access at use (`X.name`) is the LEGB/namespace model of Chapters 2-3. The `AttributeError` and
its message are Chapter 6.

**Forward.** Package `__init__` and namespace packages, lazy imports (PEP 562 module `__getattr__`), and the
finder/loader machinery are the rest of **Deep G**. The type-checking-only imports (`if TYPE_CHECKING:`) that
avoid runtime cycles for annotations connect to Chapter 16 and Deep I.

**Across books.** Acyclic module structure is how Book II keeps its own codebase, and the code it hands
**Book III**, maintainable. A **Book III** system with a clean dependency DAG (shared types in a base module,
features depending inward) has no circular imports to defer around, and where a cycle is unavoidable at a seam,
it uses a deferred import whose §64.3 cost is nothing against a request's real work. A tangle of circular
imports is a design smell **Deep U** flags at the architecture seam.

---

## 64.6 Exercises

**1. Reproduce the failure.** Build two modules that import each other and use a cross-module name at module
level, and observe the `partially initialized module` error. Explain, in terms of `sys.modules`, what state each
module was in at the moment of failure.

**2. Fix by deferral.** Move the cross-import into the function that uses it and show the pair now works. Explain
why the name exists at call time but not at import time.

**3. Fix by restructuring.** Extract the shared piece into a third module both import, and show the cycle is
gone. Explain why this is the better fix.

**4. Measure the deferral.** Run §64.3's benchmark and confirm the in-function import adds tens of nanoseconds
per call. Explain what that cost is and when it would matter.

**5. The design question.** A circular import is not itself an error, but using a name from a half-initialized
module is. Argue how this shapes the right fix. Your answer must use the §64.1 mechanism and §64.3 cost, rank
restructuring vs deferral vs `import X`-late-binding, and explain why bottom-of-file imports are a fragile
non-fix.

---

## 64.7 Summary and cross-references

- A **circular import fails** when a module uses another's names *at import time*, because `import` registers a
  module in `sys.modules` *before* its body finishes (Chapter 63), so the cycle sees a **half-initialized**
  module missing its later names.
- **A circular import is not itself an error**, using an undefined name from a partial module is. Fix by not
  needing the name at import time.
- **Break the cycle by** (best) restructuring shared pieces into a third module; (pragmatic) deferring the
  cross-import into the function that uses it; or using `import X` + `X.name` at use time rather than `from X
  import name`.
- **Measured:** a deferred (in-function) import costs **~51 ns per call** (a `sys.modules` cache hit), 3.16x a
  top-level reference but negligible in absolute terms. Defer freely for correctness; on a hot path bind once or
  restructure.

**Cross-references.** `sys.modules` and import order → Chapter 63. Name binding vs attribute access → Chapters
2-3. `AttributeError` → Chapter 6. Packages, lazy imports, finders → the rest of Deep G. `TYPE_CHECKING` imports
→ Chapter 16, Deep I. The architecture seam → Deep U.
