# Chapter 65: Lazy Imports and Startup Time

A command-line tool grows a feature that needs `pandas`, and every invocation, even `mytool --help`, gets
noticeably slower, because the heavy import runs at module load, before `main` even starts. Chapter 63
established that a module's body runs once at first import; the corollary is that *everything imported at
startup is paid before your program does anything*. Measured, a bare interpreter starts in ~23 ms, but importing
a handful of heavy stdlib modules pushes it to ~42 ms, **19 ms of pure import overhead** (1.83x) for five
modules; a large application eagerly importing dozens can spend *hundreds* of milliseconds loading code a given
run may never use. The fix is the **lazy import**: defer a heavy module's load until it is actually used, so a
run that does not touch the feature does not pay to load it.

This chapter continues **Deep G** with lazy imports and startup latency: why eager imports cost startup, how to
defer them (in-function imports and PEP 562 module `__getattr__`), and when it matters (short-lived processes)
versus when it does not (long-running servers). It is the startup-latency counterpart to Chapter 63's per-call
analysis.

## Section index

- **65.1** Deferring a module's load
- **65.2** When lazy imports matter
- **65.3** Measurement: the startup cost of eager imports
- **65.4** Edges and failure modes
- **65.5** Connections
- **65.6** Exercises
- **65.7** Summary and cross-references

Listings live under `code/ch065/` and are re-executed by `make verify` on both interpreters.

---

## 65.1 Deferring a module's load

```python
# code/ch065/l01_lazy_import.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- importing the package does NOT load the heavy submodule ---
  package imported     : True
  heavy loaded yet?    : False
  _lazypkg.heavy in sys.modules: False
--- first access triggers the load (PEP 562 __getattr__) ---
  accessed _lazypkg.heavy.DATA[:1] : [0]
  heavy loaded now?    : True
  _lazypkg.heavy in sys.modules    : True
--- subsequent access is direct (cached; __getattr__ not called again) ---
  same module object   : True
  a run that never touches .heavy pays nothing for it
```

The listing uses **PEP 562**, a package defining a module-level `__getattr__`. Importing `_lazypkg` is cheap and
does *not* load its `heavy` submodule, the load flag is `False` and `_lazypkg.heavy` is absent from
`sys.modules`. The first *access* to `_lazypkg.heavy` invokes the package's `__getattr__`, which imports the
heavy submodule on demand (now the flag is `True` and it is in `sys.modules`). The `__getattr__` caches the
result in the package's namespace, so subsequent accesses are direct attribute lookups, not repeated
`__getattr__` calls. The payoff is the last line: **a run that never touches `_lazypkg.heavy` never loads it**,
and never pays its import cost.

