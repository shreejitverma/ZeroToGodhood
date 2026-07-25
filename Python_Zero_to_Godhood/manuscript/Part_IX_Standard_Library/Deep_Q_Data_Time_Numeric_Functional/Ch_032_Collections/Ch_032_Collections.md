# Chapter 32: The `collections` Module

A developer builds a task queue with a list: `tasks.append(job)` to enqueue, `tasks.pop(0)` to dequeue
the oldest. It works perfectly in testing with a handful of tasks. In production, with a queue that
grows to tens of thousands, the service slows to a crawl, and profiling points at `pop(0)`. The reason
is not a bug; it is a data-structure mismatch. A list stores its elements in a contiguous array, so
removing the front element shifts every other element down by one: `pop(0)` is O(n), and doing it on a
growing queue is O(n²) overall. Measured, `pop(0)`/`insert(0)` on a 4000-element list is **88 times
slower** than the same operation on a `deque`, which does it in O(1).

That mismatch is what the `collections` module exists to fix. The builtin `list` and `dict` are
general-purpose and excellent at what they do, but some jobs, a double-ended queue, a tally, a grouped
accumulation, a layered lookup, have a container whose operations are asymptotically better or simply
less error-prone. This chapter covers the specialized containers, `deque`, `defaultdict`, `Counter`,
`ChainMap`, and `namedtuple`, and it is part of **Deep Q**, the data-structures volume. Chapter 8
introduced `OrderedDict` and `Counter` historically; this chapter is the working reference for choosing
the right container.

## Section index

- **32.1** The problem: the wrong container has the wrong complexity
- **32.2** `deque`: O(1) at both ends
- **32.3** `defaultdict`, `Counter`, `ChainMap`, `namedtuple`
- **32.4** Measurement: O(1) versus O(n) at the front
- **32.5** Edges and failure modes
- **32.6** Connections
- **32.7** Exercises
- **32.8** Summary and cross-references

Listings live under `code/ch032/` and are re-executed by `make verify` on both interpreters.

---

## 32.1 The problem: the wrong container has the wrong complexity

A `list` is a dynamic array: contiguous memory, O(1) indexing, O(1) append and pop at the *right* end
(amortized), but O(n) insertion and removal at the *left* or middle, because everything after the
insertion point shifts. A `dict` is a hash table: O(1) average lookup, insertion, and deletion, but no
built-in tally or default-on-miss. These are the right choices for most code, and reaching for a
specialized container when a list or dict suffices is over-engineering.

But when a job's core operation is one the builtin does poorly, front-end queue operations, counting,
grouping, the general-purpose container turns an O(1) operation into an O(n) one, and at scale that is
the difference between a service that keeps up and one that falls over. The `collections` module
provides the container whose complexity matches the job.

---

## 32.2 `deque`: O(1) at both ends

A `deque` (double-ended queue) is a doubly-linked list of fixed-size blocks. Because it is not a single
contiguous array, inserting or removing at *either* end touches only the end block: O(1). It is the
correct queue, sliding window, and undo-stack container:

```python
# code/ch032/l01_collections.py (excerpt)
dq = deque([2, 3])
dq.appendleft(1)          # O(1); list.insert(0, ...) is O(n)
dq2 = deque(maxlen=3)     # a bounded ring buffer
```

Verified output (CPython 3.13.5):

```text
--- deque: O(1) at both ends (a list is O(n) at the left) ---
  deque after appendleft/append: [1, 2, 3, 4]
  deque(maxlen=3) keeps the last 3: [3, 4, 5]
```

`appendleft` and `append` are both O(1), and `popleft`/`pop` mirror them, so a `deque` is a proper
FIFO queue (`append`/`popleft`) or LIFO stack (`append`/`pop`). The `maxlen` parameter makes a bounded
ring buffer: appending past the limit drops the opposite end, exactly what a "last N events" sliding
window needs, with no manual trimming. The trade-off against a list: a `deque` has O(n) *indexing* in
the middle (it must walk the blocks), so use a list when you need random access and a deque when you
need fast ends.

