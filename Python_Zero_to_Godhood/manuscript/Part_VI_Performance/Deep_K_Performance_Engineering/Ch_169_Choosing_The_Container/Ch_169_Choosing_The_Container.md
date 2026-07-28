# Chapter 88: Choosing the Container

Chapter 87 said to fix the exponent before the constant. In Python the exponent is almost always decided by **which container you reached for**, because the standard library already ships a data structure with the right exponent for every common access pattern.

That makes the most consequential performance decision in a Python program a one-line one. `x in some_list` inside a loop is quadratic; `x in some_set` is linear, and the edit is four characters. Measured at ten thousand items, the difference between those two lines is a factor of **5,373**.

The cost model is small enough to hold in your head, and it is checkable rather than memorised: a `bisect` on a sorted list takes exactly **10 comparisons at 1,024 elements and 11 at 2,048**, which is what a logarithm looks like when you can count it.

**This is a Deep K chapter.**
Deep Q owns what these containers are made of; this chapter owns the choice between them, under a cost model, with the gaps measured.

## Section index

- **88.1** The cost model, counted
- **88.2** Two questions that pick the container
- **88.3** Measurement: what the choice is worth
- **88.4** Edges and failure modes
- **88.5** Connections
- **88.6** Exercises
- **88.7** Summary and cross-references

Listings live under `code/ch169/` and are re-executed by `make verify` on both verification interpreters.

---

## 88.1 The cost model, counted

```python
# code/ch169/l01_container_cost_model.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- primitive operations for one lookup, at n=1024 and n=2048 ---
  operation                    n=1024   n=2048  growth
  --------------------------------------------------------
  dict[key]                         2        2  constant
  x in set                          2        2  constant
  bisect on a sorted list          10       11  logarithmic
  list.index(x)                 1,024    2,048  linear
  n heappush + one heappop      1,944    3,755  n log n
--- the logarithmic row, spelled out ---
  bisect at n=1024 takes 10 comparisons, and log2(1024) = 10
  at n=2048 it takes 11, and log2(2048) = 11
  doubling the data costs exactly one more comparison
--- the decision, as a table of access patterns ---
  membership, by key            -> set / dict          constant
  ordered scan, append at end   -> list                amortised constant
  append or pop at BOTH ends    -> collections.deque   constant
  smallest item, repeatedly     -> heapq               log n per operation
  nearest item in sorted order  -> bisect on a list    log n
  counting occurrences          -> collections.Counter constant per item
  fixed-width numbers, compact  -> array.array         constant, no boxing
```

**The counts are exact, so the model is not a claim.**
A `dict` lookup costs **2** primitive operations at either size: one `__hash__` to find the bucket and one `__eq__` to confirm the key. A `list.index` costs exactly `n`. The set and dict rows do not move when the data doubles, and the list row doubles precisely.

**The logarithmic row is the one worth staring at.**
Ten comparisons to find an item among a thousand; eleven among two thousand. Doubling the data costs one more comparison. That is the property that makes `bisect`, and every other tree-shaped structure, useful: the cost grows so slowly that for any realistic `n` it is effectively a small constant, without needing the memory a hash table spends.

**And the `heapq` row shows what "maintaining an invariant" costs.**
Building a heap of `n` items by repeated `heappush` costs about `1,944` comparisons at `n = 1,024`, roughly `2n`, because each push sifts up through only the levels it needs. A full sort of the same data (Chapter 87) costs about `n log n`. A heap is cheaper than a sort because it maintains **less order**: only enough to know the minimum.

---

## 88.2 Two questions that pick the container

The whole decision reduces to two questions, asked in this order.

**1. What do you do to it most often? That operation must be cheap.**
**2. What do you do to it rarely? That operation may be linear.**

Everything else follows.

| access pattern | container | the operation that is cheap |
|---|---|---|
| "is this in there?" | `set`, `dict` | membership, constant |
| "give me the value for this key" | `dict` | lookup, constant |
| "iterate in order, append at the end" | `list` | iteration and `append`, amortised constant |
| "add and remove at **both** ends" | `collections.deque` | both ends, constant |
| "give me the smallest, repeatedly" | `heapq` on a list | push and pop-min, log n |
| "what is nearest to this value?" | `bisect` on a sorted list | search, log n, and order is preserved |
| "how many of each?" | `collections.Counter` | increment, constant |
| "a million numbers, compactly" | `array.array`, `memoryview` | element access, constant, no boxing |
| "the last N things" | `deque(maxlen=N)` | append with automatic eviction |

**The failure is nearly always the first row done with a list.**
A list is an array. Membership is a scan. Written inside a loop over the same data, that is Chapter 87's canonical accidental quadratic, and it is the most common real performance bug in Python code, ahead of every interpreter-level concern this book has measured.

