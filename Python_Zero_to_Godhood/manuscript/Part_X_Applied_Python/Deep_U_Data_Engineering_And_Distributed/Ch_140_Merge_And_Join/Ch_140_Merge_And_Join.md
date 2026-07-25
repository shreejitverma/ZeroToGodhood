# Chapter 59: Merge and Join

Real data lives in *many* tables, and the work of data engineering is combining them: orders with the reference data that describes each symbol, events with the users who caused them, measurements with the metadata that labels them.
The operation is the relational **join**, and in pandas it is **`merge`**: match rows of two DataFrames on a **key** and combine their columns.
This is the third core pandas skill, after column operations (Chapter 57) and `groupby` (Chapter 58), and it completes the vocabulary that covers most data transformations.

`merge` has two dimensions to get right.
The **join type** (`how`): `inner` keeps only keys in both frames, `left` keeps all left rows (filling `NaN` where the right has no match), `outer` keeps all keys from either side.
And the **cardinality**, which is where the danger lives: if a key appears *m* times on the left and *n* times on the right, the merge produces *m x n* rows for that key.
The measurement makes this vivid: merging two 2,000-row frames that share one repeated key produces **4,000,000** rows, a **1,000x** blow-up from 4,000 input rows.
This **row explosion** from unintended duplicate keys is the single most common merge bug, a silent, wrong, *huge* result, and the chapter's central caution is how to prevent it with `validate=`.

**This is Deep U's join chapter.**
It completes the core trio (columns, groupby, merge) that expresses most data work, builds on the relational model (SQL joins are the same operation), and is essential to **Book III**'s pipelines, which constantly combine tables.

## Section index

- **59.1** Join types, and the row-explosion trap
- **59.2** Getting merges right: cardinality and keys
- **59.3** Measurement: the row explosion
- **59.4** Edges and failure modes
- **59.5** Connections
- **59.6** Exercises
- **59.7** Summary and cross-references

Listings live under `code/ch140/` and are re-executed by `make verify` on both verification interpreters.

---

## 59.1 Join types, and the row-explosion trap

```python
# code/ch140/l01_merge.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- inner merge (default): keep keys present in BOTH ---
  columns after merge : ['symbol', 'qty', 'sector']
  sectors aligned to each order : ['tech', 'fin', 'tech', 'energy']
--- left merge: keep all LEFT rows, NaN where no match ---
  all 4 left rows kept : True
  CCC has no match -> sector is NaN : True
--- outer merge with indicator: which side each key came from ---
  outer keeps all keys : 3 rows (a, b, c)
  match indicator values : ['both', 'left_only', 'right_only']
--- the TRAP: duplicate keys multiply rows (m x n) ---
  2 left x 3 right (same key) -> 6 rows   (2 * 3 = 6, exploded)
--- validate= catches unintended duplicate keys ---
  validate='one_to_one' raised MergeError (caught the duplicates)
--- the rule ---
  merge joins on a key; pick how= (inner/left/outer); beware DUPLICATE
  keys (m*n row explosion), use validate= to assert the expected cardinality
```

**`merge` matches on a key and combines columns.**
`orders.merge(ref, on="symbol")` aligns each order with the `ref` row of the same `symbol`, producing a frame with columns from both, and the `sector` is correctly attached to each order (including the two `AAA` orders, both getting `tech`). This is the relational join: bring the descriptive columns from `ref` alongside the transactional rows of `orders`.

**The join type (`how`) sets which rows survive:**

- **`inner`** (default): only keys present in *both* frames. A left row with no matching right key is dropped.
- **`left`**: all left rows kept; where the right has no match, its columns are `NaN` (the `CCC` order keeps its row, with `sector` `NaN`). This is the most common join for "enrich my rows with reference data, keeping all my rows even if some lack reference."
- **`outer`**: all keys from *either* side (the `a`/`b`/`c` example keeps all three). `right` is the mirror of `left`.

**`indicator=True`** adds a `_merge` column recording where each row matched (`both`, `left_only`, `right_only`), invaluable for debugging a join ("which rows failed to match?").

**The trap: duplicate keys multiply rows.**
This is the crucial, dangerous behaviour.
When the key `x` appears *twice* on the left and *three* times on the right, the merge emits *every pairing*, `2 x 3 = 6` rows.
This is correct relational semantics (a join *is* the cross-product of matching rows), but it is a **footgun** when you did not expect duplicates: a join column you *assumed* was unique but was not silently multiplies your data.
**`validate=`** is the defense: `validate="one_to_one"` (or `"one_to_many"`, `"many_to_one"`) asserts the expected cardinality and raises `MergeError` if the keys violate it, catching the explosion *before* it happens.

---

## 59.2 Getting merges right: cardinality and keys

A merge is easy to write and easy to get subtly, catastrophically wrong. The discipline is about *cardinality* and *keys*.

