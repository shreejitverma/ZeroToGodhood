# Chapter 104: Structured Arrays and Record Dtypes

Every array so far has been homogeneous: one dtype, all the way through.
But real data is *tabular*, a row has a name (text), an age (int), a score (float), three different types per record.
The Python reflex is a list of dicts (`[{"name": ..., "age": ..., "score": ...}, ...]`), and it works, but it is the Chapter 96 anti-pattern at the record level: each record is a dict (a hash table) of *boxed* Python objects, so a million records is a million dicts and several million object headers.
NumPy's answer is the **structured array**: a dtype with **named fields of different types**, so one contiguous typed block holds the records, columnar, like a table's columns laid side by side.
A million two-field records take **15 MB** as a structured array versus **184 MB** as a list of dicts, **12x** less, and each field is an ndarray *view* you vectorize (`a["age"].mean()`) instead of looping.

This chapter continues **Deep T** with structured arrays and record dtypes: heterogeneous named fields in one array, field access as a column view, and masks that span fields.
It is the foundation the pandas `DataFrame` is built on, tabular data with the memory and speed of arrays.

## Section index

- **104.1** A dtype with named fields
- **104.2** Columns are views; masks span fields
- **104.3** Measurement: memory vs a list of dicts
- **104.4** Edges and failure modes
- **104.5** Connections
- **104.6** Exercises
- **104.7** Summary and cross-references

Listings live under `code/ch104/` and are re-executed by `make verify` on both interpreters (both with NumPy 2.1.3).

---

## 104.1 A dtype with named fields

```python
# code/ch104/l01_structured.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a structured dtype: named fields, each with its own type ---
  dtype       : [('name', '<U10'), ('age', '<i4'), ('score', '<f8')]
  one record  : ('ann', 30, 9.5)   (a[0] is a record)
--- field access returns a VIEW of that column (an ndarray) ---
  a['age']         : [30, 25, 41]
  a['age'].mean()  : 32.0   (vectorized column op)
  a['score'].max() : 9.5
--- boolean masks work ACROSS fields ---
  a[a['age'] > 26]['name'] : ['ann', 'cy']
--- it is ONE contiguous typed block (record itemsize) ---
  itemsize (bytes/record) : 52   (40 name + 4 age + 8 score)
  field names             : ('name', 'age', 'score')
--- the rule ---
  a structured array is columnar typed records in one C block:
  field access is a view, columns vectorize, masks span fields
```

A **structured dtype** is a list of `(name, type)` pairs: `np.dtype([("name", "U10"), ("age", "i4"), ("score", "f8")])` declares a record of a 10-character Unicode string, a 4-byte int, and an 8-byte float.
`np.zeros(3, dtype=dt)` makes an array of three such records.
Each record is heterogeneous, but the array is still **one contiguous block**: the records sit end to end, each `itemsize` bytes wide (here 52: 40 for the string, 4 for the int, 8 for the float).

You address the array two ways.
By **record**: `a[0]` is the whole first record, `('ann', 30, 9.5)`.
By **field**: `a["age"]` is the `age` column across all records, `[30, 25, 41]`.
The field name is the column selector, and what comes back is a plain ndarray, so it vectorizes: `a["age"].mean()` is `32.0`, `a["score"].max()` is `9.5`, no loop.
`a.dtype.names` lists the fields.
This is a *table*: named typed columns, stored contiguously, operated on as arrays.

---

## 104.2 Columns are views; masks span fields

Field access returns a **view** (Chapter 99), not a copy: `a["age"]` is a window into the `age` bytes of each record (a *strided* view, since the ages are `itemsize` bytes apart, interleaved with the other fields).
So writing `a["age"] = [...]` writes *through* into the array, and reading `a["age"]` costs nothing, it is the same memory, reinterpreted as one column.
That is why columns vectorize at full array speed: `a["age"].mean()` reduces over the actual bytes, no gathering, no copy.

