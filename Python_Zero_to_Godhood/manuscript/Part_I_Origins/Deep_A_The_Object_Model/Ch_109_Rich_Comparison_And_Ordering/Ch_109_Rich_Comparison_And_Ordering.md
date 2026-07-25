# Chapter 24: Rich Comparison and Ordering

Chapter 23 covered the two relations that make an object a *value*: equality and hashing.
This chapter covers the third: **order**.
Being able to write `a < b`, sort a list of your objects, or drop them into a heap depends on the four ordering methods, `__lt__`, `__le__`, `__gt__`, `__ge__`, and they behave less automatically than people expect.
Defining `__lt__` does *not* give you `__ge__`.
The four are independent, and getting all of them mutually consistent by hand is exactly the kind of tedious, error-prone work that produces a class where `a < b` and `b > a` quietly disagree.

Python's history here is worth one sentence, because it explains the shape of the protocol.
Python 2 had a single `__cmp__(self, other)` returning negative, zero, or positive, one method, total order for free, but no way to express a *partial* order or to compare only some pairs.
Python 3 replaced it with **rich comparison**: six separate methods, each returning a real answer or `NotImplemented`, which can express partial orders (a set's `<` is subset, and two sets can be incomparable) at the cost of making you define more.
`functools.total_ordering` buys back the convenience: write `__eq__` and *one* order method, and it synthesizes the other three.

**This is the canonical home for ordering.**
It builds on Chapter 20 (the `NotImplemented` fallback protocol, now applied to comparisons), Chapter 23 (equality, the sixth relation, and the reason `total_ordering` needs `__eq__`), and hands off sorting *algorithms* and `key=` functions to **Deep Q**.

## Section index

- **24.1** Six methods, the reflected fallback, and what sorting needs
- **24.2** `functools.total_ordering` and `NotImplemented`
- **24.3** Measurement: the cost of synthesized comparisons
- **24.4** Edges and failure modes
- **24.5** Connections
- **24.6** Exercises
- **24.7** Summary and cross-references

Listings live under `code/ch109/` and are re-executed by `make verify` on both verification interpreters.

---

## 24.1 Six methods, the reflected fallback, and what sorting needs

```python
# code/ch109/l01_reflected.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- sorting needs ONLY __lt__ ---
  sorted([Only(3), Only(1), Only(2)]) : [Only(1), Only(2), Only(3)]
  min : Only(1)   max : Only(3)
--- a > b falls back to the reflected b.__lt__ ---
    -> Traced.__lt__ was called
  b > a evaluates to : True   (via the reflected __lt__ above)
--- but __le__/__ge__ are NOT derived from __lt__ ---
  Only(1) >= Only(1) raises TypeError (>= undefined): True
--- the rule ---
  < and > reflect to one relation; equality is separate; but the four
  order methods are otherwise independent (see total_ordering next)
```

Three facts, in increasing order of surprise.

**Sorting needs only `__lt__`.**
`sorted`, `min`, `max`, `heapq`, and `list.sort` express every comparison they make as "is this less than that", so a class with just `__lt__` sorts correctly.
`Only` defines nothing else and sorts fine.
This is the one ordering method worth defining first, and often the only one a sortable-but-not-fully-comparable type needs.

**`<` and `>` are reflections of one relation.**
`b > a`, when `type(b)` has no usable `__gt__`, falls back to the *reflected* method `type(a).__lt__(a, b)`, the output shows `Traced.__lt__` firing for a `>` expression.
So `__lt__` alone makes both `a < b` and `b > a` work, because "b is greater than a" is definitionally "a is less than b".
This is the `NotImplemented` fallback of Chapter 20, specialised: each comparison operator has a reflected partner (`<`/`>`, `<=`/`>=`, `==`/`==`, `!=`/`!=`), and a missing operator tries its partner on the other operand.

**But the four order methods are otherwise independent.**
`Only(1) >= Only(1)` raises `TypeError`: `>=` reflects to `<=`, and `Only` defines *neither*, so there is no path to an answer.
Defining `__lt__` gives you `<` and `>` (reflections) but **not** `<=` or `>=`, which are a different relation (they include equality).
This is the trap that motivates the next section: to be *fully* ordered you need `__eq__` plus enough order methods to cover both `<`/`>` and `<=`/`>=`, and doing that by hand invites inconsistency.

---

## 24.2 `functools.total_ordering` and `NotImplemented`

```python
# code/ch109/l02_total_ordering.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- total_ordering gives all six from __eq__ + __lt__ ---
  x <  y : True      x <= y : True
  x >  y : False     x >= y : False
  x == y : False     x != y : True
  x <= x : True   (derived __le__ works on equal values)
--- which methods actually exist on the class now ---
  order methods in Version.__dict__ : ['__lt__', '__le__', '__gt__', '__ge__']
  (only __lt__ was written; the rest were synthesized)
--- NotImplemented => clean TypeError across unrelated types ---
  Version(1) < 5 raises TypeError : True
--- the rule ---
  write __eq__ + one order method + @total_ordering for all six;
  return NotImplemented (not raise) for types you do not handle
```

`Version` defines exactly two comparisons, `__eq__` and `__lt__`, and wears `@functools.total_ordering`.
The result is a fully ordered type: all six operators work, including `<=` on equal values (`x <= x` is `True`), which needs both the order relation *and* equality, which is why `total_ordering` requires `__eq__`.
The second block proves the synthesis literally: `Version.__dict__` now contains all four order methods, though the source wrote only `__lt__`.
The decorator inspected which order method you provided and generated the missing three by composing it with `__eq__`.

The third block is the discipline that makes comparisons *cooperative* rather than brittle.
Each of `Version`'s methods returns **`NotImplemented`** (not a guessed answer, not a raise) when the other operand is not a `Version`.
So `Version(1) < 5` does not silently return `True` or `False`; it returns `NotImplemented`, Python tries `int`'s reflected method, that also declines, and the result is a clean `TypeError`, the correct outcome for "these are not comparable".
Had `__lt__` returned `False` for a non-`Version`, `Version(1) < 5` would be `False` and `Version(1) >= 5` would be `True`, a nonsensical but silent answer.
The rule: **compare only the type you understand and return `NotImplemented` for everything else**, exactly as with arithmetic operators (Chapter 20).

The recipe for an orderable value type is now complete and short: define `__eq__`, define `__hash__` (Chapter 23), define one order method (`__lt__`), each returning `NotImplemented` for foreign types, and apply `@total_ordering`.

---

## 24.3 Measurement: the cost of synthesized comparisons

`total_ordering`'s convenience is not free, and the Python docs say so without a number. Here is the number.

**Methodology.** `code/ch109/bench_ordering.py`.
Two classes with identical semantics: `Auto` uses `@total_ordering` (writes `__eq__` + `__lt__`, synthesizes `__ge__`); `Manual` hand-writes all four order methods.
`a >= b` timed, `min` of 5 runs, 5,000,000 calls.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| `a >= b` | ns/call | vs hand-written |
|---|---|---|
| hand-written `__ge__` (direct) | 42.6 | 1.0x |
| `total_ordering` `__ge__` (synthesized) | 82.1 | **1.9x** |

The synthesized `__ge__` costs **1.9x** the hand-written one (1.7x on 3.14.6).
The reason is structural: `total_ordering` cannot know your comparison in closed form, so it builds `__ge__` by *composing* the methods you gave it, roughly "`a >= b` is `not (a < b)`", which runs an extra Python-level call and a negation on every comparison, where the hand-written `__ge__` does the single `self.v >= o.v` directly.

The right reading is *not* "avoid `total_ordering`".
For the overwhelming majority of types, comparisons are not a hot path, and the trade, five methods reduced to two, with no chance of the pairs disagreeing, is strongly worth ~40 ns.
The measurement tells you precisely *when* to spend the extra code: hand-write all six order methods only on a type whose comparisons are genuinely on a measured hot path (a sort key evaluated millions of times, a heap in an inner loop).
Everywhere else, `@total_ordering` is the correct default, fewer methods, guaranteed-consistent, and the speed difference is invisible.
This is the same shape as the rest of Deep A: the ergonomic default (`total_ordering`, like the instance `__dict__`, like the operator over the raw dunder) costs a little, and you buy the fast version back only where measurement says it matters.

---

## 24.4 Edges and failure modes

**Defining `__lt__` does not give you `__le__`/`__ge__`.** §24.1.
`<`/`>` reflect to each other and `<=`/`>=` reflect to each other, but the two pairs are independent. Use `@total_ordering` (or define all four) for full ordering.

**Return `NotImplemented`, not `False`, for foreign types.** §24.2.
Returning `False` from `__lt__` for an unknown type makes `x < y` and `x >= y` both meaningful-looking and both wrong. `NotImplemented` yields a correct `TypeError`.

**`total_ordering` is slower per comparison.** §24.3.
~1.9x here. Irrelevant off the hot path; hand-write the four order methods only where comparisons are measured-hot.

**Sorting a mixed-type list can raise mid-sort.**
`sorted([1, "a"])` raises `TypeError` because `int` and `str` are not comparable, and it can raise *after* partially sorting. Ensure homogeneous, comparable elements, or pass a `key=` that maps to a comparable type.

**Inconsistent comparisons corrupt sorts silently.**
If your `__lt__` is not a strict weak ordering (for example it is not transitive, or `a < b` and `b < a` are both true), `list.sort` does not detect it and produces a garbage order, no exception. The comparison must define a genuine order.

**`==` defaulting to identity interacts with ordering.**
`total_ordering` needs a real `__eq__`; if you forget it, `<=` and `>=` use identity equality and give wrong results for equal-but-distinct values. Define `__eq__` (and `__hash__`) alongside the order method.

**Float `nan` poisons ordering too.**
`nan < x`, `nan > x`, and `nan == x` are all `False`, so a `nan` in a list makes `sort` produce an order that depends on position, not value. Filter `nan`s before sorting.

**Comparison methods are looked up on the type.**
As with all special methods (Chapter 20), an instance-level `__lt__` is ignored by `<`. Define comparisons on the class.

---

## 24.5 Connections

**Backward.**
The reflected-method fallback in §24.1 and the `NotImplemented` discipline in §24.2 are Chapter 20's operator protocol applied to comparison operators. `total_ordering` requiring `__eq__`, and comparisons living beside equality and hashing, is Chapter 23; a fully specified value type defines `__eq__`, `__hash__`, and ordering together. The per-type method lookup is Chapter 20.

**Forward.**
The sorting algorithm (Timsort), `key=` functions and the decorate-sort-undecorate pattern, and `heapq`/`bisect` are **Deep Q**. `@dataclass(order=True)`, which generates all the comparison methods from field order, is an ergonomics topic (**Deep C**/dataclasses) and is the modern alternative to hand-writing `__lt__` + `total_ordering`.

**Across books.**
Ordering is how **Book I**'s domain types sort and prioritise: price levels order by price, orders by time-priority, events by timestamp, each defining `__lt__` (plus `total_ordering`) so the standard library's sorts and heaps work on them directly. The order-book system's matching engine keeps resting orders in price-time priority using exactly this, a heap keyed on comparable order objects, and the §24.4 "inconsistent comparison corrupts the sort silently" failure is one the system guards against because a mis-ordered book is a correctness bug, not a slow one. Where those comparisons are hot (the matching inner loop), it hand-writes the order methods, the §24.3 trade made deliberately.

---

## 24.6 Exercises

**1. Sort with one method.** Define a class with only `__lt__` and confirm `sorted`, `min`, and `max` work. Then try `>=` and observe the `TypeError`. Explain which reflections `__lt__` provides and which it does not.

**2. Watch the reflection.** Reproduce §24.1's `Traced`: define only `__lt__` with a print, then evaluate `b > a` and confirm `__lt__` fires. Explain, using Chapter 20, why `>` reaches `__lt__`.

**3. Complete a value type.** Take a `Money` class with `__eq__` and `__hash__` from Chapter 23 and make it fully ordered with `@total_ordering` and one order method, each returning `NotImplemented` for non-`Money`. Verify all six operators and that `Money(1) < 5` raises cleanly.

**4. Measure the trade.** Reproduce §24.3 for your `Money` type, comparing `@total_ordering` against a hand-written full set. Report the ratio. Then argue, for a specific use (a sort of a million rows versus an occasional `if a < b`), which you would choose and why.

**5. The design question.** Python 3 replaced Python 2's single `__cmp__` with six rich-comparison methods. Argue what that bought (name a type that is comparable only partially, where `<` can return "incomparable") and what it cost (the §24.1 independence, the §24.3 need for `total_ordering`). Would a `__cmp__`-style single method have been the better default for the 90% case? Defend your answer.

---

## 24.7 Summary and cross-references

- Ordering is **four independent methods** (`__lt__`, `__le__`, `__gt__`, `__ge__`) plus equality. `<`/`>` and `<=`/`>=` are **reflected pairs** (a missing operator tries its partner on the other operand), but the two pairs are otherwise independent, `__lt__` alone does not give you `__ge__`.
- **Sorting, `min`, `max`, and `heapq` need only `__lt__`.**
- **`functools.total_ordering`** synthesizes the three missing order methods from `__eq__` plus one order method, write two, get six, guaranteed consistent.
- **Return `NotImplemented` (not `False`) for foreign types**, so incomparable pairs raise `TypeError` instead of returning a silent wrong answer.
- **Measured:** a `total_ordering`-synthesized `__ge__` costs **1.9x** a hand-written one (82.1 vs 42.6 ns), because it composes your methods with an extra call. Use `total_ordering` by default; hand-write all six only where comparisons are measured-hot.

**Cross-references.** The `NotImplemented` reflected-operator protocol → Chapter 20. Equality and hashing (the rest of a value type) → Chapter 23. Timsort, `key=`, `heapq`, `bisect` → Deep Q. `@dataclass(order=True)` → Deep C.
