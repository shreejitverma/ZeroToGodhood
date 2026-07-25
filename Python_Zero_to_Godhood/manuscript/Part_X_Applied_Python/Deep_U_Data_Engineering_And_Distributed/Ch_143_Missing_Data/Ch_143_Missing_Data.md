# Chapter 62: Missing Data

Real data has holes.
A sensor drops a reading, a form field is left blank, a join finds no match (Chapter 59), a record predates a column's existence.
Handling **missing data** correctly is one of the defining skills of data engineering, and pandas represents a missing value as **`NaN`** (Not a Number), an IEEE-754 float value with behaviour that surprises everyone at least once.
This chapter covers how to detect, remove, and fill missing data, the two ways `NaN` changes computations (aggregations *skip* it, arithmetic *propagates* it), and the trap that gives this chapter its measurement: a `NaN` in an integer column silently promotes it to `float64`, which can *corrupt large integer IDs*.

That trap is not academic.
`float64` represents integers exactly only up to `2^53`; above that, distinct integers round to the same float.
So a single missing value in a column of large integer IDs promotes the whole column to `float64` and makes distinct IDs **collide**, measured here at **499 collisions** among 1000 IDs, silently merging half the records.
No error, just wrong data.
The fix is pandas' **nullable dtypes** (`Int64`, capital I), integers that allow missing values without promotion, and the chapter's core lesson is that missing data is a *correctness* problem where the failures are silent, so the discipline is to handle `NaN` explicitly and preserve types.

**This is Deep U's missing-data chapter.**
It builds on Chapter 98 (float precision, the `2^53` wall), Chapter 59 (joins produce missing values), and the DataFrame (Chapter 57). Missing data is pervasive in **Book III**'s real-world datasets.

## Section index

- **62.1** Detecting, removing, filling, and how `NaN` behaves
- **62.2** The correctness discipline, and nullable dtypes
- **62.3** Measurement: the int-to-float ID collision
- **62.4** Edges and failure modes
- **62.5** Connections
- **62.6** Exercises
- **62.7** Summary and cross-references

Listings live under `code/ch143/` and are re-executed by `make verify` on both verification interpreters.

---

## 62.1 Detecting, removing, filling, and how `NaN` behaves

```python
# code/ch143/l01_missing.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- detect, drop, fill ---
  isna().sum() (count missing) : 2
  dropna()                     : [1.0, 3.0, 5.0]
  fillna(0)                    : [1.0, 0.0, 3.0, 0.0, 5.0]
  ffill() (carry last forward) : [1.0, 1.0, 3.0, 3.0, 5.0]
--- aggregations SKIP NaN; arithmetic PROPAGATES it ---
  mean() skips NaN : 3.0   (mean of 1,3,5)
  sum() skips NaN  : 9.0
  (s + 1) is NaN where s was NaN : [False, True, False, True, False]
--- NaN != NaN: detect with isna(), never == ---
  np.nan == np.nan : False   (False! use isna)
--- a NaN in an INT column promotes it to float64 ---
  original dtype : int64
  after a NaN    : float64   (int64 -> float64)
--- the fix: nullable Int64 allows missing WITHOUT float promotion ---
  nullable Int64 values : [1, 2, None, 4]
  still an integer type : True
  and tracks missing    : [False, False, True, False]
--- the rule ---
  detect NaN with isna (never ==); dropna/fillna/ffill to handle it;
  aggregations skip it, arithmetic propagates it; use Int64 for nullable ints
```

**Detect, remove, fill.**
`isna()` returns a boolean mask of where values are missing (`sum()` counts them). `dropna()` removes rows with missing values. `fillna(value)` replaces missing with a constant; `ffill()` (forward-fill) carries the last valid value forward (and `bfill()` backward), common for time series. These are the vectorized tools for handling missingness.

**`NaN` behaves two ways, and both must be known.**
*Aggregations skip it:* `mean()` of `[1, NaN, 3, NaN, 5]` is `3.0`, the average of the *three* present values, not five. `sum()` is `9.0`. So by default, reductions ignore missing data, which is often what you want, but note the *denominator*: `mean` divides by the count of *present* values, not the total.
*Arithmetic propagates it:* `s + 1` is `NaN` wherever `s` was `NaN`, missingness spreads through element-wise operations. So a computed column derived from a column with holes has holes in the same places.