Boolean masks (Chapter 102) **span fields**, which is what makes structured arrays genuinely tabular.
`a["age"] > 26` is a boolean mask computed from *one* field, and `a[mask]` selects the *whole records* where it holds, then `["name"]` reads that column from the selected records: `a[a["age"] > 26]["name"]` is `['ann', 'cy']`, "the names of everyone older than 26".
This is a filter-then-project, a SQL `SELECT name WHERE age > 26`, expressed in array operations and running in C.
Mask on one field, select records, read another field: the pattern generalizes to any tabular query.

The rule: **a structured array is columnar typed records in one contiguous block, field access is a view you vectorize, and masks on one field select whole records across all fields.**
It gives tabular data the memory layout and speed of arrays.
This is exactly what pandas formalizes: a `DataFrame` is (morally) a set of typed columns with an index and a rich query API, built on this same idea of named, typed, contiguous columns, so everything here is the substrate under the tool you will actually reach for, and knowing it explains why column operations in pandas are fast and row-by-row `.iterrows()` is slow.

---

## 104.3 Measurement: memory vs a list of dicts

**Methodology.** `code/ch104/bench_structured.py`.
One million records of `(x: float64, y: int64)`, built two ways: a NumPy structured array (`np.zeros(N, dtype=[("x","f8"),("y","i8")])`) versus a Python list of dicts (`[{"x": 0.0, "y": 0} for _ in range(N)]`).
Peak memory of building each via `tracemalloc`.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64, NumPy 2.1.3.

| 1,000,000 records `(x: f8, y: i8)` | peak memory | vs structured |
|---|---|---|
| structured array | **15.3 MB** | 1x |
| list of dicts | **183.5 MB** | **12x more** |

The structured array is **12x** smaller.
The arithmetic is exact for the array: 16 bytes per record (an 8-byte float plus an 8-byte int) times a million is ~15 MB, one contiguous block, zero per-record Python objects.
The list of dicts stores, *per record*, a dict object (a hash table with slots, keys, and load-factor slack) holding *boxed* Python objects (each `float` and `int` is a full heap object with a type pointer and refcount), plus the list's array of pointers, all told, over 180 bytes per record versus 16.

The memory gap is the headline, but the *access* gap compounds it.
A structured array's columns are ndarray views, so `sa["x"].sum()` is one C pass; the list of dicts needs a Python loop dereferencing a dict and unboxing a float per record.
So the structured array wins on both axes at once, an order of magnitude less memory *and* vectorized columns, which is why every serious tabular tool (pandas, Arrow, the recarray) is columnar and typed under the hood.
Use a structured array or a `DataFrame` for tabular numeric data; a list of dicts is fine only for small, irregular, or heavily-mutated records where the array's fixed schema is a poor fit.

---

## 104.4 Edges and failure modes

**Fixed-width strings truncate silently.**
A `U10` field holds *at most* 10 characters; assigning `"a-very-long-name"` stores only the first 10, no error.
Size string fields for the longest value, or use an `object` dtype field (which stores Python string references, giving up the contiguous-block benefit for that column).