---

## 32.3 `defaultdict`, `Counter`, `ChainMap`, `namedtuple`

The rest of the module removes boilerplate or adds ergonomics:

```text
--- defaultdict: a missing key auto-creates its default ---
  grouped: {'animal': ['cat', 'dog'], 'plant': ['rose']}
--- Counter: tallying and multiset arithmetic ---
  most_common(2): [('i', 4), ('s', 4)]
  addition     : {'a': 4, 'b': 3}
--- ChainMap: layered lookup without merging (first mapping wins) ---
  resolved color: red | size: M
--- namedtuple: a tuple with named fields, still a tuple ---
  p.x, p.y: 3 4 | is a tuple: True | unpacks: (3, 4)
```

**`defaultdict(factory)`** calls the factory to create a value on a missing key, so grouping is
`groups[kind].append(name)` with no `if kind not in groups: groups[kind] = []` guard, the single most
common dict-boilerplate elimination. **`Counter`** is a `dict` subclass for tallying, with
`most_common(n)` and multiset arithmetic (`+` sums counts), ideal for frequency analysis. **`ChainMap`**
layers several mappings into one view where lookup tries each in order (first wins), so
`ChainMap(overrides, defaults)` resolves configuration without *merging* the dicts, and updates go to
the first mapping, the standard layered-configuration and nested-scope pattern (Python's own name
resolution is conceptually a ChainMap of local, global, builtin). **`namedtuple`** builds a tuple
subclass with named fields: `p.x` and `p.y` work, yet `p` is still a real tuple (indexable, unpackable,
immutable), the lightweight record when a `dataclass` (Chapter 13) is more than you need.

---

## 32.4 Measurement: O(1) versus O(n) at the front

The chapter opened with the 88x figure; here is the measurement that produces it, and the scaling that
matters more than any single number.

**Methodology.** `code/ch032/bench_deque.py`. A left insert-and-remove (`appendleft`+`popleft` on a
deque, `insert(0)`+`pop(0)` on a list) at three sizes. Timed directly in ns/op; CPython 3.13.5, Apple
M3 Pro, macOS 27.0, arm64.

| n | deque (ns) | list (ns) | ratio |
|---|---|---|---|
| 100 | 20 | 66 | 3x |
| 1,000 | 19 | 435 | 23x |
| 4,000 | 19 | 1683 | 88x |

**The deque time is flat**, about 19 ns regardless of size, because `appendleft` touches only the front
block: O(1). **The list time grows with n**, from 66 ns to 1683 ns, because `insert(0)` shifts every
element: O(n). So the *ratio widens* as the container grows, 3x, 23x, 88x, which is the signature of an
O(n)-versus-O(1) difference. A single benchmark number ("deque is 88x faster") would hide the real
point; the *scaling* is what tells you the list will get worse without bound as the queue grows, which
is exactly the production failure in the chapter opening.

The lesson generalizes past `deque`: choosing a container is choosing a complexity class, and a mismatch
that is invisible at test scale becomes the dominant cost at production scale. Use a `deque` for anything
with front-end operations; reserve `list` for right-end operations and random access.

---

## 32.5 Edges and failure modes

**`list.pop(0)` in a queue.** §32.1. O(n) per call, O(n²) for the queue's lifetime. Use a `deque`. This
is the chapter-opening production bug.

**`deque` random access.** §32.2. Indexing the middle of a deque is O(n); it walks the blocks. Use a
list when you need `container[i]` for arbitrary `i`.

**`defaultdict` creating keys on read.** A `defaultdict` creates and stores a default on *any* missing-key
access, including a read, so `if d[k]:` inserts `k`. Use `d.get(k)` or `k in d` to check without
inserting.

**`Counter` of a huge iterable.** `Counter(large_iterable)` materializes counts for every distinct
element; for a stream with unbounded cardinality, that is unbounded memory. Bound the keys or use a
sketch.

