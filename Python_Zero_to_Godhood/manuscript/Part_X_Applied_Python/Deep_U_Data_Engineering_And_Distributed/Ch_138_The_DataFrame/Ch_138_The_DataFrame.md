# Chapter 57: The DataFrame

Deep T ended with the structured array (Chapter 104): typed columns in one contiguous block, the memory and speed of NumPy with the shape of records.
The **pandas DataFrame** is that idea grown into the central tool of data engineering, and this chapter opens **Deep U**, the data-engineering volume that is the seam to **Book III**.
A DataFrame is a set of **named, typed columns** (each a `Series`, backed by a NumPy array) sharing a row **index**, plus a large vocabulary of operations: alignment, missing-data handling, grouping, joining, reshaping, and IO for every format data arrives in.
It is where the numeric machinery of Deep T meets the messy, labeled, heterogeneous data of the real world.

The chapter's one non-negotiable rule is inherited directly from NumPy (Chapter 96) and confirmed by the measurement: **operate on whole columns, never loop over rows.**
A vectorized column expression runs a single C pass over contiguous typed arrays; the `iterrows()` row loop builds a Python object per row and computes in the interpreter, and it is measured here at over **1,000x** slower.
"Never use `iterrows`" is the first and most important thing a pandas user learns, and it is Chapter 96's vectorization rule at the table level.

**This opens Deep U, the data-engineering volume.**
The DataFrame builds on Chapter 104 (structured arrays, its conceptual ancestor), Deep T's NumPy (its engine), and Chapter 102 (boolean masks, its filtering). It is the tool **Book III**'s data pipelines are written in.
(Verified against pandas 2.2.3 on 3.13 and pandas 3.0.5 on 3.14; the listing uses version-stable accessors, since reprs and some dtype names differ across those major versions.)

## Section index

- **57.1** Columns, types, and vectorized operations
- **57.2** The cardinal rule: columns, not rows
- **57.3** Measurement: vectorized versus `iterrows`
- **57.4** Edges and failure modes
- **57.5** Connections
- **57.6** Exercises
- **57.7** Summary and cross-references

Listings live under `code/ch138/` and are re-executed by `make verify` on both verification interpreters.

---

## 57.1 Columns, types, and vectorized operations

```python
# code/ch138/l01_dataframe.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a DataFrame is named, typed columns sharing a row index ---
  shape (rows, cols) : (4, 3)
  column names       : ['symbol', 'price', 'qty']
  price dtype        : float64
  qty dtype          : int64
  symbol is text     : True
--- a column is a Series (a typed vector, backed by NumPy) ---
  df['qty'] as a list : [5, 3, 8, 2]
  df['qty'].sum()     : 18
  df['price'].mean()  : 25.0
--- vectorized column arithmetic: a whole new column in one C pass ---
  (price * qty).tolist()    : [50.0, 60.0, 240.0, 80.0]
  total notional            : 430.0
--- boolean filtering: a mask over rows (Chapter 102, at table level) ---
  rows with qty > 3 (symbols) : ['AAA', 'CCC']
  how many                    : 2
--- add a computed column (assign back) ---
  columns after adding 'notional' : ['symbol', 'price', 'qty', 'notional']
--- the rule ---
  a DataFrame is typed columns + an index; operate on whole columns
  (vectorized, in C), filter with masks, never loop over rows
```

A **DataFrame** is columnar and typed, exactly like Chapter 104's structured array, with labels added.
It has a `shape` (rows, columns), named `columns`, and each column has its own **dtype** (`price` is `float64`, `qty` is `int64`, `symbol` is text).
The columnar, typed layout is the source of both its memory efficiency and its speed: each column is a contiguous typed array, so operations run in C (Deep T), not per-element Python.

A **column is a `Series`**, a typed vector backed by a NumPy array, with the full reduction vocabulary: `df["qty"].sum()`, `df["price"].mean()`.
This is the key to how you *think* in pandas: you manipulate whole columns, not individual cells.

**Vectorized column arithmetic** produces a whole new column in one pass: `df["price"] * df["qty"]` computes the elementwise product across all rows, in C, with no loop, exactly Chapter 96's vectorization, applied to labeled columns. Assigning it back (`df["notional"] = ...`) adds a computed column.

**Boolean filtering** is Chapter 102's masks at the table level: `df[df["qty"] > 3]` selects the rows where the mask is true, returning a sub-DataFrame. The mask (`df["qty"] > 3`) is a boolean Series; indexing the frame with it filters rows. This is how you express "the rows where X" without a loop.

So the DataFrame model is: **typed columns you operate on whole**, an index that labels and aligns rows, and masks that filter, the structured array of Chapter 104 with labels, alignment, and a rich API layered on NumPy.

---

## 57.2 The cardinal rule: columns, not rows

Everything about using pandas well flows from one rule, and it is worth stating starkly because violating it is the single most common pandas mistake.

**Operate on whole columns; never loop over rows.**