**A record view (`a[0]`) is a `np.void` scalar, not a dict.**
Indexing a single record returns a `np.void` (a reference into the array's bytes), not a Python dict; you access its fields by name (`a[0]["age"]`) or position.
Iterating records in Python (`for rec in a`) is the row-by-row anti-pattern, operate on *columns* (`a["age"]`), not rows.

**Field access is a strided view, not contiguous.**
`a["x"]` for an interleaved structured array is a *strided* column (elements `itemsize` bytes apart), not a contiguous array.
Most operations handle strides fine, but the column is not C-contiguous, and code that assumes contiguity (some C extensions, `.tobytes()` expectations) may need `np.ascontiguousarray(a["x"])`, which copies.

**Alignment and padding.**
By default fields are packed tightly; `np.dtype(..., align=True)` pads fields to their natural alignment (like a C `struct`), changing `itemsize` and byte layout.
Matters when the array mirrors a C struct (Chapter 45) or a binary file format, match the alignment the format uses.

**`recarray` gives attribute access, at a cost.**
`a.view(np.recarray)` lets you write `a.age` instead of `a["age"]`, but attribute access adds overhead (an `__getattr__` lookup per access) and can shadow real ndarray attributes.
The dict-style `a["age"]` is the faster, less surprising default.

**This is not pandas.**
Structured arrays have no index, no label-based alignment, no missing-data handling, no group-by, no join.
For real tabular analysis, use pandas (built on this); structured arrays are the right tool for fixed-schema numeric records, binary-format I/O, and interop with C structs.

---

## 104.5 Connections

**Backward.**
Field access returning a view is Chapter 99 (views vs copies), strided this time.
Cross-field masking is Chapter 102 (boolean masking).
Column vectorization is Chapter 96.
The record layout, named typed fields packed into a fixed-width block, is the array-level form of Chapter 45's `struct` (binary layout) and mirrors a C `struct`, so a structured array can map a binary file's records directly (and a memmapped structured array, Chapter 103, reads on-disk records without loading).

**Forward.**
`recarray` (attribute access), `align=True` (C-struct layout), nested and sub-array fields, and the pandas `DataFrame` (the tabular tool built on typed columns) are Deep T and Deep U topics.
Apache Arrow's columnar format is the same idea at data-interchange scale.

**Across books.**
Typed columnar records are how **Book III** holds structured data efficiently, feature tables, labeled examples, batches of heterogeneous fields, without a Python object per row.
A **Book III** data pipeline stores millions of records as columns (a structured array, a `DataFrame`, or an Arrow table) and operates on them column-wise, so preprocessing a feature is one vectorized pass, not a per-row loop.
The §104.3 list-of-dicts trap is exactly the shape that makes naive data code bloated and slow, which **Deep T** replaces with columnar typed storage and **Deep U** enforces across data-processing pipelines.

---

## 104.6 Exercises

**1. Build a table.**
Reproduce §104.1: define a structured dtype with a string, an int, and a float field; fill three records; access a record (`a[0]`) and a column (`a["age"]`); reduce a column (`.mean()`, `.max()`).
Explain record vs field access.

**2. Query it.**
Select the records where one field passes a threshold and read another field from them (`a[a["age"] > k]["name"]`).
Explain how the mask on one field selects whole records across all fields, and connect it to SQL `SELECT ... WHERE`.

**3. Measure the memory.**
Run §104.3's benchmark.
Confirm the structured array is ~12x smaller than the list of dicts.
Compute the structured array's expected size from its `itemsize` and `N`, and explain where the list of dicts' extra bytes go.

**4. The truncation trap.**
Assign a string longer than a `U`-field's width and observe the silent truncation.
Then try an `object` dtype field and note what you gave up.
Explain the fixed-width string trade-off.

**5. The design question.**
NumPy stores tabular data as typed columns in one contiguous block (a structured array), not as a list of dicts.
Argue why, using the §104.3 memory measurement and the column-view vectorization of §104.2, and connect it to why pandas/Arrow are columnar.

---

## 104.7 Summary and cross-references

- A **structured dtype** is named fields of different types; a **structured array** packs N such records into one contiguous typed block (columnar, like a table).
- **Field access (`a["age"]`) returns a view** of that column, an ndarray you vectorize (`.mean()`), no loop; **`a[0]`** is a whole record (`np.void`).
- **Masks span fields:** `a[a["age"] > 26]["name"]` filters on one field and projects another, a SQL-style query in C.
- **Measured:** a million two-field records take **15.3 MB** as a structured array versus **183.5 MB** as a list of dicts, **12x** less, and columns vectorize where the list needs a loop.
- **Edges:** fixed-width strings truncate silently; columns are strided (not contiguous); `align=True` for C-struct layout; `recarray` adds attribute access at a cost; this is not pandas (no index/join/missing-data), which is *built on* it.

**Cross-references.** Views/strides → Chapter 99; boolean masking → Chapter 102; binary/struct layout → Chapters 45, 98; on-disk records → Chapter 103; vectorization → Chapter 96. `recarray`, nested fields, and the `DataFrame` → the rest of Deep T and Deep U.
