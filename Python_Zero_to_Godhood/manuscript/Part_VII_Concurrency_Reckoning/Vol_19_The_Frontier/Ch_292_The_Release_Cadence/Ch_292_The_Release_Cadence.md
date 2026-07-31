# Chapter 292: The Release Cadence

## The frontier

The previous eighteen volumes traced Python's timeline from its origins to Python 3.14.
This volume is different: it is about the *frontier* - Python 3.15 and beyond - which by definition has not fully arrived.
Rather than document unreleased features, these chapters cover what it means to *live at the edge* of a language that keeps moving, and the skills that require.
The first of those skills is understanding the rhythm of change and reading the version you are running on.

Since PEP 602 (adopted for Python 3.9), CPython ships a *feature release every year*, in October, each supported for five years.
This predictable annual cadence is the backdrop for everything this book's timeline described: a steady stream of small, composable changes rather than rare, disruptive leaps.
It is why the later volumes read as a smooth accumulation - f-strings here, a `match` statement there, `batched` in one release, `zstd` in the next - each release modest precisely because they come so often.

The practical demand this cadence creates is the ability to read and compare the running version programmatically, which `sys.version_info` makes precise.

This is the frontier volume's opening: not a mechanism owned by any Deep Volume, but the process by which the language evolves, and the tools for keeping pace.

## What this looks like

`sys.version_info` is a structured, tuple-comparable view of the running version.
Listing 292.1 shows how to interrogate it, reporting structure and comparisons (never the raw version numbers) so the output is stable across the interpreters that run it.

Verified output (CPython 3.13.5):

```text
--- sys.version_info is a structured, comparable version ---
  type is a named tuple : version_info
  has named fields : True
  it IS a tuple, so it compares as one : True
  version_info is not a string to parse but a named tuple you can
  compare directly - major/minor/micro plus releaselevel and serial.
  reading the version is exact, not string-munging
--- compare against a version to gate behaviour ---
  running Python 3 (>= (3, 0)) : True
  at least 3.6 (f-strings)     : True
  before 4.0                   : True
  a tuple comparison is the correct version check: `if
  sys.version_info >= (3, 12):` enables a branch only on new enough
  Python. tuples compare element-wise, so (3, 14) > (3, 9) as expected
--- the annual cadence (PEP 602): a feature release every October ---
  release years : [2020, 2021, 2022, 2023, 2024, 2025]
  every gap is exactly one year : True
  since 3.9 the gap between feature releases is a steady 12 months.
  predictable cadence is why the timeline in this book reads as a
  smooth accumulation - each release is small because they are frequent
--- the support window: five years per release ---
  each feature release gets ~2 years of bugfixes then ~3 of security
  fixes - five years total. so at any time several versions are
  supported at once, which is exactly why writing code that spans
  versions (the next chapter) is a core frontier skill
--- reading the version is how you meet the frontier safely ---
  is the running interpreter at least the newest release in our table : True
  (always true - the point is you TEST the version rather than assume
  it). code that checks sys.version_info adapts to whatever Python it
  runs on, which is what living on an annual-release language requires
--- the constraint answered ---
  an annual release cadence (PEP 602) means features arrive steadily
  and several versions are always supported. sys.version_info gives a
  structured, tuple-comparable view of the running version, so code
  can gate behaviour precisely. reading the version is the first skill
  of working at the frontier - the base the next chapters build on
```

## Why each part matters

**version_info is structured, not a string.**
The first block shows `sys.version_info` is a named tuple with `major`, `minor`, `micro`, `releaselevel`, and `serial` fields, and that it *is* a tuple.
This matters because it means version checks are exact tuple comparisons, not error-prone string parsing of `sys.version`.
You never split and `int()` a version string; you compare tuples.

**Tuple comparison gates behavior.**
The second block shows the idiom: `sys.version_info >= (3, 0)`, `>= (3, 6)`, `< (4, 0)`.
Because tuples compare element-wise, `(3, 14) > (3, 9)` as expected, so `if sys.version_info >= (3, 12):` enables a branch only on a new-enough Python.
This is the correct, precise way to gate version-dependent behavior - the foundation the next chapter builds on.

**The annual cadence.**
The third block encodes the release years from 3.9 to 3.14 and confirms every gap is exactly one year.
Since 3.9, feature releases are a steady twelve months apart.
This predictability is what makes the language's evolution plannable - and it is the structural reason each release in this book's later timeline is small: they are frequent, so no single one needs to carry much.

**The five-year support window.**
The fourth block notes each feature release's five-year support life (roughly two years of bugfixes, three of security fixes).
The consequence is that *several versions are always supported at once* - so at any moment, real-world code must run across a span of Python versions, which is exactly why writing version-spanning code is a core frontier skill.

**Test, don't assume.**
The fifth block makes the meta-point: the tautological check is always true because the point is that you *test* the version rather than assume it.
Code that reads `sys.version_info` adapts to whatever Python it runs on, which is what living on an annual-release language requires.

## Where this lands

The release cadence is the metronome behind the entire timeline this book documented.
Understanding it reframes the whole history: Python did not lurch forward in a few big jumps but accumulated capability steadily, one modest release a year, each supported long enough that the ecosystem could move at its own pace.
Reach for `sys.version_info` - a comparable tuple, never a parsed string - whenever behavior depends on the Python version.
This chapter opened the frontier volume with the process itself; the next chapters cover the skills it demands: writing code that spans versions, navigating experimental builds, and recognizing what stays constant as everything else changes.