**The conversion is not free, and it is almost always worth it.**
Building a set from a list is one linear pass. If you look something up exactly once, the set costs more than it saves. If you look up twice, it has already paid for itself at any interesting size. The rule of thumb is: if the container is consulted more than a couple of times, convert.

**`bisect` occupies a real and narrow niche.**
It is slower than a set for pure membership (§88.3 measures 15x) and it is the only one of the two that can answer "what is the nearest value", "what is the next one after this", or "how many are below this threshold". Reach for it when you need **order and search**, not when you need membership.

**And the pattern that is not about speed at all.**
`deque(maxlen=N)` gives a bounded buffer with eviction for free. `Counter` gives counting with `most_common`. `defaultdict` removes a branch. These are chosen for correctness and clarity, and the fact that they also have the right exponent is what makes the standard library's collections worth learning as a set rather than one at a time.

---

## 88.3 Measurement: what the choice is worth

**Methodology.** `code/ch169/bench_containers.py`.
Three access patterns at one size, so the gaps are comparable. `min` of 15 batches (fewer for the slow rows).
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**Membership, against 10,000 items.**

| one membership test | time | vs `set` |
|---|---|---|
| `x in set` | 6.1 ns | 1.00x |
| `x in dict` | 6.2 ns | 1.03x |
| `bisect` on a sorted list | 92.6 ns | **15.3x** |
| `x in list` | 32,530 ns | **5,373x** |

Five thousand times. Not five percent, not five times. And the fix is to write `set(...)` once. This is the single highest-leverage line-level change available in Python, and it is available because a list scan and a hash lookup are different exponents, not different constants.

`bisect`'s 15x over a set is worth understanding rather than avoiding: it performs about 14 comparisons plus a Python-level function call, against the set's one hash and one equality check in C. It is not slow; it is doing a different, more capable job.

**Work at the front of a sequence.**

| 5,000 pushes then 5,000 pops at the front | time | vs `deque` |
|---|---|---|
| `deque.appendleft` / `popleft` | 117 us | 1.00x |
| `list.insert(0, ...)` / `pop(0)` | 4,876 us | **41.8x** |

A list is an array, so inserting at the front moves every element; a deque is a doubly-linked list of blocks and does not. Neither container is "faster": they have different exponents for *this* operation and the same exponent for iteration. Choosing between them is choosing which operation you intend to do often.

**Taking the smallest item, repeatedly.**

| take the 1,000 smallest of 10,000, one at a time | time | vs `heapq` |
|---|---|---|
| `heapq.heapify` then `heappop` | 276 us | 1.00x |
| sort, then `pop(0)`, each time | 20,931 us | **75.8x** |
| `min()` then `remove()`, each time | 70,544 us | **255.6x** |

This table is about **maintaining an invariant you do not need**. Re-sorting maintains total order when only the minimum was required; `min()` plus `remove()` maintains no order and pays two linear scans per extraction. The heap maintains exactly enough order to answer one question cheaply, which is why it is the right answer to a priority queue and the wrong answer to "give me these in order" (for that, sort once).

**The honest framing of all three tables.**
None of these gaps is a constant-factor optimisation, and none of them is available by writing cleverer code. They are all the same move: state the access pattern, then use the container the standard library already built for it.
**Book I**'s side of the shared order-book system makes the same choice with different names, `std::unordered_map` for price-level lookup, `std::deque` for the event queue, a heap for expiry, and its reasoning is this table. That the two languages agree on the data structures and disagree only on the constants is the clearest illustration in this series that the exponent is the portable part of a design.

---

## 88.4 Edges and failure modes

**Set and dict membership requires hashability, and the hash must be cheap.** §88.3's 6 ns assumes an `int`. A key whose `__hash__` walks a large structure moves the cost into the hash, and a class with `__eq__` but no `__hash__` is unhashable entirely.

**Hash collisions degrade to linear.**
Adversarial keys, or a `__hash__` that returns a constant, turn every lookup into a scan. String hashing is randomised per process by default (`PYTHONHASHSEED`) precisely to make the adversarial case hard to arrange remotely.

**Building the container is a linear pass you must account for.** §88.2.
Converting a list to a set inside a loop is a quadratic algorithm wearing a constant-time lookup. Build it once, outside.

**`in` on a `dict` tests keys, and on a `list` of tuples tests whole tuples.**
`(a, b) in list_of_pairs` is a linear scan comparing tuples. `b in dict_of_a_to_b` is a linear scan over values, not a lookup, because `in` on a dict tests keys. `value in d.values()` is O(n) and looks like it should not be.

**`deque` indexing is O(n) in the middle.**
`dq[0]` and `dq[-1]` are constant; `dq[n // 2]` walks the blocks. A deque is for the ends. If you need arbitrary indexing *and* cheap front operations, you need a different structure or a different algorithm.

**`heapq` gives you the minimum only.**
There is no cheap maximum, no cheap search, no cheap delete of an arbitrary element, and no stability. For a max-heap, negate the keys; for delete-arbitrary, use the standard "mark as removed and skip on pop" idiom.