**`namedtuple` versus `dataclass`.** A `namedtuple` is immutable and tuple-comparable; a `dataclass`
(Chapter 13) is mutable by default, supports methods and defaults more flexibly, and (with `slots=True`)
is comparable in footprint. Use `namedtuple` for a lightweight immutable record, `dataclass` when you
need more.

**`ChainMap` mutation.** Writes go to the *first* mapping only; the underlying dicts are not merged. Do
not expect `cm[k] = v` to update the layer where `k` currently resolves.

---

## 32.6 Connections

**Backward.** `OrderedDict` and `Counter` in their historical setting are Chapter 8. The `dict` insertion-
order guarantee that made `OrderedDict` mostly redundant is Chapter 12. `namedtuple` versus `dataclass`
is Chapter 13. `ChainMap`'s layered lookup mirrors the LEGB name resolution of Chapter 3.

**Forward.** `itertools` and `functools`, the functional side of Deep Q, are the next chapters. The
container internals, the array growth policy, the hash table, the deque block layout, are **Deep A** and
the rest of **Deep Q**. The collector's view of these containers is Chapter 30.

**Across books.** The right-container discipline is how Book II keeps its data-pipeline stages cheap at
the seams. A **Book III** retrieval pipeline's sliding-window deduplication uses a `deque(maxlen=N)`;
its token-frequency stage is a `Counter`; its layered configuration (defaults, environment, request) is
a `ChainMap`. Choosing the O(1) container at each stage is what keeps the pipeline's per-document cost
flat as the corpus grows, the same principle the §32.4 measurement demonstrates. **Deep U** owns the
pipeline seam.

---

## 32.7 Exercises

**1. Reproduce the production bug.** Build a queue with a list using `pop(0)` and one with a `deque`
using `popleft`, and measure both at growing sizes to the standard of §32.4. Confirm the list's cost
grows and the deque's is flat, and explain the O(n²) total for the list-based queue's lifetime.

**2. Build a sliding window.** Use `deque(maxlen=N)` to keep a running window of the last N values and
compute a moving average. Show that appending past N drops the oldest automatically, and explain why this
is O(1) per update where a list-based window would be O(N).

**3. Group without boilerplate.** Group a list of records by a key, first with a plain `dict` and an
`if key not in` guard, then with a `defaultdict`. Show they produce the same result, and explain the one
behavioral difference (defaultdict inserts on read).

**4. Layer a configuration.** Build a three-level `ChainMap` (defaults, file config, command-line
overrides) and show that a lookup resolves to the highest-priority layer that has the key. Then mutate
it and show the write goes only to the first layer. Explain when this is what you want.

**5. The design question.** `collections` provides specialized containers rather than making `list` and
`dict` handle every case. Argue why. Your answer must address the complexity trade-offs (a container fast
at both ends is slow at random access), the principle of using the container whose complexity matches the
job, and why a single "does everything" container cannot be optimal for all operations.

---

## 32.8 Summary and cross-references

- The builtin `list` (contiguous array) and `dict` (hash table) are general-purpose; `collections`
  provides containers whose complexity or ergonomics match specific jobs.
- **`deque`** is O(1) at *both* ends (a list is O(n) at the left), with a `maxlen` ring buffer; use it
  for queues and sliding windows. Its middle indexing is O(n).
- **`defaultdict`** auto-creates on a missing key (removing grouping boilerplate), **`Counter`** tallies
  with `most_common` and multiset arithmetic, **`ChainMap`** layers mappings for first-wins lookup
  without merging, **`namedtuple`** is a tuple with named fields.
- **Measured:** a left insert/remove on a 4000-element list is **88x** a deque's, and the ratio *widens*
  with size (O(n) vs O(1)); the scaling, not the single number, is the point.

**Cross-references.** `OrderedDict`/`Counter` history → Chapter 8. Dict ordering → Chapter 12.
`namedtuple` vs `dataclass` → Chapter 13. LEGB and ChainMap → Chapter 3. `itertools`/`functools` → the
next Deep Q chapters. Container internals → Deep A and Deep Q. The pipeline seam → Deep U.
