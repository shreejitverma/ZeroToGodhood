# Chapter 63: Reshaping: Pivot and Melt

The same data can be laid out two ways, and choosing, and converting between, them is a core data-engineering skill.
**Long** (or *tidy*) format has one row per observation, with a column naming the variable: `(date, metric, value)`, one row for each metric on each date.
**Wide** format spreads a variable across columns: `date` as the index, each metric its own column, one row per date.
Both describe identical data; they differ in shape, and analysis, storage, and display each favour a different one.

The operations that convert between them are **`pivot`** (long to wide) and **`melt`** (wide to long), with **`pivot_table`** as pivot-plus-aggregation (the spreadsheet pivot table).
The organizing principle is the **tidy data** idea: keep data in *long* format for a pipeline, because tidy data groups, filters, joins, and plots *uniformly regardless of how many variables there are*, and reshape to *wide* only at the edges, for a human-readable display or a dense numeric matrix to feed a model.
The measurement adds the storage angle: for *dense* data, wide is more compact (measured **2.9x** smaller), because long format repeats the key columns for every value.

**This is Deep U's reshaping chapter.**
It builds on the DataFrame (Chapter 57) and complements groupby (Chapter 58, `pivot_table` is a groupby reshaped) and the tidy-data foundation that **Book III**'s feature pipelines rest on.

## Section index

- **63.1** Pivot, melt, and pivot_table
- **63.2** Tidy data: which shape, when
- **63.3** Measurement: long versus wide memory
- **63.4** Edges and failure modes
- **63.5** Connections
- **63.6** Exercises
- **63.7** Summary and cross-references

Listings live under `code/ch144/` and are re-executed by `make verify` on both verification interpreters.

---

## 63.1 Pivot, melt, and pivot_table

```python
# code/ch144/l01_reshape.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- LONG (tidy) format: one row per (date, metric) observation ---
  long shape (rows, cols) : (4, 3)
--- pivot: long -> WIDE (metric values become columns) ---
  wide columns (the metrics) : ['a', 'b']
  wide 'a' column by date    : [1, 3]   (d1=1, d2=3)
  wide shape                 : (2, 2)
--- melt: WIDE -> long (columns become rows) ---
  melted back to rows : 4
  metric column values : ['a', 'a', 'b', 'b']
--- pivot_table: pivot WITH aggregation (handles duplicates) ---
  pivot_table sum per group : {'x': 30, 'y': 30}   (x: 10+20, y: 30)
--- the rule ---
  pivot (long->wide), melt (wide->long), pivot_table (pivot + aggregate);
  keep data tidy (long) for analysis, reshape to wide for display/compactness
```

**Long (tidy) format** has one row per observation: `(d1, a, 1)`, `(d1, b, 2)`, `(d2, a, 3)`, `(d2, b, 4)`, four rows, three columns, with `metric` naming the variable and `value` holding it. Each *observation* is a row; the *variable* is data, not structure.

**`pivot` reshapes long to wide.**
`long.pivot(index="date", columns="metric", values="value")` makes the `metric` values (`a`, `b`) into *columns*, indexed by `date`. The result is a 2x2 grid: rows are dates, columns are metrics, cells are values (`wide["a"]` is `[1, 3]`, the `a` metric across the two dates). The variable that was *data* (the `metric` column) has become *structure* (column headers).

**`melt` reshapes wide to long** (the inverse).
`flat.melt(id_vars="date", var_name="metric", value_name="value")` takes the wide columns (`a`, `b`) and stacks them back into rows under a `metric` column, returning to the four-row long form. Structure (column headers) becomes data (a `metric` column) again.

**`pivot_table` is pivot with aggregation.**
Plain `pivot` requires unique index/column pairs (it fails on duplicates). `pivot_table` *aggregates* duplicates: `dup.pivot_table(index="group", values="value", aggfunc="sum")` sums the values per group (`x`: `10+20=30`). This is the spreadsheet "pivot table", a groupby (Chapter 58) reshaped into a grid, and it is what you use when the data has multiple values per cell.

So the trio: `pivot` (long to wide, unique pairs), `melt` (wide to long), `pivot_table` (pivot with aggregation for duplicates). They convert freely between the two shapes of the same data.

---

## 63.2 Tidy data: which shape, when

The shapes are interconvertible, so the real skill is knowing *which shape to work in*, and the answer is a principle: **keep data tidy (long) for pipelines; reshape to wide at the edges.**

**Long (tidy) is the analysis form.**
Tidy data, one variable per column, one observation per row, one value per cell, is the canonical shape for data work because it is *uniform*: operations do not depend on how many variables there are.

- **groupby** works the same whether you have 2 metrics or 200 (group by `metric`).
- **filter** is uniform (`df[df["metric"] == "a"]`).
- **join** aligns on the observation keys.
- **plot** maps columns to aesthetics regardless of variable count.

