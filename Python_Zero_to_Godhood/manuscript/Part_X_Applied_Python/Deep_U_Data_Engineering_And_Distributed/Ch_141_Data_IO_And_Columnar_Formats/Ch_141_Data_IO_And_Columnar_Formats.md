# Chapter 60: Data IO and Columnar Formats

Data has to be read and written, and the **format** you choose is one of the most consequential and most overlooked decisions in a data pipeline.
The default reflex is **CSV**, text, universal, human-readable, and it is the right choice for exactly two things: humans reading it, and interop with tools that require text.
For everything else, a data pipeline reading and writing its own intermediate and final data, CSV is the wrong choice, and **Parquet** is the right one.
This chapter shows why, with a measurement that is decisive: Parquet is **2x smaller** on disk and **12-14x faster** to read than CSV for the same table, *and* it preserves the dtypes CSV throws away.

The reason is the same **columnar** principle that runs through Deep T (NumPy) and Deep U (pandas).
CSV is text and row-oriented: every value is a string, stored row by row, uncompressed, with no type information, so reading it means parsing text and *guessing* types.
Parquet is binary and column-oriented (the Apache Arrow lineage, Deep T): each column is stored contiguously, typed and compressed, with the schema embedded, so reading it means loading typed columns directly into NumPy arrays, no parsing, no guessing.
The format that stores data the way the computation uses it (columnar, typed) is faster to read, smaller to store, and safe across a round trip.

**This is Deep U's IO chapter.**
It applies the columnar principle (Deep T, Chapter 104) to *storage*, connects to the DataFrame (the columnar in-memory structure, Chapter 57), and is essential to **Book III**'s pipelines, which move data between stages as files.

## Section index

- **60.1** CSV versus Parquet: round trip, dtypes, columns
- **60.2** Choosing a format
- **60.3** Measurement: size and read speed
- **60.4** Edges and failure modes
- **60.5** Connections
- **60.6** Exercises
- **60.7** Summary and cross-references

Listings live under `code/ch141/` and are re-executed by `make verify` on both verification interpreters.

---

## 60.1 CSV versus Parquet: round trip, dtypes, columns

```python
# code/ch141/l01_io.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- write and read back through both formats (round trip) ---
  CSV round-trip values match     : True
  Parquet round-trip values match : True
--- Parquet PRESERVES dtypes; CSV infers them on read ---
  original qty dtype        : int64
  Parquet-read qty dtype    : int64   (preserved)
  Parquet preserved int64   : True
--- Parquet is smaller (columnar + compression) ---
  both files were written   : True
--- Parquet stores the schema; a column can be read WITHOUT the rest ---
  read only the 'qty' column : ['qty']   (columnar: skip other columns)
--- the rule ---
  use Parquet (columnar, typed, compressed) for data pipelines: smaller,
  faster to read, dtype-preserving; use CSV only for human/interop needs
```

Both formats **round-trip the values** correctly (the numbers survive write-and-read), so correctness of *values* is not the differentiator. Three other properties are.

**Parquet preserves dtypes; CSV does not.**
The original `qty` column is `int64`. Written to Parquet and read back, it is *still* `int64`, the schema is stored *in the file*. Written to CSV, it becomes text (`"100"`, `"200"`, ...), and on read pandas must *infer* the type from the text, which it often gets right but sometimes gets wrong (a column of ZIP codes read as integers losing leading zeros, a column with one stray string forcing the whole column to `object`, dates read as strings). CSV's typelessness is a recurring source of data-corruption bugs; Parquet's embedded schema eliminates them.

**Parquet is columnar, so you can read one column without the rest.**
`pd.read_parquet(path, columns=["qty"])` reads *only* the `qty` column, skipping the others entirely, because Parquet stores each column separately. For a wide table where you need a few columns, this reads a fraction of the file. CSV, being row-oriented text, must read and parse the *whole* file to get any column.

**Parquet is smaller** (both files are written here; the size win is dramatic at scale, §60.3), because columnar storage compresses far better, values in a column are similar (same type, often similar magnitude), which compresses well, where a CSV row mixes types and does not.

So Parquet is *typed* (schema in the file), *columnar* (read columns independently, compresses well), and *binary* (no text parsing), three properties that make it the right format for a data pipeline, while CSV's only advantages are human-readability and universal interop.

---

## 60.2 Choosing a format

The decision is straightforward once you separate the two use cases.

**Use Parquet (or another columnar binary format) for data pipelines.** §60.3.
Whenever your *program* writes data that your program (or another program) will *read*, intermediate stages, cached datasets, feature stores, final outputs consumed by analytics, Parquet is the default: smaller, much faster to read, dtype-preserving, and column-selectable. This is the overwhelming majority of a pipeline's IO.

