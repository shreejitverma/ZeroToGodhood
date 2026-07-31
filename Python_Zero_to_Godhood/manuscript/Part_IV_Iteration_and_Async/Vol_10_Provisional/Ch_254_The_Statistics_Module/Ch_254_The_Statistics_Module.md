# Chapter 254: The Statistics Module

## The constraint

Computing an average looks trivial - `sum(data) / len(data)` - and that very triviality is the trap.
The one-liner is subtly wrong in several ways.
It raises a bare `ZeroDivisionError` on empty input, giving no hint of what actually happened.
It computes the *mean*, when often what you wanted was the *median* (robust to outliers) or the *mode* (the most common value) - and confusing "average" with those is a genuine analytical error, not just a naming slip.
And when you reach for spread, standard deviation has two formulas - *sample* (divide by n-1) and *population* (divide by n) - and picking the wrong one is a classic mistake that silently biases results.

So Python programmers either re-derived these summaries each time, quietly getting the edge cases wrong, or pulled in `numpy` - a large numeric dependency - just to get a one-line statistical summary.
Neither is right for "I have a list of numbers and want their basic descriptive statistics."

The constraint Python 3.4 (2014, PEP 450) answered: **provide correct, well-defined, named descriptive statistics in the standard library - the right formulas, the sample/population distinction made explicit, exact arithmetic supported - so basic statistics need neither re-derivation nor a heavy dependency.**

This chapter owns no Deep-Volume mechanism; descriptive statistics are a domain of functions, not a language feature.
What it owns is the release: the day basic statistics became batteries-included and correct.

## What shipped

The `statistics` module provides `mean`, `median`, `mode`, and the deviation family (`stdev`/`variance` for samples, `pstdev`/`pvariance` for populations), with correct definitions, exact-arithmetic support, and a domain-specific `StatisticsError`.
Listing 254.1 shows it on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- the central-tendency trio: mean, median, mode ---
  data : [2, 4, 4, 4, 5, 5, 7, 9]
  mean   : 5   (the average, 40/8)
  median : 4.5   (middle value)
  mode   : 4   (most common value)
  three DIFFERENT notions of 'typical', each a named function. mean
  is the average, median the middle, mode the most frequent - naming
  them prevents the classic 'I said average but meant median' bug
--- median averages the middle TWO on even-length data ---
  median([1, 2, 3, 4]) : 2.5   (mean of 2 and 3)
  with an even count there is no single middle, so median returns the
  average of the two central values - the correct definition, which
  a naive data[len//2] gets wrong
--- the standard-deviation family: sample vs population ---
  stdev  (sample)     : 2.1381
  pstdev (population) : 2.0000
  variance (sample)   : 4.5714
  pvariance (pop.)    : 4.0000
  stdev/variance use the SAMPLE formula (divide by n-1), the right
  default when your data is a sample of a larger population. pstdev/
  pvariance use n for a full population. confusing the two is a
  common statistics error the separate names prevent
--- exact arithmetic: Fraction and Decimal, not just float ---
  mean of three 1/3 : 1/3   (EXACT, not 0.333...)
  statistics.mean preserves the input type: given Fractions it
  returns an exact Fraction, given Decimals an exact Decimal - so
  money and rationals stay precise instead of drifting into float
--- empty input is an explicit error, not a silent crash ---
  mean([]) -> StatisticsError: mean requires at least one data point
  a hand-rolled sum(x)/len(x) raises a bare ZeroDivisionError on
  empty data; statistics raises a clear, domain-specific
  StatisticsError that says what actually went wrong
--- the constraint answered ---
  basic statistics were re-derived (and mis-derived) everywhere or
  borrowed from numpy for a one-liner. the statistics module (3.4)
  made mean/median/mode and the sample-vs-population deviation family
  correct, named, exact-arithmetic-aware, and batteries-included -
  the right definitions, in the standard library
```

## Why each part answers the constraint

**Three named notions of "typical."**
The first block gives `mean` (5, the average), `median` (4.5, the middle), and `mode` (4, the most frequent) for the same data - three genuinely different summaries, each a distinct named function.
Naming them separately prevents the analytical error of saying "average" and computing the wrong one: if you want the outlier-robust middle, you call `median`, and the name makes the choice explicit.

**Median handles even-length data correctly.**
The second block shows the definitional care: `median([1, 2, 3, 4])` is `2.5`, the average of the two central values, because there is no single middle element in an even-length sequence.
A naive `sorted(data)[len(data)//2]` returns `3` here - wrong.
The module implements the correct definition, which is exactly the kind of edge case hand-rolled code gets wrong.

**Sample versus population, made explicit.**
The third block separates the deviation family by name.
`stdev`/`variance` use the sample formula (divide by n-1), the right default when your data is a sample drawn from a larger population; `pstdev`/`pvariance` use n, for a complete population.
The distinction is a well-known source of error, and the module surfaces it as two clearly-named function pairs rather than a formula you have to remember to adjust - choosing the right one becomes choosing the right name.

**Exact arithmetic, not just float.**
The fourth block shows `mean` of three `Fraction(1, 3)` values returning an exact `Fraction(1, 3)`, not the float `0.333...`.
The module preserves the input's numeric type, so `Fraction` and `Decimal` data stay exact - important for money and rationals, where drifting into binary float would introduce rounding error.

**Empty input is a clear error.**
The fifth block shows `mean([])` raising `StatisticsError: mean requires at least one data point` - a domain-specific message that says what went wrong, rather than the bare `ZeroDivisionError` a hand-rolled `sum/len` produces.
The error is part of getting the edge cases right.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; `statistics` is a domain library built on Python's numeric tower.
It has a deliberate scope: descriptive statistics for modest data sets, prioritizing correctness and exactness over raw speed.
For large numeric arrays and heavy computation, `numpy` remains the right tool - but for "summarize this list of numbers correctly," the standard library now suffices, with no dependency and the right definitions.
What the timeline records is the release act: in 3.4, PEP 450 made basic descriptive statistics batteries-included, and later releases extended the module (`fmean`, `quantiles`, `correlation`, and more).

## Where this lands

The `statistics` module is a small, correctness-focused addition that removed a whole category of quiet bugs - the mis-derived average, the wrong standard-deviation formula, the empty-list crash.
Reach for it whenever you need mean, median, mode, or spread on a manageable data set and do not want a numeric dependency: use `median` when outliers matter, choose `stdev`/`variance` for sample data and `pstdev`/`pvariance` for full populations, and pass `Fraction` or `Decimal` when exactness matters.
Reach for `numpy` when the data is large or the computation heavy.
No Deep Volume owns a statistics mechanism; this chapter is the record of the release that put the right definitions in the standard library.
