# Chapter 72: Generator Expressions and Short-Circuiting

`any(x == 5 for x in data)` and `any([x == 5 for x in data])` differ by two brackets and return the same
answer, but on a million-element `data` where the match is near the front, the first takes **170 nanoseconds**
and the second takes **12 milliseconds**, a **68,000x** difference. The bracketed version is a *list
comprehension*: it builds the entire million-element list of booleans *before* `any` even runs, then `any`
checks them. The bracketless version is a *generator expression*: `any` pulls values from it one at a time and
**stops at the first `True`**, the sixth item. The brackets look harmless, they even look tidier, but they force
full materialization and defeat short-circuiting. This is one of the most common and most invisible performance
bugs in Python.

This chapter continues **Deep F** with generator expressions: how a genexp differs from a list comprehension
(lazy versus eager), why the difference is enormous inside short-circuiting consumers like `any`/`all`/`next`,
and when each is right. It is the expression-level counterpart to Chapter 69's iterator protocol and Chapter 9's
laziness.

## Section index

- **72.1** Lazy genexp vs eager listcomp
- **72.2** Short-circuiting and the bracket trap
- **72.3** Measurement: `any` with and without brackets
- **72.4** Edges and failure modes
- **72.5** Connections
- **72.6** Exercises
- **72.7** Summary and cross-references

Listings live under `code/ch072/` and are re-executed by `make verify` on both interpreters.

---

## 72.1 Lazy genexp vs eager listcomp

```python
# code/ch072/l01_genexp.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- any() over a generator expression: short-circuits ---
  result: True, items examined: 6 (stopped at x==5)
--- any() over a list comprehension: examines everything first ---
  result: True, items examined: 1,000,000 (built the full list)
--- next() on a genexp takes just the first matching value ---
  first even > 10 : 12
--- a genexp is a one-shot iterator; a listcomp is a reusable list ---
  genexp first pass : [0, 1, 4]
  genexp again      : []  (exhausted)
  listcomp reusable : [0, 1, 4] [0, 1, 4]
```

A **generator expression** `(f(x) for x in data)` is a lazy iterator: it produces values on demand and holds
one at a time. A **list comprehension** `[f(x) for x in data]` builds the whole list eagerly. The counter makes
the consequence stark: `any` over the *genexp* examines **6** items (it stops the moment `check(x)` returns
`True` at `x == 5`), while `any` over the *listcomp* examines **1,000,000**, because the list is fully built
*before* `any` sees it. Same answer, six versus a million units of work.

The other two blocks round out the picture. `next(genexp)` pulls just the *first* value (the first even number
over 10 is 12), computing nothing beyond it, ideal for "find the first match." And a genexp is a **one-shot
iterator** (Chapter 69): the first `list(gen)` drains it, the second is empty; a listcomp is a reusable list you
can iterate repeatedly. So the two forms differ on three axes at once: *when* they compute (lazy vs eager),
*how much* memory they hold (one item vs all), and *how many times* you can iterate (once vs many).

---

## 72.2 Short-circuiting and the bracket trap

The dramatic case is a genexp inside a **short-circuiting consumer**, a function that may decide its answer
before consuming everything: `any` (stops at the first truthy), `all` (stops at the first falsy), `next` (takes
one), and to a degree `min`/`max`/`in`. Given a genexp, these consume only as far as they must. Given a *list
comprehension*, they cannot short-circuit at all, because the list is already fully built before the consumer
runs; the `[...]` did all the work up front.

This is the "bracket trap": `any([... for ...])` looks almost identical to `any(... for ...)`, and readers, even
experienced ones, often add the brackets out of habit or to "make it a proper collection." But the brackets turn
a lazy, short-circuiting, constant-memory operation into an eager, exhaustive, O(n)-memory one. When the match
is near the front (the common case for `any`/`next`, you are usually looking for *whether* or *the first*), the
cost difference is the full length of the input, §72.3's 68,000x.

The rule: **drop the brackets. Pass a generator expression, not a list comprehension, to `any`, `all`, `next`,
`min`, `max`, `sum`, `in`, and any consumer that streams or short-circuits.** The genexp is not just faster; it
is lazier (short-circuits), lighter (constant memory), and reads the same. Use a list comprehension only when
you genuinely need the *list*, to iterate it more than once, index it, take its length, or mutate it. If you
find yourself wrapping a comprehension in `[]` only to hand it to a function that consumes it once, remove the
brackets.

---

## 72.3 Measurement: `any` with and without brackets

**Methodology.** `code/ch072/bench_short_circuit.py`. `any` over a generator expression versus a list
comprehension, over a 1,000,000-element source whose match (`x == 5`) is near the front. `min` per call; ratio
relative to the genexp. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| `any` over 1,000,000 items | min per call | ratio |
|---|---|---|
| `any(genexp)` (short-circuits) | **170 ns** | 1.00x |
| `any([listcomp])` (builds all) | **11,688,163 ns** | **68,544x** |

The genexp form finishes in **170 ns**, examining six items before `any` short-circuits. The listcomp form takes
**11.7 ms**, **68,000x** longer, because it builds a million-element list first (allocating and computing every
element) and only then does `any` scan it, immediately finding the answer near the front. The entire 11.7 ms is
work the brackets forced and the answer did not need. The exact ratio depends on where the match is (a match at
the very end would make the two comparable), but for the typical "is there any / find the first" query, the
match is early and the genexp wins by the full length of the input.