**`NaN != NaN`.**
The most counterintuitive fact: `np.nan == np.nan` is `False`. `NaN` is not equal to *itself* (IEEE-754 semantics, Chapter 98). So you **cannot** detect missing with `== NaN` (it is always `False`); you *must* use `isna()`/`notna()`. This trips up everyone who tries `df[df["x"] == np.nan]` (which matches nothing) instead of `df[df["x"].isna()]`.

**The int-to-float promotion trap.**
`NaN` is a *float*, so a `NaN` in an *integer* column forces the whole column to `float64` (an int64 column becomes float64 the moment a missing value appears). This is the trap §62.3 measures: for large integer IDs, that promotion loses precision.

**The fix: nullable dtypes.**
Pandas' `Int64` (capital I) is a *nullable integer* dtype: it stores integers *and* allows a missing marker (`pd.NA`) *without* promoting to float. The `[1, 2, None, 4]` array stays an integer type and tracks the missing value. Nullable dtypes (`Int64`, `Float64`, `boolean`, the new `string`) are the modern, type-safe way to have missing values without the promotion trap.

---

## 62.2 The correctness discipline, and nullable dtypes

Missing data is a *correctness* problem, and its failures are *silent*, so the discipline is about making handling explicit.

**Decide, per column, what missing means and handle it deliberately.**
Missing is not one thing: "not measured", "not applicable", "zero", "unknown". The handling differs:

- **Drop** (`dropna`) when a row without the value is useless (but beware dropping too much, and know *which* rows you lost).
- **Fill** (`fillna`) with a meaningful default, `0` for a count, the mean/median for a measurement, a sentinel category, or forward-fill for time series, but never fill *blindly* (filling a missing price with 0 corrupts an average).
- **Keep** (as `NaN`/`NA`) when downstream operations handle it correctly (aggregations skip it), and propagate it honestly.

The point: **choose the handling to match the meaning**, and do it explicitly, rather than letting `NaN` silently flow through and skew results.

**Detect with `isna`, never `==`.** §62.1.
`df[df["x"].isna()]`, `df["x"].notna()`, `df.dropna(subset=["x"])`. The `== NaN` bug matches nothing and silently hides the missing rows.

**Watch the aggregation denominators.**
`mean` skips `NaN`, so it averages over present values, usually right, but if you need "average over *all* rows treating missing as zero", `fillna(0).mean()` gives a different (smaller) answer. Know which you want. `count()` counts non-missing; `len()` counts all. The gap between them is the missing count.