Pandas gives you several ways to iterate rows, `iterrows()`, `itertuples()`, `for` over the frame, `apply(axis=1)`, and they are almost always the wrong tool for anything but tiny data.
The reason is the same as Chapter 96's: a DataFrame stores each column as a contiguous typed NumPy array, so a *column* operation runs in C over that array, while a *row* operation crosses back into Python for every row, boxing values into Python objects and running the interpreter per row.
`iterrows()` is the worst offender: it constructs a *new pandas Series object for every row*, an expensive operation repeated per row, which is why it is measured at over 1,000x slower than the vectorized equivalent (§57.3).

The vocabulary that keeps you in C:

- **Column arithmetic:** `df["a"] * df["b"]`, `df["a"] + 1`, `np.log(df["a"])`, elementwise over whole columns.
- **Boolean masks:** `df[df["a"] > 0]`, `df["a"].where(cond)`, filtering and conditional logic (Chapter 102).
- **Reductions:** `df["a"].sum()`, `.mean()`, `.max()`, over columns.
- **`groupby`:** `df.groupby("key")["value"].sum()`, split-apply-combine in C (the next chapters).
- **Vectorized string/date methods:** `df["s"].str.upper()`, `df["d"].dt.year`, applied to whole columns.
- **`merge`/`join`:** combining frames on keys, in C.

If you find yourself writing `for _, row in df.iterrows():`, stop, there is almost always a vectorized expression that does the same thing in one C pass.
The rare legitimate row loop is for genuinely sequential, non-vectorizable logic on *small* data (a few hundred rows), and even then `itertuples()` (which yields lightweight named tuples, not Series) is far faster than `iterrows()`.

The rule: **express computations as whole-column operations, masks, groupbys, and merges; treat a row loop over a large DataFrame as a bug.**
This is Deep U's foundational discipline, and it is Deep T's vectorization (Chapter 96) carried into labeled, heterogeneous data.

---

## 57.3 Measurement: vectorized versus `iterrows`

**Methodology.** `code/ch138/bench_iterrows.py`.
Sum of `price * qty` over 200,000 rows, computed as a vectorized column expression versus an `iterrows()` row loop.
Wall-clock, `perf_counter`.
CPython 3.13.5, pandas 2.2.3, Apple M3 Pro, macOS 27.0, arm64.

| sum `price*qty` over 200,000 rows | time | vs vectorized |
|---|---|---|
| vectorized columns `(df["price"] * df["qty"]).sum()` | ~1 ms | 1x |
| `iterrows()` loop | ~1,500 ms | **~1,478x slower** |

The vectorized column expression is over **1,000x** faster (1,478x here; 1,799x on 3.14.6 with pandas 3.0.5, the direction is identical, the exact multiple varies with versions).
The vectorized version multiplies two contiguous `float64`/`int64` arrays and sums, in C, in about a millisecond.
`iterrows()` constructs a **pandas Series object for each of the 200,000 rows**, indexes into it by column name twice, and does the arithmetic on boxed Python scalars in the interpreter, three orders of magnitude of overhead.

This is the measurement that defines pandas performance, and it corrects the instinct that transfers from ordinary Python.
In plain Python, "loop over the rows and process each" is natural and correct.
In pandas it is catastrophic, because the data is *columnar and typed*, and the whole point of that layout is to operate on columns in C.
The 1,000x is not a micro-optimization; it is the difference between a query that returns in a millisecond and one that takes a second and a half, per operation, which in a pipeline of many operations is the difference between interactive and unusable.

So the rule from §57.2 is not stylistic; it is a 1,000x rule.
**Vectorize every DataFrame computation, never `iterrows`.**
And the deeper lesson, threaded through Deep T and Deep U, is that *columnar, typed storage is fast only if you use it columnarly*: the DataFrame (like the NumPy array, like the structured array) delivers its speed through whole-column operations, and a row loop throws that entire advantage away, reducing a C-speed engine to interpreted per-element Python.
This is why data engineering thinks in columns, transformations, and aggregations rather than rows and loops, the data model rewards it by three orders of magnitude, and **Book III**'s pipelines are built on exactly this columnar discipline.

---

## 57.4 Edges and failure modes

**Never use `iterrows` on large data.** §57.2, §57.3.
Over 1,000x slower than vectorized. Express the computation as column operations, masks, groupbys, or merges. If you must loop small data, use `itertuples()` (far faster than `iterrows`), never `iterrows`.

**Chained indexing and the `SettingWithCopyWarning`.**
`df[df["a"] > 0]["b"] = 1` may assign to a temporary copy, not `df` (the warning). Use `.loc[df["a"] > 0, "b"] = 1` for a single, unambiguous operation. Pandas 3.0's copy-on-write changes this behaviour, another reason it varies across versions.

**dtypes matter, and `object` is a trap.**
A column of Python objects (`object` dtype, historically the default for strings) loses vectorization, operations fall back to per-element Python. Use proper dtypes (numeric, the new string dtype in pandas 3.0, `category` for low-cardinality). Mixed-type columns become `object` and slow.

**Missing data (`NaN`) propagates and changes dtype.**
Introducing `NaN` into an integer column promotes it to `float64` (since `NaN` is a float), and `NaN` propagates through arithmetic (`NaN + 1` is `NaN`). Handle missing data explicitly (`fillna`, `dropna`, nullable dtypes).