A *wide* frame with one column per metric, by contrast, requires code that names each metric column, so adding a metric means changing the code. Tidy data scales to any number of variables with the *same* code. This is why data pipelines, and the tools built for them (the plotting grammar, the modeling frameworks), prefer long format: it is the shape where the code does not grow with the data's variety.

**Wide is for display and dense matrices.**
Reshape to wide at the *edges* of a pipeline:

- **Human display:** a wide table (dates down, metrics across) is what a person reads; long format is verbose and hard to scan.
- **Dense numeric matrix:** a model or a linear-algebra operation wants a 2D array (rows = samples, columns = features), which is wide, so the final step before modeling often pivots to wide (a feature matrix).
- **Compactness for dense data:** §63.3, wide stores keys once.

**The workflow:** ingest and process in long/tidy form (uniform, scalable operations), and pivot to wide only at the end, for a report or a model input.
`melt` any wide data you *receive* into long, work in long, and `pivot` to wide only when you *emit* a display or matrix.

The rule: **tidy (long) is the working shape; wide is a presentation/matrix shape.** Reshaping (`pivot`/`melt`/`pivot_table`) is how you move between the working form and the edges, and recognizing which form a given step wants, and reshaping deliberately, is the skill.

---

## 63.3 Measurement: long versus wide memory

**Methodology.** `code/ch144/bench_reshape.py`.
A 10,000 x 20 *dense* grid (every date-metric combination present), stored in long format (200,000 rows) and wide format (10,000 x 20), comparing memory (`memory_usage`).
CPython 3.13.5, pandas 2.2.3.

| 10,000 x 20 dense grid | memory | rows/shape |
|---|---|---|
| wide format | 1.6 MB | 10,000 x 20, keys once |
| long format | 4.6 MB | 200,000 rows, keys repeated |
| long / wide | **2.9x** | |

Long format uses **2.9x** more memory than wide for this dense grid (identical on both interpreters).
The reason is *key repetition*: long format stores the `date` key `20` times (once per metric) and the `metric` key `10,000` times (once per date), so the two key columns dominate, while wide stores each `date` once (the index) and each `metric` once (a column header), plus the value matrix.
For *dense* data (every combination present), this makes wide clearly more compact.

But the measurement's lesson is a *caveat*, not a directive, and it is important not to over-read it.
Memory is **not** the main reason to choose a shape:

- **For dense data, wide is smaller** (2.9x here), so if you must store a dense grid compactly, wide (or a plain 2D array, Deep T) wins.
- **For sparse or heterogeneous data, long is smaller** (and often the *only* sensible form): if most date-metric combinations are *absent*, wide wastes a cell (a `NaN`) for every missing combination, while long simply omits the absent rows. A sparse wide grid is mostly `NaN`; the equivalent long frame has only the present observations.
- **And the shape choice is mostly about *operations*, not storage** (§63.2): tidy/long is the analysis form because operations are uniform, and that matters far more than the 2.9x.

So the guidance stands from §63.2, refined: **work in long/tidy form** (for uniform, scalable operations and to handle sparsity), and reshape to wide only at the edges (display, dense matrix), *and* be aware that for dense data wide is more compact if storage is the concern.
This completes Deep U's structural vocabulary: the DataFrame holds typed columns (Chapter 57), groupby aggregates (Chapter 58), merge combines tables (Chapter 59), and pivot/melt reshape between the long working form and the wide presentation form.
**Book III**'s feature pipelines live in tidy/long data, processing uniformly regardless of feature count, and pivot to a wide feature matrix only at the boundary where a model consumes it, the §63.2 workflow as the shape of the pipeline.

---

## 63.4 Edges and failure modes

**`pivot` fails on duplicate index/column pairs.** §63.1.
Plain `pivot` requires unique `(index, columns)` combinations; duplicates raise. Use `pivot_table` with an `aggfunc` to aggregate duplicates.

**`pivot` to wide creates `NaN` for absent combinations.**
Pivoting sparse long data to wide fills missing combinations with `NaN` (Chapter 62), potentially a mostly-`NaN` grid. This is the sparsity cost of wide format; keep sparse data long.

**Choose the working shape for operations, not memory.** §63.2, §63.3.
Tidy/long is the analysis form (uniform operations). The 2.9x memory difference rarely justifies working in wide.

**`melt` needs the id_vars specified.**
`melt(id_vars=[...])` keeps the identifier columns and stacks the rest. Forgetting `id_vars` (or `value_vars`) melts the wrong columns. Be explicit about which columns are identifiers versus variables.

**Multi-level results from multiple index/column keys.**
Pivoting on multiple keys produces a MultiIndex (hierarchical index/columns), which is powerful but adds complexity (`.stack()`/`.unstack()` navigate it). MultiIndex reshaping is a step up in difficulty; flatten with `reset_index` when you need a simple frame.