**Use CSV only for humans and text-only interop.**
CSV earns its place for exactly two things: a human needs to open the file (in a spreadsheet, an editor), or a tool in the chain *requires* text CSV and cannot read Parquet. For these, CSV's readability and universality are worth its costs. Outside them, it is the wrong choice.

**Know the format landscape:**

- **Parquet:** columnar, compressed, typed, the standard for analytical data at rest. Reads column subsets efficiently. The default.
- **Arrow / Feather:** the in-memory columnar standard (and its file form), zero-copy shareable across tools and languages (the buffer-protocol idea, Chapter 44, at data-interchange scale). Fastest for interchange between Arrow-aware tools.
- **CSV:** text, universal, human-readable, typeless, slow, large. Interop and inspection only.
- **JSON:** text, self-describing, good for nested/irregular data and APIs, but slow and large for tabular data.
- **Databases (SQL) / HDF5:** for queryable or scientific storage (Deep U / Deep R topics).

The rule: **default to Parquet for pipeline data; use CSV/JSON only when a human or an external text-only tool requires it.**
The instinct to "just use CSV" because it is simple is a false economy, it silently loses types (bugs), reads slowly (a 12-14x tax on every load), and stores large (2x the disk), and the alternative (`df.to_parquet` / `pd.read_parquet`) is exactly as simple to write.
This is the same lesson as the whole columnar arc: the format that matches how the data is used (typed columns) is faster, smaller, and safer than the format that does not (untyped text rows).

---

## 60.3 Measurement: size and read speed

