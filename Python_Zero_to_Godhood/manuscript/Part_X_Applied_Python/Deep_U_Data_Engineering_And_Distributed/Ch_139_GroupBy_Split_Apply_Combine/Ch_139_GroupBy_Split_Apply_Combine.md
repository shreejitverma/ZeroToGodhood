# Chapter 58: GroupBy: Split-Apply-Combine

Chapter 57 established the first pillar of pandas: operate on whole columns.
This chapter is the second: **`groupby`**, the split-apply-combine pattern that turns "per-group summary" into a single expression.
Almost every data question of the form "X *per* Y", total sales per region, average latency per endpoint, count per category, error rate per day, is a `groupby`, and expressing it as one is both dramatically clearer and faster than the manual alternative.

The pattern has three steps, and the name says all three.
**Split** the rows into groups by a key (or keys).
**Apply** an aggregation to each group's values (sum, mean, count, or several at once).
**Combine** the per-group results into a new frame, indexed by the group key.
Pandas does all three in C over the columnar data, so `df.groupby("region")["sales"].sum()` is a single vectorized operation, measured **5-6x** faster than even a *well-written* Python accumulation loop (and far faster than the row loops of Chapter 57).

**This is Deep U's aggregation chapter.**
It is the second core pandas skill after Chapter 57's column operations, builds on the columnar/vectorized model (Deep T, Chapter 96), and is the workhorse of the data pipelines in **Book III**.

## Section index

- **58.1** Split, apply, combine
- **58.2** The pattern and its vocabulary
- **58.3** Measurement: `groupby` versus a manual loop
- **58.4** Edges and failure modes
- **58.5** Connections
- **58.6** Exercises
- **58.7** Summary and cross-references

Listings live under `code/ch139/` and are re-executed by `make verify` on both verification interpreters.

---

## 58.1 Split, apply, combine

```python
# code/ch139/l01_groupby.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- split-apply-combine: one aggregate per group ---
  sum per region  : {'east': 60, 'west': 90}
  mean per region : {'east': 20.0, 'west': 45.0}
  count per region: {'east': 3, 'west': 2}
  max per region  : {'east': 30, 'west': 50}
--- multiple aggregations at once with .agg([...]) ---
  agg sum column   : {'east': 60, 'west': 90}
  agg mean column  : {'east': 20.0, 'west': 45.0}
--- group by MULTIPLE keys ---
  (region, product) -> sum : {('east', 'a'): 10, ('east', 'b'): 20, ('west', 'a'): 70}
--- the result is indexed by the group key (a new frame/series) ---
  result index (the keys)  : ['east', 'west']
  look up one group        : east -> 60
--- the rule ---
  groupby(key).agg splits rows by key, aggregates each group in C, and
  combines into a keyed result; use it instead of a per-group Python loop
```

`df.groupby("region")["sales"].sum()` performs all three steps at once.
**Split:** the rows are partitioned by `region` into `east` (three rows) and `west` (two rows).
**Apply:** `sum` is applied to each group's `sales`, `east` sums to 60, `west` to 90.
**Combine:** the results are assembled into a Series indexed by the group key (`{'east': 60, 'west': 90}`).
Swap `sum` for `mean`, `count`, `max`, or any aggregation, and you get that summary per group.

**Multiple aggregations at once** come from `.agg([...])`: `df.groupby("region")["sales"].agg(["sum", "mean", "count"])` computes all three per group in one pass, returning a frame with a column per aggregation. This is how you build a summary table (sum, mean, and count per group together) without three separate groupbys.

**Multiple keys** partition by a *combination*: `df.groupby(["region", "product"])["sales"].sum()` groups by each `(region, product)` pair, giving a result indexed by the tuple. This is the drill-down, "sales per region *and* product", the hierarchical grouping behind pivot tables.

**The result is keyed.** The output is a Series (or frame) indexed by the group key, so you can look up a group directly (`result["east"]` is 60) or use the whole thing in further operations. The group key *becomes the index*, which is why groupby composes cleanly with the rest of pandas.

So `groupby` is the split-apply-combine engine: name the grouping key(s), name the aggregation(s), and pandas produces the per-group summary in C.

---

## 58.2 The pattern and its vocabulary

Split-apply-combine is a *pattern*, not just a function, and recognizing when a problem fits it is the skill.

**When it fits:** any "per-group" question.
"Total per category", "average per user", "max per day", "count of errors per endpoint", "first and last per session", if you can phrase the question with the word *per*, it is a groupby. The grouping key is what comes after "per"; the aggregation is what comes before.

**The apply step's vocabulary:**

