# Chapter 293: Writing Across Versions

## The frontier

Chapter 292 established the annual release cadence and the five-year support window, which together mean that at any moment *several* Python versions are in active use.
Real code - a library published to the world, a service deployed across a heterogeneous fleet - must run on a *range* of versions.
And it must do so well: use a new feature where it exists, and degrade gracefully where it does not.

This is a core skill of living at the frontier, and there are two disciplined approaches.
**Feature detection** asks whether the *capability* exists.
**Version gating** asks whether the *Python version* is new enough.
Feature detection is usually the better tool, because it tests the thing you actually need rather than a version number that only *correlates* with it - but version gating is unavoidable for syntax changes, which cannot be detected at runtime because the code would not parse.

This chapter is not about a mechanism any Deep Volume owns; it is about the discipline of spanning versions.

## What this looks like

Listing 293.1 shows the patterns - `hasattr`, `try`/`import`, and `sys.version_info` guards - on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- feature detection with hasattr: test the capability itself ---
  str has removeprefix : True
  strip_prefix('unhappy', 'un') : 'happy'
  hasattr asks 'does this method EXIST?' - the exact question. the
  code uses the builtin when present and a hand-written fallback
  otherwise, so it is correct on every version without a version check
--- try/import: detect a module the same way ---
  TOML parser resolved to : tomllib (standard library)
  try/except ImportError picks the stdlib module where it exists and
  falls back to a backport otherwise - the standard way to support a
  feature that graduated FROM a package INTO the stdlib
--- version gating: when detection is not possible ---
  target the 3.12+ path? : True
  some changes are SYNTAX (like PEP 701 f-strings or 3.14's t-strings),
  which you cannot hasattr - the code would not even parse on an old
  Python. those you gate by version, often by isolating the new syntax
  in a module imported only on new enough interpreters
--- prefer feature detection over version gating where you can ---
  a version check says 'Python is >= 3.9', which only CORRELATES with
  'removeprefix exists'. hasattr(str, 'removeprefix') tests the truth
  directly - so it also works on a backport, a patched build, or an
  alternative implementation. detect the capability, not the version
--- the __future__ ledger tells you what became default when ---
  __future__.division became mandatory in : 3.0
  __future__ (Chapter 240) records which once-optional behaviours are
  now the default and since when - a machine-readable history of the
  language's forward motion, useful when reasoning about old code
--- the constraint answered ---
  supporting many live versions means using new features where present
  and degrading where absent. feature detection (hasattr, try/import)
  tests the capability directly and is preferred; version gating
  (sys.version_info) covers syntax changes detection cannot reach.
  together they let one codebase span the frontier and the past
```

## Why each part matters

**Feature detection with `hasattr`.**
The first block detects `str.removeprefix` (which arrived in 3.9, Chapter 268) with `hasattr`, using the builtin when present and a hand-written fallback otherwise.
`hasattr` asks the exact question - "does this method exist?" - so the code is correct on every version without ever naming a version number.
This is the cleanest form of version-spanning code: the fallback path and the fast path coexist, selected by the capability itself.

**`try`/`import` for modules.**
The second block detects a *module* the same way: `import tomllib` (stdlib since 3.11, Chapter 277), falling back to the third-party `tomli` backport if absent.
This `try`/`except ImportError` pattern is the standard way to support a feature that *graduated from a package into the standard library* - a common trajectory (Chapter 277's `tomllib`, Chapter 250's `unittest.mock`), where the same capability lives in the stdlib on new Pythons and in a package on old ones.

**Version gating for syntax.**
The third block covers what detection *cannot* reach.
Some changes are *syntax* - PEP 701's f-string relaxations, 3.14's t-strings, the `match` statement - and you cannot `hasattr` a syntax feature, because code using it would fail to *parse* on an older Python before any check could run.
Those you gate by `sys.version_info`, typically by isolating the new syntax in a module imported only on a new-enough interpreter, so the old interpreter never tries to parse it.

**Prefer detection.**
The fourth block states the principle.
A version check says "Python is >= 3.9," which only *correlates* with "removeprefix exists."
`hasattr(str, "removeprefix")` tests the truth *directly*, so it also works on a backport, a patched build, or an alternative Python implementation where the version number might not tell the whole story.
Detect the capability, not the version, whenever the capability is detectable.

**The `__future__` ledger.**
The fifth block returns to `__future__` (Chapter 240) as a machine-readable record: `__future__.division` became mandatory in 3.0.
The module documents which once-optional behaviors are now default and since when - a history of the language's forward motion that is occasionally useful when reasoning about old code's behavior.

## Where this lands

Writing across versions is the everyday reality of an annual-release language with a long support tail.
Reach for feature detection first - `hasattr` for attributes and methods, `try`/`except ImportError` for modules - because it tests exactly what you depend on and is robust to backports and alternative implementations.
Fall back to `sys.version_info` gating only when the change is *syntax* that detection cannot reach, and then isolate the new syntax so old interpreters never parse it.
This is the second frontier skill, built on the first (reading the version, Chapter 292): together they let one codebase serve both the newest release and the supported past.
The next chapters continue the frontier: navigating experimental builds, and recognizing what stays constant while all this changes.