**The index is not free and not just row numbers.**
Operations align on the *index*; a mismatched index silently produces `NaN`s in arithmetic between Series. `reset_index`/`set_index` matter. The index is a labeling and alignment tool, not decoration.

**Copies versus views (as in NumPy).**
Some operations return views, some copies (Chapter 99); pandas 3.0's copy-on-write makes this more predictable but changes behaviour from 2.x. Do not rely on mutating a slice affecting the original.

**Version differences are real.**
pandas 2.x versus 3.0 differ in the default string dtype (`object` -> `str`), copy-on-write, and reprs. Code and, especially, exact output can differ across versions, which is why this chapter's listing reports version-stable facts.

**`apply` is often a disguised loop.**
`df.apply(f, axis=1)` calls `f` per row, nearly as slow as `iterrows`. Prefer vectorized expressions; use `apply` only when no vectorized form exists, and on columns (`axis=0`) or Series where possible.

---

## 57.5 Connections

**Backward.**
The DataFrame is Chapter 104's structured array (typed columns) with labels, alignment, and a rich API. Its columns are NumPy arrays (Deep T), so column operations are Chapter 96's vectorization. Boolean filtering is Chapter 102's masks. Missing-data dtype promotion is Chapter 98 (dtypes). Views versus copies is Chapter 99.

**Forward.**
`groupby` (split-apply-combine), `merge`/`join` (combining frames), reshaping (`pivot`/`melt`), time-series operations, and IO (CSV/Parquet/SQL) are the rest of **Deep U**. Apache Arrow (the columnar interchange format pandas increasingly uses) and out-of-core/distributed frames (Dask, Polars) are Deep U/distributed topics. The performance rule connects to Deep T's vectorization throughout.

**Across books.**
The DataFrame is the primary data structure of **Book III**'s pipelines: features, labels, market data, and results all live in DataFrames, and the "columns not rows" rule is the difference between a pipeline that processes a dataset in seconds and one that takes hours. The order-book system's analytics and backtesting hold their data in DataFrames (or the columnar engines that share the model), compute every transformation as vectorized column operations, groupbys, and merges, and treat a row loop as a defect, so a computation over millions of records is a handful of C passes, the §57.3 1,000x rule as the architecture of the data path. Deep U is where **Book II**'s numeric foundations become **Book III**'s data engineering.

---

## 57.6 Exercises

**1. Build and operate.** Reproduce §57.1: create a DataFrame, inspect its shape/columns/dtypes, access a column as a Series, compute a vectorized column, filter with a mask, and add a computed column. Explain how it extends the structured array of Chapter 104.

**2. Prove the rule.** Reproduce §57.3. Confirm the vectorized version is over 1,000x faster than `iterrows`. Then try `itertuples` and `apply(axis=1)` and place them on the spectrum. Explain why `iterrows` is the slowest.

**3. Vectorize a loop.** Take a row loop that computes a derived column with an `if`/`else` and rewrite it with `np.where` / a boolean mask (Chapter 102) as a vectorized column. Measure both. Explain the transformation.

**4. The object-dtype trap.** Create a column with mixed types (forcing `object` dtype) and show a vectorized operation on it is slow (per-element Python), then fix the dtype and show the speedup. Explain why `object` columns lose vectorization.

**5. The design question.** pandas stores data columnar and typed (like NumPy) and rewards column operations with a 1,000x speedup over row loops. Argue why this data model is right for data engineering, using §57.3, and why the "think in columns" discipline is the foundational skill. Connect it to Chapter 96 (NumPy) and Chapter 104 (structured arrays).

---

## 57.7 Summary and cross-references

- A **pandas DataFrame** is **named, typed columns** (each a `Series`, backed by a NumPy array) sharing a row **index**, the structured array of Chapter 104 with labels, alignment, and a rich API. Columns have dtypes; operations run in C over contiguous typed arrays.
- **Operate on whole columns:** vectorized arithmetic (`df["a"] * df["b"]`), boolean masks (`df[df["a"] > 0]`, Chapter 102), reductions (`.sum()`), groupbys, and merges, all in C.
- **The cardinal rule: never loop over rows.** **Measured:** summing `price*qty` over 200,000 rows is over **1,000x** faster vectorized than with `iterrows()` (which builds a Series object per row). A row loop over a large DataFrame is the number-one pandas performance mistake.
- **Edges:** `object` dtype loses vectorization (use proper dtypes); `NaN` promotes int to float and propagates; the index aligns operations (mismatches yield `NaN`); chained indexing warns; `apply(axis=1)` is a disguised loop; pandas 2.x/3.0 differ (string dtype, copy-on-write).

**Cross-references.** Structured arrays (the ancestor) → Chapter 104. Vectorization → Chapter 96. Boolean masks → Chapter 102. dtypes and missing data → Chapter 98. Views/copies → Chapter 99. `groupby`, `merge`, reshaping, IO, Arrow, distributed frames → the rest of Deep U. The Book III data-pipeline seam → Deep U / Book III.