There are two ways to defer an import. The simplest is an **in-function import**: put `import pandas` inside the
function that uses it (Chapter 64's deferral, applied for startup rather than for a cycle), so it loads on first
call. The more ergonomic, for a *library* that wants `import mypkg` to stay cheap while `mypkg.submodule`
transparently loads on demand, is **PEP 562 `__getattr__`** at the package level, as the listing shows. Both
defer the cost from *import time* to *first use*.

---

## 65.2 When lazy imports matter

Lazy imports trade *startup* latency for *first-use* latency, and whether that trade is worth it depends
entirely on the process lifetime.

For a **short-lived process**, a CLI tool, a script run in a loop, a serverless function invoked per request,
startup latency is *user-visible* and *paid every invocation*. A CLI that imports `pandas`, `requests`, and a
cloud SDK at module level makes `--help` take a second, and a serverless function pays that import on every cold
start. Here lazy imports are a real win: defer the heavy imports so the common paths (help text, argument
errors, a lightweight subcommand) start fast, and only the code path that actually needs `pandas` pays for it.

For a **long-running process**, a web server, a daemon, a notebook kernel, startup happens *once* and is
amortized over the process's whole life. A 200 ms import is nothing against days of uptime, and *eager* imports
are often *better*: load everything at startup so the first request is not slowed by a lazy import, and so an
import error surfaces at boot (fail fast) rather than mid-request. Here lazy imports add complexity for no real
benefit and can *hide* an import error until the unlucky first request hits it.

The rule: **lazy-import in short-lived processes and libraries; eager-import in long-running services.** A
library should keep its top-level `import mypkg` cheap (lazy-load heavy optional dependencies via PEP 562) so it
does not tax every importer; an application binary should decide by its lifetime. And measure before optimizing
startup, `python -X importtime` shows exactly which imports cost what, so you defer the ones that actually
matter rather than guessing.

---

## 65.3 Measurement: the startup cost of eager imports

**Methodology.** `code/ch065/bench_startup.py`. Wall-clock of a fresh interpreter running `pass` versus one
importing five heavy stdlib modules (`decimal`, `json`, `xml.etree.ElementTree`, `email`, `http.client`). `min`
over runs. Subprocess/startup timing is OS-bound and noisy, so the ratio, not the absolute time, is the finding.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| interpreter startup | min per run | overhead |
|---|---|---|
| bare (`pass`) | **~23 ms** | 1.00x |
| + eager heavy imports | **~42 ms** | **+19 ms (1.83x)** |

Importing five heavy stdlib modules adds **~19 ms** to startup, nearly doubling it. The bare startup itself
(~23 ms) is the interpreter initializing and importing its own bootstrap modules; the extra 19 ms is *your*
imports running their bodies before `main`. Five modules is modest, a real application's dependency tree
(a web framework, an ORM, a cloud SDK, a data library) can add *hundreds* of milliseconds, all paid before the
program does anything. This is subprocess-timing and noisy, but the direction is unambiguous: eager imports are
startup latency.

The rule: **for anything short-lived, defer heavy imports so startup stays fast.** Profile with `python -X
importtime` to find the expensive imports, then move the ones only some code paths need into those code paths (or
behind PEP 562 lazy loading). For a long-running service, do the opposite, import eagerly at boot so requests are
never slowed and import failures surface immediately. As with the per-call analysis of Chapter 64, the tool
(defer vs eager) follows from *where the cost is paid*: startup for eager, first-use for lazy, and the process
lifetime decides which you want.

---

## 65.4 Edges and failure modes

**Eager heavy imports in a CLI/short-lived process.** §65.3. Paid on every invocation, user-visible. Defer to
first use.

**Lazy imports in a long-running service.** §65.2. No startup benefit (amortized), and they can hide an import
error until the first request that triggers the load. Prefer eager imports at boot for services (fail fast).

**Hidden import errors from deferral.** A deferred import that would fail (missing optional dependency, syntax
error) does *not* fail until the deferring code runs, potentially long after startup, in production, on a rare
path. Test the lazy paths, or validate critical imports at startup even if you defer their heavy use.

**PEP 562 `__getattr__` masking real errors.** A package `__getattr__` that catches too broadly, or raises the
wrong error, can turn a real `ImportError` (broken submodule) into a confusing `AttributeError`. Re-raise import
failures clearly; only synthesize `AttributeError` for genuinely unknown names.

**Repeated in-function imports on a hot path.** An in-function `import` runs a `sys.modules` lookup every call
(~51 ns, Chapter 64). For startup deferral that is fine (the point is to skip the *first* load), but on a hot
loop, bind the module once after first import rather than importing every iteration.

**Circular imports reintroduced by eager loading.** Making a lazy import eager (to fail fast) can resurrect a
circular-import problem the laziness was accidentally avoiding (Chapter 64). Restructure the cycle rather than
depending on lazy timing to dodge it.

---

## 65.5 Connections

**Backward.** The "body runs once at first import" fact this exploits is Chapter 63; lazy imports move *when*
that once happens. The in-function deferral and its per-call cost are Chapter 64. PEP 562 module `__getattr__`
is the module-level analogue of the instance `__getattr__` in the data model (Chapters 4, 16).

**Forward.** Finders, loaders, and `sys.path` (how a deferred import is *located* when it fires) are the rest of
**Deep G**. Import-time profiling (`-X importtime`) and startup optimization connect to the profiling of Chapter
51. Optional-dependency patterns (import a backend lazily, fall back if absent) are a packaging topic (Deep N).

**Across books.** Startup discipline is how Book II keeps its tools and services responsive for **Book III**. A
**Book III** CLI defers heavy model/data imports so `--help` and argument validation are instant, while its
long-running inference *service* imports everything at boot so the first request is not penalized and a missing
dependency crashes the container at startup, not mid-request. The §65.3 startup cost is the reason the CLI and
the service make opposite import choices. **Deep U** owns the startup/latency seam.

---

## 65.6 Exercises

**1. Prove the deferral.** Reproduce §65.1: show importing the package does not load the heavy submodule, and
first access does. Explain PEP 562 `__getattr__` and why the second access does not re-invoke it.

**2. Measure the startup cost.** Run §65.3's benchmark and confirm eager heavy imports add startup time. Then
use `python -X importtime` to attribute the cost to specific modules. Explain what you would defer.

**3. Defer in a CLI.** Take a small tool that imports a heavy module at top level and move the import into the
subcommand that needs it. Show `--help` gets faster while the heavy subcommand is unchanged. Explain the trade.

**4. Catch a hidden error.** Write a deferred import of a nonexistent module and show the error appears only when
the deferring code runs, not at startup. Explain why this is a risk and how to mitigate it.

**5. The design question.** Lazy imports help short-lived processes and hurt (or do nothing for) long-running
ones. Argue how to decide. Your answer must use the §65.3 measurement, contrast startup-cost-per-invocation with
amortized-once, and address the fail-fast argument for eager imports in services.

---

## 65.7 Summary and cross-references

- **Everything imported at startup runs its body before your program does** (Chapter 63), so eager heavy imports
  are **startup latency**.
- **Lazy imports defer the load to first use:** an **in-function import** (loads on first call) or **PEP 562
  package `__getattr__`** (a submodule loads on first attribute access, then caches). A run that never uses the
  feature never loads it.
- **Measured:** importing five heavy stdlib modules adds **~19 ms** to startup (1.83x); real apps can add
  hundreds of ms. Subprocess-noisy, but the direction is clear.
- **Lazy-import in short-lived processes (CLIs, serverless) and libraries; eager-import in long-running services**
  (amortized, fail-fast). Profile with `-X importtime`; beware deferred imports hiding errors.

**Cross-references.** Import caching → Chapter 63. In-function deferral and its cost → Chapter 64. `__getattr__`
data model → Chapters 4, 16. Finders/loaders/`sys.path` → the rest of Deep G. Import profiling → Chapter 51.
Optional dependencies/packaging → Deep N. The startup/latency seam → Deep U.