**Methodology.** `code/ch141/bench_formats.py`.
A 500,000-row typed table (`id` int, `price` float, `qty` int) written to CSV and Parquet, comparing file size and read time (reads warmed up, so the Parquet engine's one-time init is not charged).
CPython 3.13.5, pandas 2.2.3, pyarrow 19.0.0, Apple M3 Pro, macOS 27.0, arm64.

| 500,000-row table | CSV | Parquet | Parquet advantage |
|---|---|---|---|
| file size | 13.8 MB | 6.9 MB | **2.0x smaller** |
| read time | 50 ms | 4 ms | **12x faster** |

Parquet is **2x smaller** on disk and **12x faster** to read (14x on 3.14.6), for identical data.
The size win is compression over columnar data (similar values per column compress well).
The speed win is the absence of text parsing: CSV must scan 13.8 MB of text, split on commas, and convert each field from string to the right type, per value; Parquet loads already-typed, already-columnar data straight into NumPy arrays (Deep T), no parsing, no conversion.

And the measurement *understates* Parquet's advantage, because it charges only what this benchmark measured:

- The **dtype safety** (§60.1) is not a number but a correctness property, CSV's type inference is a bug source Parquet eliminates.
- The **column selection** (§60.1) means reading a few columns of a wide table is a fraction of even this Parquet time, while CSV must read everything.
- The gap **grows with data size** and width, at gigabytes, the 12-14x read gap and 2x size gap compound into the difference between a pipeline that runs and one that does not.

So the guidance is unqualified for pipeline data: **use Parquet.**
It is faster (12-14x reads), smaller (2x), and safer (typed) than CSV, at no extra code cost.
This closes the columnar arc that spans Deep T and Deep U: NumPy made *computation* fast by storing values in typed contiguous arrays (Chapter 96); the DataFrame made *tabular data* fast the same way (Chapter 57); and Parquet makes *storage* fast, small, and safe by writing data in that same columnar, typed form.
The principle is one, columnar and typed beats row-oriented and untyped, at every layer, in memory and on disk, and it is the architectural foundation of **Book III**'s data platform.

---

## 60.4 Edges and failure modes

**CSV loses types; Parquet preserves them.** §60.1.
CSV re-infers types on read (leading-zero ZIP codes become ints, mixed columns become `object`, dates become strings). Parquet stores the schema. For any typed data, Parquet avoids a class of corruption bugs.

**Parquet needs an engine (pyarrow or fastparquet).**
`to_parquet`/`read_parquet` require `pyarrow` (or `fastparquet`) installed. CSV needs nothing. This is the one dependency cost of Parquet, well worth it for pipelines.

**CSV parsing has many footguns.**
Delimiters, quoting, embedded newlines, encodings (Deep D), and locale-specific decimal separators all break CSV parsing. `read_csv` has dozens of parameters to handle them, each a chance to get it wrong. Parquet, being binary and self-describing, has none of these.

**Parquet is not human-readable or appendable.**
You cannot open a Parquet file in an editor, and appending is not as trivial as `>>` on a CSV (Parquet is written as complete files/row-groups). For streaming appends or human inspection, CSV (or a database) fits better.

**Column selection needs the columnar read.** §60.1.
`read_parquet(columns=[...])` is what makes column selection fast; reading the whole file and then selecting columns loses the benefit. Push the column selection into the read.

**Compression and row-group tuning.**
Parquet supports codecs (snappy default, zstd, gzip) and row-group sizes that trade compression ratio against read speed. Defaults are good; tune only with measured need.

**Version and schema evolution.**
Parquet handles schema evolution (adding columns) reasonably, but reading files written by very different tool versions can have edge cases. Within a pipeline using one writer/reader, this is a non-issue.

**Do not use CSV as a pipeline's internal format.** §60.2.
The "just use CSV" reflex costs types, speed, and size. Use Parquet for internal data; CSV only at human/interop boundaries.

---

## 60.5 Connections

**Backward.**
Parquet's columnar, typed layout is the on-disk form of Chapter 57's DataFrame and Chapter 104's structured array, and the Apache Arrow lineage is the buffer-protocol / zero-copy idea (Chapter 44) at data scale. Reading typed columns directly into NumPy arrays is Deep T. CSV's encoding footguns are Deep D (text/bytes).

**Forward.**
Apache Arrow (in-memory columnar interchange), partitioned Parquet datasets (splitting by key for parallel/selective reads), predicate/column pushdown (reading only needed rows/columns), and out-of-core/distributed IO (Dask, Spark reading Parquet) are the rest of **Deep U**. Databases and SQL (queryable storage) are Deep U / Deep R. Compression is a Deep Q topic.

**Across books.**
Format choice is an architectural decision in **Book III**'s data platform: intermediate datasets, feature stores, and model inputs are stored as Parquet (typed, columnar, compressed), so pipeline stages read their inputs 10x faster and never suffer a CSV type-inference bug, while CSV appears only at the human-facing edges (a report, an export). The order-book system stores its historical and derived data as partitioned Parquet, reads only the columns and partitions each job needs (column and predicate pushdown), and reserves CSV for human-inspected samples, so a backtest over years of data loads in seconds instead of minutes, the §60.3 columnar advantage as the foundation of a data platform that scales. Deep U's arc, DataFrame, groupby, merge, columnar IO, is the toolkit; columnar-and-typed is the principle throughout.

---

## 60.6 Exercises

**1. Round-trip both.** Reproduce §60.1: write a typed DataFrame to CSV and Parquet, read both back, and confirm values match but only Parquet preserves the dtype. Then read a single column from Parquet. Explain the three Parquet advantages.

**2. Measure it.** Reproduce §60.3. Confirm Parquet is smaller and faster. Then widen the table (more columns) and read only a few via `columns=`, and show it is faster still. Explain columnar column-selection.

**3. The CSV type trap.** Create a column of ZIP codes with leading zeros (`"01234"`), write to CSV, read back, and show the leading zeros lost (inferred as int). Then via Parquet and show them preserved. Explain CSV's typelessness.

**4. When CSV wins.** Identify two scenarios where CSV is the right choice (a human opening the file, a text-only external tool) and one where it is clearly wrong (a pipeline's internal cache). Justify each with §60.2.

**5. The design question.** Parquet (columnar, typed, binary) beats CSV (row, typeless, text) on size, speed, and safety for pipeline data. Argue why the columnar-and-typed principle wins at the storage layer as it does in memory (NumPy, pandas), and why "just use CSV" is a false economy for pipelines. Connect it to Arrow and the whole columnar arc.

---

## 60.7 Summary and cross-references

- **Format matters.** **CSV** is text, row-oriented, typeless, and uncompressed, universal and human-readable, but slow, large, and type-losing. **Parquet** is binary, columnar, typed (schema embedded), and compressed.
- **Parquet advantages:** **preserves dtypes** (CSV re-infers, sometimes wrongly), **reads column subsets** without the rest (columnar), and is **smaller and faster**.
- **Measured:** for a 500,000-row table, Parquet is **2.0x smaller** and **12-14x faster** to read than CSV, because it skips text parsing and loads typed columns directly into NumPy arrays. The gap grows with size and width.
- **The rule:** **use Parquet for pipeline data** (internal, intermediate, final); **use CSV only for humans and text-only interop**. The "just use CSV" reflex costs types, speed, and size at no code-cost saving.
- **Edges:** Parquet needs an engine (pyarrow); it is not human-readable or trivially appendable; CSV parsing has many footguns (delimiters, quoting, encodings); push column selection into the read.

**Cross-references.** The columnar DataFrame → Chapter 57. Structured/columnar storage → Chapter 104. Zero-copy / Arrow lineage → Chapter 44 (buffer protocol). Typed columns into NumPy → Deep T. CSV encoding footguns → Deep D. Arrow, partitioned datasets, pushdown, distributed IO, databases → the rest of Deep U / Deep R. Book III data platform → Deep U / Book III.