**`stack`/`unstack` are the index-level reshapers.**
`stack` (columns to index) and `unstack` (index to columns) reshape along the index levels, related to melt/pivot but operating on the index structure. They are the tools for MultiIndex reshaping.

**Reshaping is not free for large data.**
Pivoting a very large long frame to a wide grid materializes the full (possibly sparse, `NaN`-filled) matrix, which can be large. For big sparse data, aggregate or filter before pivoting.

**Round-tripping may reorder or retype.**
`melt` then `pivot` (or vice versa) may not perfectly preserve column order or dtypes. Do not rely on byte-identical round trips; verify the data, not the exact layout.

---

## 63.5 Connections

**Backward.**
`pivot_table` is `groupby` (Chapter 58) reshaped into a grid. Reshaping operates on the DataFrame's columns and index (Chapter 57). Pivoting sparse data creates missing values (Chapter 62). Wide dense data is close to a 2D NumPy array (Deep T).

**Forward.**
`stack`/`unstack` and MultiIndex reshaping, `crosstab` (frequency tables), and `get_dummies` (one-hot encoding, a categorical-to-wide reshape) are the rest of **Deep U**. The tidy-data principle underlies plotting grammars (seaborn, plotnine) and modeling frameworks (Deep W). The wide feature matrix is the input to ML (Deep W).

**Across books.**
The tidy/long working form and wide feature matrix are the two poles of **Book III**'s feature engineering: data is ingested and transformed in tidy form (uniform operations regardless of feature count, easy to add features), and pivoted to a wide `(samples x features)` matrix only at the boundary where a model consumes it. The order-book system holds its per-symbol, per-time observations in tidy/long form through the pipeline (so a new metric is a new row type, not a code change), reshapes to wide for display dashboards and for the feature matrices its models consume, and uses `pivot_table` for its summary grids, the §63.2 workflow as the pipeline's structure. Deep U's structural quartet, DataFrame, groupby, merge, reshape, is the complete grammar; tidy data is the guiding principle.

---

## 63.6 Exercises

**1. Round-trip the shapes.** Reproduce §63.1: pivot long to wide, melt back to long, and confirm the data survives. Then use `pivot_table` on data with duplicates. Explain when `pivot` fails and `pivot_table` is needed.

**2. Tidy operations.** Take a wide frame with several metric columns and a computation that must name each column. Melt to long and do the same computation uniformly (one groupby). Show adding a metric requires no code change in the long version. Explain the tidy-data advantage.

**3. Measure the shapes.** Reproduce §63.3. Confirm wide is more compact for dense data. Then make the data *sparse* (most combinations absent) and show long becomes smaller (wide is mostly `NaN`). Explain the density trade-off.

**4. Pivot to a feature matrix.** Take tidy `(sample, feature, value)` data and pivot to a wide `(sample x feature)` matrix suitable for a model. Explain why the model wants wide and the pipeline wanted long.

**5. The design question.** Data is interconvertible between long and wide, yet tidy/long is preferred as the working form. Argue why, using the uniformity of operations (§63.2) and sparsity handling, and why wide is a presentation/matrix shape. When does the §63.3 memory difference actually matter?

---

## 63.7 Summary and cross-references

- The same data has two shapes: **long (tidy)** (one row per observation, a variable column) and **wide** (a variable spread across columns). **`pivot`** reshapes long to wide, **`melt`** wide to long, **`pivot_table`** pivots *with aggregation* (for duplicates, a groupby grid).
- **Tidy (long) is the working form:** operations (groupby, filter, join, plot) are **uniform regardless of variable count**, so the code does not grow with the data's variety, and it handles sparsity. **Wide is a presentation/matrix form** (human display, dense feature matrix). Reshape at the edges.
- **Measured:** for a dense 10,000 x 20 grid, long uses **2.9x** more memory than wide, because long repeats the key columns per value while wide stores keys once. But for **sparse** data long is smaller, and the shape choice is mostly about **operations, not memory**.
- **Workflow:** ingest and process in long/tidy form; pivot to wide only for display or a model input.
- **Edges:** `pivot` fails on duplicate pairs (use `pivot_table`); pivoting sparse data creates `NaN` grids (keep sparse data long); multiple keys create MultiIndex; specify `id_vars` for `melt`; reshaping large data materializes big matrices.

**Cross-references.** `pivot_table` as reshaped groupby → Chapter 58. Columnar DataFrame → Chapter 57. Pivoting creates missing values → Chapter 62. Wide dense data as a 2D array → Deep T. `stack`/`unstack`, `crosstab`, `get_dummies`, tidy plotting, feature matrices → the rest of Deep U / Deep W. Book III feature engineering → Deep U / Book III.