**Know your join's cardinality, and assert it.** §59.1, §59.3.
Every merge is one of:

- **one-to-one:** each key unique on both sides (e.g. joining two per-entity tables). Result has the same rows as the inputs.
- **one-to-many / many-to-one:** unique on one side, repeated on the other (e.g. orders many, reference one, the common enrichment join). Result has the "many" side's row count.
- **many-to-many:** repeated on both sides. Result *explodes* to the product per key, this is almost always a bug when unintended.

The rule: **know which case you are in, and pass `validate=` to make pandas enforce it.**
`orders.merge(ref, on="symbol", validate="many_to_one")` documents *and checks* that each order matches at most one reference row; if `ref` unexpectedly has a duplicate `symbol`, it raises instead of silently doubling every order. This single habit prevents the most damaging merge bug.

**Check your keys before merging.**

- **Uniqueness:** if you believe a key is unique, verify it (`df["k"].is_unique`) or let `validate=` check. An accidental duplicate is the explosion.
- **Missing matches:** an `inner` join *silently drops* rows that do not match. Use `how="left"` + `indicator=True` to *see* which rows failed to match rather than losing them silently.
- **Key dtype and content:** the keys must be the *same type and value* to match. A `"5"` (string) does not match a `5` (int); a trailing space or a case difference (`"AAA"` vs `"aaa "`) breaks the match. Normalize keys (strip, lowercase, cast) before merging, mismatched keys produce a *silent under-match*, the mirror of the explosion.

**Prefer explicit over implicit.**
Pass `on=` (or `left_on`/`right_on`) explicitly rather than relying on pandas inferring the join columns; specify `how=`; use `suffixes=` to disambiguate same-named non-key columns. An explicit merge is a readable, checkable statement of intent.

The overarching principle: **a merge is a claim about how two tables relate, so state the claim (`how`, `on`, `validate`) and let pandas check it.**
The failures, silent explosion (duplicate keys), silent under-match (mismatched keys), silent row loss (`inner` drops non-matches), are all *silent*, so the defense is to make your assumptions explicit and machine-checked.

---

## 59.3 Measurement: the row explosion

**Methodology.** `code/ch140/bench_merge_explosion.py`.
Merging a 2,000-row frame (one key value repeated 2,000 times) with another 2,000-row frame (same key), and counting the result.
CPython 3.13.5, pandas 2.2.3, Apple M3 Pro, macOS 27.0, arm64.

| merge on one shared, repeated key | value |
|---|---|
| input rows (left + right) | 4,000 |
| merged output rows | **4,000,000** |
| blow-up factor | **1,000x the input** |
| `validate="one_to_one"` | raises `MergeError` (caught first) |

Four thousand input rows become **four million** output rows, a **1,000x** explosion, because the shared key appears 2,000 times on each side and the merge emits every one of the `2000 x 2000` pairings.

This is the measurement that matters for merges, and it is a *correctness* measurement, not a speed one.
The row explosion is the **number-one merge bug**: a join column you assumed was unique but was not (a duplicate from a data-quality issue, a wrong grain, a fan-out you did not intend) silently multiplies your data.
The consequences cascade: memory blows up (four million rows from four thousand), every downstream aggregate is *wrong* (sums and counts inflated by the duplication), and there is *no error*, just a much larger, incorrect result that may not be noticed until the numbers are questioned.

The defense is the discipline of §59.2, made concrete: **`validate=` catches it first.**
`validate="one_to_one"` (or the appropriate cardinality) raises `MergeError` *before* building the explosion, because it checks the key uniqueness the merge assumes.
So the rule is unconditional: **when you merge on keys you believe are unique, pass `validate=`.**
It costs nothing, documents your assumption, and converts a silent, catastrophic, hard-to-diagnose row explosion into an immediate, loud, exactly-located error.
This is the same principle as the whole book's approach to correctness, make assumptions explicit and machine-checked, applied to the operation where an unstated assumption (key uniqueness) does the most damage.
`merge` completes Deep U's core trio (columns, groupby, merge), and its lesson is that the most important thing about a join is not its speed but its *cardinality*, which you must know and assert.

---

## 59.4 Edges and failure modes

**Duplicate keys explode rows.** §59.1, §59.3.
`m x n` rows per shared key. The number-one merge bug. Use `validate=` to assert the expected cardinality and catch it before it happens.

**`inner` joins silently drop non-matching rows.** §59.2.
Rows without a match in the other frame vanish. Use `how="left"` + `indicator=True` to see what failed to match rather than losing it silently.

**Mismatched key dtype/content silently under-matches.** §59.2.
`"5"` != `5`; whitespace and case break matches. Normalize keys (cast, strip, lowercase) before merging. A silent under-match is as dangerous as the explosion.