The rule restated as a habit: **when a comprehension is an *argument* to a function, prefer the parenthesized
generator form.** `sum(x*x for x in data)`, `any(is_valid(r) for r in rows)`, `next(u for u in users if
u.active)`, none should have inner brackets. The brackets are correct only when you are *storing* a list you will
use as a list. This is the same laziness discipline as Chapter 9 and Chapter 33, at the expression level, and
the §72.3 measurement is why it matters: two characters decide between constant work and O(n) work.

---

## 72.4 Edges and failure modes

**Brackets inside a short-circuiting consumer.** §72.2. `any([...])`/`all([...])`/`next([...])` defeat short-
circuiting and materialize the whole list. Drop the brackets to a genexp.

**Reusing an exhausted genexp.** §72.1. A generator expression is one-shot; iterating it twice yields nothing the
second time (Chapter 69). If you need to iterate more than once, use a list comprehension (accept the memory) or
rebuild the genexp.

**Genexp needing a list's operations.** A genexp has no `len`, no indexing, no `in`-repeatedly. If you need those,
materialize with a list comprehension. Do not force a genexp where a list's capabilities are required.

**A genexp as the sole argument needs no extra parens.** `sum(x for x in data)` is valid, the call parentheses
serve as the genexp's. But `func(x for x in data, other)` is a syntax error; a genexp with siblings needs its own
parentheses: `func((x for x in data), other)`.

**Late binding in a genexp.** A genexp captures variables by reference and evaluates lazily, so a genexp built in
a loop over a changing variable sees the *final* value when consumed later (the classic closure-in-a-loop
surprise). Bind loop variables as default arguments or materialize eagerly if you need the value at build time.

**Genexp over a consumed iterator.** A genexp *reading* from a single-pass iterator shares that iterator's
exhaustion; building two genexps over the same iterator does not give two independent passes. Use `tee` (Chapter
33) or a list if you need multiple passes over the source.

---

## 72.5 Connections

**Backward.** The laziness and constant memory a genexp gives are Chapter 9; the single-pass iterator it *is* is
Chapter 69. List comprehensions and the comprehension syntax are Chapter 3. The `itertools` that composes lazy
streams is Chapter 33. The bytecode difference between a comprehension and a loop (and the specializing
interpreter) is Chapter 50.

**Forward.** Async comprehensions and `async for` (Chapters 10-11) extend genexps to async sources. The closure/
late-binding subtlety connects to Chapter 3's scoping. Streaming pipelines built from genexps are a **Deep U**
pattern.

**Across books.** Genexps are how Book II streams and short-circuits over large data for **Book III** without
materializing it. A **Book III** validation or filtering step over a large record stream uses `any`/`all`/`next`
with generator expressions, so it stops at the first decisive record and never builds a full intermediate list,
constant memory and early exit. The §72.3 bracket trap is exactly the kind of silent O(n) blowup that turns a
fast check into a bottleneck at corpus scale, which **Deep U** guards against at the streaming seam.

---

## 72.6 Exercises

**1. Prove the short-circuit.** Reproduce §72.1 with a counter: show `any(genexp)` examines a handful of items
and `any([listcomp])` examines all. Explain why the brackets prevent short-circuiting.

**2. Measure the trap.** Run §72.3's benchmark and confirm the bracketed form is orders of magnitude slower when
the match is near the front. Then move the match to the end and show the two converge. Explain the dependence on
match position.

**3. Find the first.** Use `next(genexp)` to find the first item matching a predicate without scanning the rest,
and show a list comprehension would scan everything. Explain when `next(genexp)` is the right tool.

**4. Choose the form.** For several tasks (check existence, build a reusable collection, sum a stream, index into
results), pick genexp or listcomp and justify each. Explain the three axes (lazy/eager, memory, reuse).

**5. The design question.** A genexp and a listcomp differ by two brackets but behave very differently inside a
consuming function. Argue why the language makes them so syntactically similar yet semantically distinct, and
what discipline avoids the trap. Your answer must use the §72.3 measurement and the short-circuiting behavior.

---

## 72.7 Summary and cross-references

- A **generator expression** `(f(x) for x in data)` is **lazy** (one item at a time, one-shot); a **list
  comprehension** `[f(x) for x in data]` is **eager** (builds the whole list, reusable).
- Inside a **short-circuiting consumer** (`any`, `all`, `next`, `in`, `min`/`max`), a genexp stops early; a
  listcomp builds everything first and cannot short-circuit, the **bracket trap**.
- **Measured:** `any(genexp)` is **68,000x** faster than `any([listcomp])` on a million items with an early match
  (170 ns vs 11.7 ms), because the brackets force full materialization. **Drop the brackets** when passing a
  comprehension to a consuming function.
- **Use a list comprehension only when you need the list** (reuse, indexing, `len`, mutation); otherwise pass a
  generator expression.

**Cross-references.** Laziness and memory → Chapter 9. Iterator protocol and single-pass → Chapter 69.
Comprehension syntax → Chapter 3. `itertools` → Chapter 33. Comprehension bytecode → Chapter 50. Async
comprehensions → Chapters 10-11. The streaming seam → Deep U.