**Use nullable dtypes for type safety.** §62.1, §62.3.
For integer columns that may have missing values, especially IDs and keys, use `Int64` (nullable) to avoid the float promotion that corrupts large integers. Nullable dtypes also make missingness explicit in the type system (`pd.NA` is distinct from `NaN`) and are increasingly the pandas default (pandas 3.0's string dtype). The old `object`/`NaN` approach is a source of both slowness and the promotion bug.

**Missing data compounds through pipelines.**
A `NaN` from a failed join (Chapter 59) propagates through arithmetic, skews an aggregation, and, if it hits an integer column, corrupts IDs, so a single missing value early can silently distort a final result. The defense is to handle missingness at each stage deliberately, and to validate (assert no unexpected `NaN`s where there should be none) rather than let it flow.

The rule: **treat missing data as a first-class correctness concern, detect it with `isna`, handle it deliberately per its meaning, use nullable dtypes to preserve types, and validate that missingness is where you expect.**

---

## 62.3 Measurement: the int-to-float ID collision

**Methodology.** `code/ch143/bench_promotion.py`.
A *correctness* measurement, not a timing one: 1000 consecutive integer IDs starting at `2^53`, counting distinct values as `int64`, after promotion to `float64` (what a single `NaN` forces), and as nullable `Int64`.
CPython 3.13.5, pandas 2.2.3.

| 1000 IDs starting at 2^53 | distinct values |
|---|---|
| `int64` (exact) | 1,000 |
| after `float64` promotion | **501** |
| IDs silently merged (collisions) | **499** |
| nullable `Int64` | 1,000 |

Promoting the IDs to `float64` collapses 1000 distinct integers to **501**, silently merging **499** of them.
The cause is Chapter 98's `2^53` wall: `float64` has 52 bits of mantissa, so it represents integers exactly only up to `2^53`; above that, consecutive integers round to the *same* float (only every second, then every fourth, integer is representable).
So distinct IDs above `2^53` become equal after promotion, and a single `NaN` in an integer ID column, which forces exactly this promotion (§62.1), triggers it.

This is a genuinely dangerous, silent data-corruption bug, and it is worth dwelling on because it hides so well.
There is **no error**: the promotion is legal, the collisions are silent, and the data *looks* fine, just with fewer distinct IDs than it should have.
The consequences are severe: duplicate-looking rows (distinct records now share an ID), wrong join results (Chapter 59, IDs that should not match now do), lost records (deduplication on the corrupted ID drops real data), and inflated or deflated aggregates.
And it surfaces far from the cause, a `NaN` introduced by a join in stage 1 corrupts the IDs, and the wrong counts appear in stage 5.

The fix is precise and the lesson general.
**Use nullable `Int64` for integer IDs and keys that may have missing values**, which keeps them exact (1000 distinct) while allowing `pd.NA`, so the promotion never happens.
More broadly, this is the missing-data theme in its sharpest form: missing values do not just leave holes, they can *silently change your types and corrupt your data*, and the failures are invisible until the numbers are questioned.
So the discipline of §62.2, handle missingness explicitly, preserve types with nullable dtypes, validate that missing is where you expect, is not fussiness; it is the defense against exactly this class of silent corruption.
This is the same principle as Chapter 59's `validate=` (assert your assumptions) and the whole book's correctness stance: where a failure is silent, make the assumption explicit and machine-checked, and missing data is where that matters most.

---

## 62.4 Edges and failure modes

**`NaN != NaN`; detect with `isna`.** §62.1.
`== np.nan` matches nothing (a silent no-op that hides missing rows). Always use `isna()`/`notna()`.

**A `NaN` promotes an integer column to `float64`, corrupting large IDs.** §62.3.
The `2^53` wall. Use nullable `Int64` for integer IDs/keys that may be missing.

**Blind `fillna` corrupts aggregates.** §62.2.
Filling a missing *price* with `0` skews the mean; filling a missing *count* with `0` may be right. Fill with a meaning-appropriate value, or keep `NaN`.

**`mean`/`sum` skip `NaN`; know the denominator.** §62.1.
`mean` averages over present values. If you need "treat missing as 0", `fillna(0)` first. `count` (non-missing) differs from `len` (all).

**`dropna` can drop too much.**
`dropna()` (any missing in the row) can remove far more than intended. Use `subset=` to drop only on specific columns, and check how many rows you lost.

**`NaN` versus `None` versus `pd.NA`.**
`NaN` is the float missing marker; `None` is Python's null (becomes `NaN` in float columns, stays `None`/`NA` in object/nullable columns); `pd.NA` is the nullable-dtype missing marker (with more consistent propagation). Mixing them, and their subtly different behaviours, is a source of confusion; prefer nullable dtypes with `pd.NA` for consistency.

**Missing data from joins.** §62.5.
`left`/`outer` joins (Chapter 59) *introduce* `NaN` for non-matches. A join is a common source of missingness; handle the resulting `NaN`s deliberately.

**Interpolation assumes structure.**
`interpolate()` (fill by linear/time interpolation) is powerful for time series but assumes the data is smoothly varying; using it on categorical or non-continuous data produces nonsense.

**Silent propagation through pipelines.** §62.2, §62.3.
One early `NaN` can distort a far-downstream result. Validate for unexpected `NaN`s at stage boundaries.

---

## 62.5 Connections

**Backward.**
The `float64` `2^53` wall is Chapter 98 (dtypes/precision); `NaN != NaN` is IEEE-754 (Chapter 98) and reflexivity failure (Chapter 23). Joins introducing `NaN` is Chapter 59. Missing data lives in the DataFrame's columns (Chapter 57). The silent-corruption theme is the book's correctness stance (assert assumptions).

**Forward.**
Nullable dtypes (`Int64`, `Float64`, `boolean`, `string`) and the pandas 3.0 / Arrow-backed types (more consistent `pd.NA`) are the modern direction. Missing-data-aware ML preprocessing (imputation strategies) is **Deep W**. `merge_asof` and time-series interpolation are Deep U. Data validation frameworks (Great Expectations, pandera) formalize the "validate missingness" discipline.

**Across books.**
Missing data is pervasive in **Book III**'s real datasets, and handling it correctly is a data-quality requirement: a missing price must not become zero (corrupting a VWAP), a missing ID must not collide (corrupting a join), a missing feature must be imputed deliberately (not silently propagated into a model). The order-book system uses nullable `Int64` for its integer IDs and keys (so a missing key never corrupts them via float promotion), fills missing prices/quantities with meaning-appropriate values or keeps them as `NA`, and validates for unexpected missingness at each pipeline stage, the §62.2 discipline as a data-quality gate, so the §62.3 silent corruption never reaches a P&L number. In a domain where a wrong number is a real loss, missing-data correctness is not optional.

---

## 62.6 Exercises

**1. Detect and handle.** Reproduce §62.1: count missing with `isna`, then `dropna`, `fillna`, and `ffill`. Confirm `mean` skips `NaN` and arithmetic propagates it. Show `== np.nan` matches nothing and `isna` works. Explain each.

**2. The promotion trap.** Reproduce §62.3: create large integer IDs, promote to `float64` (via a `NaN` or `astype`), and count the collisions. Then use nullable `Int64` and show no collisions. Explain the `2^53` wall and why a `NaN` triggers it.

**3. Denominator matters.** Compute `mean` of a column with missing values two ways: skipping `NaN` (default) and treating missing as `0` (`fillna(0)`). Show they differ. Explain which is right for which meaning.

**4. Missing from a join.** Perform a `left` join (Chapter 59) that produces `NaN`s, then handle them appropriately. Show how a blind `fillna(0)` would corrupt a downstream aggregate. Explain the cross-stage propagation.

**5. The design question.** Missing data's failures are silent (`== NaN` no-op, int-to-float ID collision, skewed aggregates). Argue why the discipline, `isna` detection, deliberate per-meaning handling, nullable dtypes, validation, is essential, using §62.3. Connect it to Chapter 59's `validate=` and the book's "assert your assumptions" stance.

---

## 62.7 Summary and cross-references

- Pandas represents missing as **`NaN`**. **Detect** with `isna()`/`notna()` (never `== NaN`, which matches nothing); **handle** with `dropna`, `fillna(value)`, `ffill`/`bfill`, `interpolate`.
- **`NaN` behaves two ways:** aggregations **skip** it (`mean` averages present values, watch the denominator), arithmetic **propagates** it (`NaN + 1` is `NaN`). And **`NaN != NaN`** (not equal to itself).
- **The trap:** a `NaN` in an integer column **promotes it to `float64`**, and above `2^53` (Chapter 98) distinct large integers collide. **Measured:** 1000 IDs at `2^53` collapse to **501** after promotion (**499 silent collisions**). **Fix:** nullable **`Int64`** keeps integers exact while allowing missing (`pd.NA`).
- **Missing data is a silent correctness problem:** handle it deliberately per its meaning, preserve types with nullable dtypes, and **validate** that missingness is where you expect (as Chapter 59 validates joins).
- **Edges:** blind `fillna` corrupts aggregates; `dropna` can drop too much (use `subset=`); `NaN`/`None`/`pd.NA` differ (prefer nullable + `pd.NA`); joins introduce `NaN`; one early `NaN` distorts far-downstream results.

**Cross-references.** Float precision / `2^53` wall / `NaN` semantics → Chapter 98. Joins produce missing values / `validate=` → Chapter 59. Reflexivity failure (`NaN != NaN`) → Chapter 23. Columnar DataFrame → Chapter 57. Nullable/Arrow dtypes, imputation, validation frameworks → the rest of Deep U / Deep W. Book III data quality → Deep U / Book III.