**Same-named non-key columns get suffixed.**
If both frames have a column `value` (not the key), the merge appends `_x`/`_y` suffixes. Use `suffixes=("_left", "_right")` for clarity, or rename before merging.

**Merging on the index versus columns.**
`merge(on="k")` joins on a column; `join` (or `merge(left_index=True, ...)`) joins on the index. Mixing them up is a common error; be explicit about whether the key is a column or the index.

**`merge` is not `concat`.**
`merge` combines *columns* by matching keys (a join); `pd.concat` stacks frames *vertically* (append rows) or *horizontally* (by index). Use `concat` to union rows, `merge` to join on a key.

**Large many-to-many merges exhaust memory.** §59.3.
The explosion is a memory bomb. For large data, verify cardinality first, and consider whether the join grain is correct (often an unintended many-to-many means the wrong key).

**Ordering is not guaranteed.**
merge does not promise to preserve row order (it depends on the join algorithm and version). Sort explicitly if you need a specific order.

---

## 59.5 Connections

**Backward.**
merge is the relational join, the same operation as SQL `JOIN`. It combines the columnar frames of Chapter 57. `NaN` for non-matches (left/outer joins) is the missing-data handling of Chapter 57 / Chapter 98. The result is a frame that feeds further column operations and groupbys (Chapters 57-58).

**Forward.**
`concat` (stacking frames), `join` (index-based), `merge_asof` (nearest-key/time joins, essential for time series), and reshaping (`pivot`, `melt`) are the rest of **Deep U**. SQL joins (Deep U / databases) are the same semantics. Distributed joins (Dask, Spark) scale the operation, with the same explosion hazard.

**Across books.**
Joins are pervasive in **Book III**'s pipelines: enriching events with entity metadata, aligning features with labels, combining market data with reference data, are all merges, and the row-explosion bug is a real production hazard when a supposedly-unique key turns out not to be. The order-book system enriches its transactional data (orders, fills) with reference tables (instruments, venues) via `merge`, and it `validate=`s every such join (`many_to_one`, asserting the reference key is unique) so that a data-quality issue in the reference data raises immediately rather than silently doubling every trade and corrupting every P&L aggregate, the §59.3 discipline as a correctness safeguard on the data path. Deep U's core trio, columns, groupby, merge, is the grammar; asserting cardinality is the correctness.

---

## 59.6 Exercises

**1. The join types.** Reproduce §59.1: perform inner, left, and outer merges and confirm which rows each keeps. Use `indicator=True` to see match status. Explain when each `how` is right.

**2. Cause and catch the explosion.** Reproduce §59.3: merge on a duplicated key and confirm the row explosion. Then add `validate="one_to_one"` and confirm it raises first. Explain the `m x n` semantics and why `validate=` is the defense.

**3. Silent failures.** Construct (a) an inner join that silently drops rows and (b) a merge that under-matches due to a key dtype mismatch. Show how `indicator=True` and key normalization reveal/fix each. Explain why silent failures are the danger.

**4. Cardinality practice.** For three real join scenarios, identify the cardinality (one-to-one, one-to-many, many-to-one, many-to-many) and write the merge with the correct `validate=`. Explain how you determined the cardinality.

**5. The design question.** A merge's most important property is its cardinality, not its speed, and the failures are all silent (explosion, under-match, row loss). Argue why `validate=` should be a habit on every keyed merge, using §59.3, and how "make assumptions explicit and machine-checked" applies to joins specifically.

---

## 59.7 Summary and cross-references

- **`merge`** joins two DataFrames on a **key**, combining their columns, the relational join. **`how`** sets which rows survive: **`inner`** (keys in both), **`left`** (all left, `NaN` for non-matches), **`outer`** (all keys from either side). **`indicator=True`** records match status.
- **The row-explosion trap:** a key appearing *m* times left and *n* times right produces **`m x n`** rows. **Measured:** merging two 2,000-row frames on one shared repeated key produces **4,000,000** rows (a **1,000x** blow-up), silently. This is the number-one merge bug.
- **Know and assert cardinality:** every merge is one-to-one, one-to-many/many-to-one, or many-to-many. Pass **`validate=`** to check it and catch the explosion *before* it happens (`MergeError`).
- **The failures are all silent:** explosion (duplicate keys), under-match (mismatched key dtype/content), row loss (`inner` drops non-matches). The defense is explicit `how`/`on`/`validate` and key normalization.
- **Edges:** same-named non-key columns get suffixed; `merge` (join on key) is not `concat` (stack rows); index vs column keys; large many-to-many merges exhaust memory; order is not guaranteed.

**Cross-references.** Columnar frames → Chapter 57. groupby (the other core operation) → Chapter 58. Missing data (`NaN`) → Chapters 57, 98. `concat`, `join`, `merge_asof`, pivot/melt, SQL joins, distributed joins → the rest of Deep U. Book III pipelines → Deep U / Book III.