- **Reductions:** `sum`, `mean`, `count`, `min`, `max`, `std`, `median`, `nunique`, one value per group.
- **Multiple at once:** `.agg(["sum", "mean"])` or `.agg({"col1": "sum", "col2": "mean"})` for different aggregations per column.
- **Custom aggregations:** `.agg(lambda g: ...)` for a group-level function (slower, per-group Python, use only when no built-in fits).
- **Transform** (`.transform`): return a result the *same shape* as the input (e.g. group-normalized values, "each value minus its group mean"), for adding group-derived columns back to the original rows.
- **Filter** (`.filter`): keep only groups satisfying a condition (e.g. groups with more than N rows).

**The design payoff:** groupby *composes* with the rest of pandas.
The result is a frame, so you can filter it, sort it, merge it, or feed it into another operation, all vectorized.
A pipeline like "sales per region, keep regions above a threshold, sort descending" is three chained operations, each in C, no loop anywhere.
This composability is why data engineering expresses transformations as chains of vectorized operations (filter, groupby, merge, sort) rather than procedural loops: each operation is a C pass, and they compose into a pipeline that stays in C end to end.

The rule: **express every "per-group summary" as a `groupby(...).agg(...)`**, and reach for `transform` (add a group-derived column) or `filter` (keep qualifying groups) for the variants. A manual per-group loop (build a dict of lists, iterate, aggregate) is slower, longer, and error-prone, groupby is the tool.

---

## 58.3 Measurement: `groupby` versus a manual loop

**Methodology.** `code/ch139/bench_groupby.py`.
A per-key sum over 500,000 rows (100 keys), computed with `groupby("key")["v"].sum()` versus a Python `dict`-accumulation loop over the column values.
Wall-clock, `perf_counter`.
CPython 3.13.5, pandas 2.2.3, Apple M3 Pro, macOS 27.0, arm64.

| per-key sum over 500,000 rows | time | vs groupby |
|---|---|---|
| `groupby("key")["v"].sum()` | ~5 ms | 1x |
| Python `dict` accumulation loop | ~24 ms | **~5x slower** |

`groupby` is **~5x** faster than the manual loop (6x on 3.14.6).
Note that the comparison is *fair to the loop*: the Python version is a tight `dict.get` accumulation over `tolist()`ed columns, the *fast* pure-Python way (not the 1,000x-slower `iterrows` of Chapter 57).
Even so, groupby wins by 5x, because it groups and sums in C over contiguous typed arrays, while the loop runs the interpreter per row and boxes each value.

The 5x is smaller than Chapter 57's 1,000x for a reason worth understanding: a simple `dict.get` loop is already reasonably efficient (it is *not* building a Series per row), so groupby's advantage over it is "merely" several-fold rather than thousands-fold.
But the point stands and the gap *widens* with complexity: more groups, multiple aggregations, multiple keys, or further operations on the result, each of which groupby does in C while the loop would need more and more Python code.
And the *clarity* difference is large regardless of the speed: `df.groupby("key")["v"].sum()` is one self-documenting expression; the loop is several lines of accumulation logic that must be re-written for every new aggregation.

So the guidance combines speed and clarity: **express per-group aggregation as `groupby`**, always.
It is faster (5x here, more as complexity grows), clearer (one expression), and composable (the result feeds the next vectorized operation).
This is Deep U's second pillar after Chapter 57's "columns not rows": *aggregation is split-apply-combine, done in C by groupby*, not a hand-written loop.
Together, vectorized column operations and groupby cover the large majority of data transformations, and both keep the computation in C over the columnar data, which is the entire performance premise of data engineering, and of **Book III**'s pipelines.

---

## 58.4 Edges and failure modes

**Custom Python aggregations are slow.** §58.2.
`.agg(lambda g: ...)` and `.apply(python_func)` run Python per group, losing the C speed. Use built-in aggregations (`sum`, `mean`, named strings) whenever possible; reserve custom functions for what has no built-in.

**`groupby` sorts by key by default.**
The result is sorted by the group key, which costs time on many groups. `groupby(key, sort=False)` skips the sort when you do not need ordered output, a real speedup for high-cardinality keys.

**Missing keys (`NaN`) are dropped by default.**
Rows whose group key is `NaN` are excluded from the result by default. Pass `dropna=False` to include a `NaN` group if missing keys are meaningful.

**`agg` versus `transform` versus `apply`.**
`agg` returns one row per group (a summary); `transform` returns the same shape as the input (a per-row group-derived value); `apply` is the general, slower fallback. Using the wrong one gives the wrong shape or slow code, choose by whether you want a summary (`agg`) or a broadcast-back column (`transform`).

