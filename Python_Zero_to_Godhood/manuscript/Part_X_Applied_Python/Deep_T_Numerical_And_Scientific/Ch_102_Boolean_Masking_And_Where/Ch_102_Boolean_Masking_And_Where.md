# Chapter 102: Boolean Masking and `np.where`

The reflex for "apply a rule to each element", clamp negatives to zero, keep values in a range, replace
outliers, is a Python loop with an `if`. In NumPy that reflex is the Chapter 96 anti-pattern, and the fix is
**boolean masking**. A comparison on an array produces a *boolean array*, and from that mask you get the whole
vocabulary of conditional logic *without a loop*: **select** matching elements (`arr[mask]`), **update** them in
place (`arr[mask] = value`), **branch** elementwise (`np.where(cond, x, y)`, "keep `x` where the condition holds,
else `y`"), and **aggregate** (`mask.sum()` counts, `mask.any()`, `mask.all()`). All run in C. Applying a ReLU
(keep positives, else 0) to a million values with `np.where` is **33x** faster than the equivalent Python
comprehension, and the gap only grows with more complex conditions.

This chapter continues **Deep T** with boolean masking and `np.where`: the mask vocabulary, the `&`/`|`/`~`
combinators (not `and`/`or`), and why vectorized conditionals replace element loops. It is how you express
"if-this-then-that" over an array at C speed.

## Section index

- **102.1** The mask vocabulary
- **102.2** Combining masks, and select vs update
- **102.3** Measurement: `np.where` vs a loop
- **102.4** Edges and failure modes
- **102.5** Connections
- **102.6** Exercises
- **102.7** Summary and cross-references

Listings live under `code/ch102/` and are re-executed by `make verify` on both interpreters (both with NumPy
2.1.3).

---

## 102.1 The mask vocabulary

```python
# code/ch102/l01_masking.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
  a : [-2, -1, 0, 1, 2, 3]
--- a comparison makes a boolean array ---
  a > 0 : [False, False, False, True, True, True]
--- SELECT with a mask (a copy of the matching elements) ---
  a[a > 0] : [1, 2, 3]   (the positives)
--- BRANCH elementwise with np.where(cond, x, y) ---
  np.where(a > 0, a, 0) : [0, 0, 0, 1, 2, 3]   (a ReLU: keep positives, else 0)
--- UPDATE in place with mask assignment (writes through) ---
  b[b < 0] = 0 -> [0, 0, 0, 1, 2, 3]
--- AGGREGATE a mask: count / any / all ---
  (a > 0).sum() (count) : 3
  (a < 0).any()         : True
  (a >= -2).all()       : True
--- combine masks with & | ~ (parenthesize each comparison) ---
  (a > -2) & (a < 2) selects : [-1, 0, 1]
--- the rule ---
  express conditional array logic with masks / np.where, not a loop
  arr[mask] selects (copy); arr[mask]=v updates in place; & | ~ combine
```

It starts with a **comparison**: `a > 0` produces a *boolean array* (one `bool` per element), the mask. From
there:

- **Select**: `a[a > 0]` returns the elements where the mask is `True` (a *copy*, Chapter 99), the positives.
- **Branch**: `np.where(a > 0, a, 0)` computes, elementwise, `a` where the condition holds and `0` where it does
  not, a vectorized `if`/`else` (here a ReLU). It picks between two arrays (or scalars, broadcast) per element.
- **Update in place**: `b[b < 0] = 0` assigns `0` to the elements where `b < 0`, clamping negatives *in place*
  (fancy *assignment* writes through, the Chapter 99 exception, even though `b[b < 0]` *reads* a copy).
- **Aggregate**: `(a > 0).sum()` *counts* the `True`s (booleans sum as 0/1), and `.any()`/`.all()` test existence
  and universality.

Every one of these is a whole-array operation running in C, no Python loop, no per-element branch.

---

## 102.2 Combining masks, and select vs update

The last block shows the critical syntax detail: **combine masks with `&` (and), `|` (or), `~` (not), not the
Python `and`/`or`/`not`**, and *parenthesize each comparison*. `(a > -2) & (a < 2)` is an elementwise AND of two
boolean arrays; `a > -2 and a < 2` raises `ValueError` (Python's `and` tries to take the *truth value of a whole
array*, which is ambiguous). The parentheses are required because `&` binds *tighter* than the comparison
operators, so `a > -2 & a < 2` parses wrongly. This trips up everyone once: **array boolean logic uses `& | ~`
with parentheses**, because `and`/`or` are Python scalar operators that cannot combine element-wise.

The select-vs-update distinction (Chapter 99) matters here: `arr[mask]` *reads* a copy, so `x = arr[mask]; x[0]
= 9` does *not* change `arr`. But `arr[mask] = value` *writes* through, modifying `arr` in place. So to *extract*
matching elements, `arr[mask]` gives an independent array; to *modify* them, assign to `arr[mask]`. And
`np.where(cond, x, y)` always produces a *new* array (it does not modify in place), use it when you want a
transformed *copy*, and mask assignment when you want an in-place update.

The rule: **express conditional array logic with masks and `np.where`, combining conditions with `& | ~`
(parenthesized), never with a Python loop or `and`/`or`.** The mask vocabulary covers essentially all
element-wise conditional needs, filter (select), clamp/replace (update or `np.where`), count/test (aggregate),
at C speed. Reaching for a `for` loop with an `if` to process array elements is the reduction-form of Chapter
96's anti-pattern; there is almost always a mask expression that does it in one C pass.

---

## 102.3 Measurement: `np.where` vs a loop

**Methodology.** `code/ch102/bench_masking.py`. A ReLU (keep positives, else 0) over 1,000,000 values via
`np.where(arr > 0, arr, 0)` versus a Python list comprehension with an `if`/`else`. `min` per run. CPython
3.13.5, Apple M3 Pro, macOS 27.0, arm64, NumPy 2.1.3.

| ReLU over 1,000,000 values | time | vs vectorized |
|---|---|---|
| `np.where(arr > 0, arr, 0)` | **603 us** | 1.0x |
| Python `if`/`else` comprehension | **20.1 ms** | **33x slower** |

`np.where` is **33x** faster. It evaluates the condition (`arr > 0`, one C pass producing a boolean array) and
selects between the two branches (another C pass) over the whole array in compiled code; the Python comprehension
branches *per element* in the interpreter, boxing each result. The comprehension is already the *fast* way to do
it in pure Python (faster than an explicit `for` loop), and it is still 33x slower than the vectorized form.

The rule: **vectorize conditionals with `np.where`/masks; do not loop.** The 33x here is for a *simple*
condition; a more complex per-element rule (multiple conditions, `np.select` for several branches, nested
`np.where`) widens the gap, because each additional Python-level operation per element compounds while the
vectorized version adds another C pass. And masking composes with everything else in Deep T, filter with a mask,
reduce the result (`arr[arr > 0].mean()`), normalize with broadcasting (Chapter 97), so a whole conditional-plus-
aggregate pipeline stays in C. As throughout Deep T, the idiomatic array expression (mask/`where`) is also the
fast one; a Python loop over elements to apply a condition is both slower and less readable.

---

## 102.4 Edges and failure modes

**`and`/`or` on arrays.** §102.2. `a > 0 and a < 2` raises `ValueError` (ambiguous array truth value). Use `&`/
`|`/`~` with each comparison parenthesized.

**Missing parentheses.** `a > -2 & a < 2` mis-parses (`&` binds tighter than comparison). Always parenthesize:
`(a > -2) & (a < 2)`.

**`arr[mask]` copy vs `arr[mask] = v` update.** §102.2. Reading a mask returns a copy (mutating it does not change
`arr`); assigning to a mask updates in place. Use the right one for select vs modify.

**`np.where` evaluates both branches.** `np.where(cond, f(arr), g(arr))` computes `f(arr)` *and* `g(arr)` for the
*whole* array, then selects, it does *not* skip the unused branch per element. If a branch is expensive or invalid
where the condition is false (e.g. `1/arr` where `arr` is 0), that is wasted work or a warning; mask-assign the
valid subset instead.

**Boolean array memory.** A mask is a full boolean array (1 byte per element in NumPy). For a billion-element
array that is a gigabyte of mask; chain conditions carefully, or use `np.count_nonzero`/`np.any` that do not
materialize intermediates where possible.

**Truthiness of a whole array.** `if arr:` on a multi-element array raises (ambiguous). Use `.any()`/`.all()`
(or `.size`) to get a scalar boolean from an array condition.

**`np.select` for many branches.** Nesting `np.where` for 3+ cases is unreadable; `np.select(condlist,
choicelist, default)` handles multiple conditions cleanly. Use it instead of deeply nested `where`.

---

## 102.5 Connections

**Backward.** Masks selecting a copy vs assignment writing through is Chapter 99 (views/copies). The comparison
producing a boolean array is vectorization (Chapter 96). Combining with reductions (`mask.sum()`) is Chapter 101.
The `and`/`or` truth-value error is Python's boolean protocol (Chapter 6).

**Forward.** `np.select` (multi-branch), `np.clip` (a common where-pattern), fancy integer indexing, and grouped/
conditional aggregation are Deep T. Masked arrays (`numpy.ma`) for missing data are a Deep T topic. pandas boolean
indexing builds on this.

**Across books.** Vectorized conditionals are how Book II applies rules to **Book III**'s data without loops. A
**Book III** pipeline filters tokens/documents with masks, clamps or normalizes activations with `np.where`/
`np.clip`, thresholds scores, and counts matches with `mask.sum()`, all in C, so a rule over a million records is
a handful of array passes. The §102.1 loop-with-`if` reflex is exactly the pattern that makes naive numeric code
slow, which **Deep T** replaces with masks, and **Deep U** enforces on data-processing hot paths.

---

## 102.6 Exercises

**1. The mask vocabulary.** Reproduce §102.1: select with a mask, branch with `np.where`, update in place with
mask assignment, and count/test with `.sum()`/`.any()`/`.all()`. Explain what each does.

**2. Combine conditions.** Select elements in a range with `(a > lo) & (a < hi)`, then try `and` and observe the
error. Explain why `&` and parentheses are required.

**3. Measure the speedup.** Run §102.3's benchmark and confirm `np.where` beats the comprehension. Then add a
second condition and show the gap widens. Explain the compounding.

**4. Both-branches trap.** Write `np.where(arr != 0, 1/arr, 0)` and observe the divide warning (both branches
computed). Fix it with mask assignment on the valid subset. Explain why `where` evaluates both branches.

**5. The design question.** NumPy expresses conditionals as masks/`np.where` over whole arrays rather than
per-element branches. Argue why, using the §102.3 measurement, and explain the `& | ~` combinator rule and the
select-vs-update distinction.

---

## 102.7 Summary and cross-references

- A **comparison makes a boolean mask**; from it: **select** `arr[mask]` (a copy), **update** `arr[mask] = value`
  (in place), **branch** `np.where(cond, x, y)` (elementwise if/else), **aggregate** `mask.sum()`/`any()`/`all()`.
  All run in C.
- **Combine masks with `& | ~` (parenthesized), not `and`/`or`** (which raise on arrays).
- **Measured:** a ReLU over a million values is **33x** faster with `np.where` than a Python comprehension (603 us
  vs 20.1 ms); the gap widens with more conditions.
- **Edges:** `arr[mask]` copies but `arr[mask]=v` writes through; `np.where` evaluates *both* branches (mask-assign
  for expensive/invalid branches); a whole-array `if` is ambiguous (use `.any()`/`.all()`); use `np.select` for
  many branches.

**Cross-references.** Views/copies and mask assignment → Chapter 99; vectorization → Chapter 96; mask reductions
→ Chapter 101; array truth value → Chapter 6. `np.select`/`np.clip`/masked arrays → the rest of Deep T. The
data-rule seam → Deep U.