**A sorted list must stay sorted.**
`bisect.insort` keeps it sorted at O(n) per insertion because of the shift, even though it *finds* the position in O(log n). For many insertions interleaved with many searches, that is quadratic, and the answer is a different structure or a batch sort at the end.

**`array.array` and `memoryview` trade generality for density.**
They hold one machine type, cannot hold `None`, and their elements are boxed into Python objects on every read. They pay off when the data is large and mostly handed to something that consumes buffers (Chapter 79), not when it is walked element by element in Python.

---

## 88.5 Connections

**Backward.**
Measuring the exponent, and the accidental quadratics a wrong container produces, is Chapter 87. Finding which function to look at is Chapter 86. Honest measurement is Chapter 85. The per-element interpreter cost that all of these share is Chapter 78.

**Forward.**
Memory as its own cost model, where `array.array` and `__slots__` belong, is Chapter 89. Caching, which is a container decision by another name, is Chapter 90. Streaming, when the container should not exist at all, is Chapter 91. `list`, `dict`, `set`, `deque` and `heapq` internals, the resize policies and the probing strategy, are Deep Q.

**Across books.**
The data structures in the shared system were chosen once and implemented twice. **Book I** uses `std::unordered_map`, `std::deque` and a binary heap where Book II uses `dict`, `collections.deque` and `heapq`, and the reasoning is identical because the exponents are. The constants differ by an order of magnitude and do not change a single choice, which is the point of doing the analysis before choosing a language.

---

## 88.6 Exercises

**1. Count your own.** Reproduce §88.1. Then add `list.remove`, `dict.pop`, and `deque.rotate` to the table and predict each before measuring.

**2. Find the crossover.** For "look up `m` values in a collection of `n`", find the `m` at which building a set first pays for itself, at `n = 10,000`. Explain the shape of the answer.

**3. Convert a real quadratic.** Find a list membership test inside a loop in code you maintain. Measure before and after converting to a set, at your real `n`, and report the factor.

**4. Where `bisect` wins.** Write the three queries a `set` cannot answer and `bisect` can. Implement each and measure it against the naive list scan.

**5. Break a heap.** Implement "remove an arbitrary element from a priority queue" with `heapq` and explain why the obvious approach is O(n). Then implement the mark-as-removed idiom and say what it costs in memory.

**6. The design question.** Python's `list` is an array and its `dict` is a hash table, and neither can be swapped for a different implementation by the user. Argue why the standard library ships `deque`, `heapq`, and `bisect` as separate tools rather than making `list` adaptive: what an adaptive list would cost every existing program, what it would do to the C-API's contiguity guarantee (Chapters 79 and 82), and how the current design pushes the choice, and the understanding, onto the programmer deliberately.

---

## 88.7 Summary and cross-references

- **The container decides the exponent**, and the standard library already ships one with the right exponent for every common access pattern. The most consequential performance decision in a Python program is usually a one-line one.
- **Counted, not asserted:** a `dict` lookup costs **2** primitive operations at 1,024 and at 2,048 elements; `list.index` costs exactly `n`; `bisect` costs **10 comparisons at 1,024 and 11 at 2,048**, so doubling the data costs one more comparison.
- **Two questions pick the container:** what do you do most often (that must be cheap), and what do you do rarely (that may be linear).
- **Measured at 10,000 items:** `x in set` 6.1 ns, `x in dict` 6.2 ns, `bisect` 92.6 ns (**15.3x**), `x in list` 32,530 ns (**5,373x**). The fix for the last row is writing `set(...)` once.
- **Front operations:** `deque.appendleft`/`popleft` 117 us against `list.insert(0)`/`pop(0)` 4,876 us (**41.8x**). A list is an array; a deque is blocks.
- **Maintaining an invariant you do not need is expensive:** taking the 1,000 smallest of 10,000 costs 276 us with `heapq`, 20,931 us re-sorting (**75.8x**), and 70,544 us with `min()` plus `remove()` (**255.6x**).
- **`bisect` is not a slower set**; it is the tool for nearest-match, range, and successor queries that a set cannot answer at all.
- **Edges:** keys must be hashable and cheaply so; collisions degrade to linear; building the container is a linear pass to account for; `value in d.values()` is O(n); `deque` indexing in the middle is O(n); `heapq` gives only the minimum; `bisect.insort` is O(n) per insertion; `array.array` trades generality for density and boxes on every read.

**Cross-references.** Measuring the exponent → Chapter 87. Finding the hot path → Chapter 86. Honest measurement → Chapter 85. Per-element interpreter cost → Chapter 78. Memory as a cost model → Chapter 89. Caching → Chapter 90. Streaming → Chapter 91. Container internals → Deep Q. Buffers and `memoryview` → Chapter 79.