**Grouping on a computed key.**
To group by something not already a column (a bucket, a derived category), compute it first (`df["bucket"] = ...`) or pass a Series/function to `groupby`. Grouping by a derived key per row via `apply` is slow; vectorize the key computation.

**Large numbers of groups cost memory.**
Grouping by a high-cardinality key (millions of distinct values) creates many groups and can be memory-heavy. Consider whether the grouping is what you want, or a coarser bucketing.

**The result's index is the key.**
groupby returns a result *indexed by the group key*; `reset_index()` turns it back into columns if you need a flat frame. Forgetting this leads to confusion when merging or exporting the result.

**Observed categories in categorical groupby.**
Grouping a `category`-dtype column includes *all* categories by default (even empty ones), which can surprise. Use `observed=True` to include only categories present in the data.

---

## 58.5 Connections

**Backward.**
groupby is vectorized aggregation (Chapter 96) with a grouping key, over the DataFrame's columns (Chapter 57). The C-speed grouping is the columnar/typed advantage of Deep T and Chapter 104. Reductions per group are Chapter 101's array reductions, grouped.

**Forward.**
`merge`/`join` (combining frames), pivot tables (groupby reshaped), window functions (`rolling`, `expanding`), and time-series resampling (`resample`, a time-based groupby) are the rest of **Deep U**. SQL's `GROUP BY` is the same pattern (Deep U / databases). Distributed groupby (Dask, Spark) scales it beyond one machine.

**Across books.**
Split-apply-combine is everywhere in **Book III**'s pipelines: features per entity, metrics per time bucket, aggregates per category, are all groupbys, expressed as one C-speed operation rather than a loop. The order-book system computes per-symbol, per-interval, and per-venue aggregates (volume, VWAP, counts) with groupby, chains them (filter groups, sort, merge with reference data) as vectorized pipelines, and never hand-writes an accumulation loop, so a summary over millions of records is a handful of C passes, the §58.3 pattern as the shape of every analytics query. Deep U's two pillars, columns (Chapter 57) and groupby (this chapter), are the grammar of that data path.

---

## 58.6 Exercises

**1. The three steps.** Reproduce §58.1: group by one key and compute sum, mean, count, max; use `.agg([...])` for several at once; group by two keys. Explain split, apply, and combine for each, and why the result is keyed.

**2. Recognize the pattern.** Take three "X per Y" questions in plain English and write each as a groupby. Identify the grouping key and the aggregation in each. Then write one as a manual loop and compare the clarity.

**3. Measure it.** Reproduce §58.3. Confirm groupby beats the dict loop. Then add a second aggregation and a second key and show the gap widening. Explain why complexity favours groupby.

**4. transform versus agg.** Add a column that is "each value minus its group mean" using `transform`, and compare to what `agg` returns. Explain the shape difference and when to use each.

**5. The design question.** groupby expresses aggregation as split-apply-combine in C, composing with the rest of pandas. Argue why this declarative, vectorized style beats procedural loops for data work, using §58.3 (speed) and §58.2 (composability). Connect it to SQL `GROUP BY` and to why data pipelines are chains of vectorized operations.

---

## 58.7 Summary and cross-references

- **`groupby`** implements **split-apply-combine**: **split** rows by a key, **apply** an aggregation to each group, **combine** into a result indexed by the key. `df.groupby("region")["sales"].sum()` is "sum per region" in one C-speed expression.
- **Vocabulary:** reductions (`sum`/`mean`/`count`/...), `.agg([...])` for several at once, multiple keys for drill-down, `transform` (same-shape group-derived values), `filter` (keep qualifying groups). The result is keyed and **composes** with the rest of pandas.
- **Measured:** a per-key sum over 500,000 rows is **~5x** faster with `groupby` than a (fast) Python `dict`-accumulation loop, and the gap widens with more groups, keys, and aggregations, plus groupby is one clear expression versus a hand-written loop.
- **Any "X per Y" question is a groupby.** Express per-group summaries as `groupby(...).agg(...)`, never a manual accumulation loop.
- **Edges:** custom Python aggregations are slow (prefer built-ins); `sort=False` speeds high-cardinality grouping; `NaN` keys drop by default (`dropna=False`); choose `agg`/`transform`/`apply` by output shape; the result is indexed by the key (`reset_index` to flatten).

**Cross-references.** Column operations (the first pillar) → Chapter 57. Vectorization / array reductions → Chapters 96, 101. Structured/columnar storage → Chapter 104. `merge`/pivot/`rolling`/`resample`, SQL `GROUP BY`, distributed groupby → the rest of Deep U. Book III data pipelines → Deep U / Book III.
