# Chapter 87: Complexity Beats Constants

Chapter 86 found the hot function. The first question to ask about it is not how to make it faster; it is **how its cost grows**.

A 30% constant-factor win is a good afternoon and it is permanent only until the input doubles. Turning an accidental O(n²) into O(n) is a different program: it wins by a factor of two at the next doubling, four at the one after, and it keeps winning. Deep H's entire volume, every technique in it, lives inside a factor of about three. This chapter's subject buys factors that have no ceiling.

The exponent is **measurable exactly**, with no timer and therefore no noise, by the doubling method: run the operation at `n` and at `2n`, count the primitive operations it performed, and take `log2` of the ratio. That figure *is* the exponent, because `cost(n) = c·n^k` implies `cost(2n)/cost(n) = 2^k` regardless of `c`. The constant cancels; the exponent survives.

And the same method works on a clock when the primitive is inside C and cannot be counted. Applied to the accidental quadratics Python code actually contains, it finds five of them, including one that only appears when somebody keeps a second reference to a string.

**This is a Deep K chapter.**
It is about measuring the exponent before the constant, and about the specific Python idioms whose exponent is not what it looks like.

## Section index

- **87.1** The doubling method, exactly
- **87.2** The accidental quadratics
- **87.3** Measurement: the same method on a clock
- **87.4** Edges and failure modes
- **87.5** Connections
- **87.6** Exercises
- **87.7** Summary and cross-references

Listings live under `code/ch168/` and are re-executed by `make verify` on both verification interpreters.

---

## 87.1 The doubling method, exactly

```python
# code/ch168/l01_measuring_the_exponent.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- primitive operations at n=100 and n=200, and the exponent ---
  operation                     n=100    n=200  exponent  class
  ------------------------------------------------------------------
  x in list                       100      200      1.00  linear
  x in set                          1        1      0.00  constant
  duplicates, nested loops      4,950   19,900      2.01  quadratic
  duplicates, with a set          200      400      1.00  linear
  list.sort() on shuffled         541    1,262      1.22  n log n
--- what the doubling method is actually doing ---
  cost(n) = c * n^k, so cost(2n)/cost(n) = 2^k regardless of c;
  taking log2 of the ratio cancels the constant and leaves the exponent
--- and why the constant does not matter to this measurement ---
  a linear algorithm with a terrible constant still doubles when n doubles;
  a quadratic one with a tiny constant still quadruples, and wins the race
  in the other direction at every subsequent doubling
```

**These are counts, not times, and that is the point.**
The primitive being counted is a comparison or a hash, made observable by a small class that tallies its own `__eq__`, `__lt__`, and `__hash__` calls. Because nothing is timed, the numbers are exact, reproducible, and identical on both interpreters. `x in list` is exactly 100 comparisons for a missing element in a 100-element list, exactly 200 in a 200-element one. The nested-loop duplicate check is exactly `n(n-1)/2`: 4,950 and 19,900.

**The method distinguishes more than linear from quadratic.**
`list.sort()` on shuffled input lands at **1.22**, correctly identifying `n log n` rather than rounding to either neighbour. That precision matters when the question is whether a change actually removed a log factor or merely moved work around.

**The technique generalises past comparisons.**
When the operation is not this convenient, count whatever it does per step: rows fetched, bytes copied, files opened, HTTP requests issued, allocations made. An ORM that issues one query per row has an exponent of 1 in queries and will fall over at a scale a profiler run on 50 rows will never reveal. Counting the right primitive is usually easier than timing, and always more exact.

**Why the constant is the wrong thing to look at first.**
A linear algorithm with a terrible constant still doubles when `n` doubles. A quadratic one with a tiny constant still quadruples. The two curves cross exactly once, and after that crossing the gap widens without limit. Optimising the constant of a quadratic moves the crossing point; it does not change what happens after it.

---

## 87.2 The accidental quadratics

Python makes several quadratic algorithms look like linear ones, because the quadratic part is inside a C loop and the source is a single method call. These are the ones worth knowing by sight.

| the idiom | why it is quadratic | the linear form |
|---|---|---|
| `s += x` in a loop | each concatenation may copy the whole string | `"".join(parts)` |
| `list.insert(0, x)` | every element shifts up one slot | `collections.deque.appendleft` |
| `list.pop(0)` | every element shifts down one slot | `deque.popleft` |
| `x in list` inside a loop over n items | a linear scan per iteration | `x in set` |
| `sum(list_of_lists, [])` | builds a new list per addition | `itertools.chain.from_iterable` |
| `del lst[0]` in a loop | same shift as `pop(0)` | `deque`, or slice once |
| repeated `str.replace` over growing text | rescans from the start each time | one pass, or `re.sub` |
| `df.append(row)` per row (pandas) | copies the frame each time | build a list, construct once |

**The pattern is always the same.** An operation that is O(n) in the size of a container is placed inside a loop that runs n times, and the O(n) part is invisible because it is one method call. `insert(0, x)` looks exactly as cheap as `append(x)` in the source and is not.

**The string case has a twist that makes it worse, not better.**
`s += x` in a loop measures **linear** on CPython, because the interpreter resizes the string in place when it holds the only reference to it (Chapter 74). That optimisation has a precondition, "nothing else refers to this string", which is invisible at the call site and is broken by appending the intermediate to a list, passing it to a logger, capturing it in a closure, or holding it in a debugger. §87.3 measures both: plain `+=` at exponent **1.00**, and the same loop with one extra reference at **1.99**.

This is the most dangerous shape a performance bug can have: correct in the benchmark, correct in the test, quadratic in production the day someone adds logging. `"".join` is linear unconditionally and is the reason the rule is stated without exception.

**Finding them in code you did not write.**
Grep is surprisingly effective: `insert(0`, `pop(0)`, `+= ` on a name that is a string in a loop, ` in ` where the right operand is built with `list(`. But the reliable method is §87.1's: instrument the suspicious function, run it at `n` and `2n`, and read the exponent. It takes five minutes and it does not require understanding the code.

---

## 87.3 Measurement: the same method on a clock

**Methodology.** `code/ch168/bench_accidental_quadratics.py`.
The doubling method with a timer instead of a counter, for cases whose primitive is inside C. Run at `n` and `4n` and take `log4` of the ratio; the wider span gives the ratio room to clear measurement noise. `min` of 7 runs at each size. Membership cases use a smaller `n` because they are already quadratic.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | n | t(n) | t(4n) | exponent | class |
|---|---|---|---|---|---|
| `s += x` | 4,000 | 0.12 ms | 0.49 ms | **1.00** | linear |
| `s += x`, second reference held | 4,000 | 1.39 ms | 21.91 ms | **1.99** | **quadratic** |
| `"".join(parts)` | 4,000 | 0.05 ms | 0.21 ms | 0.99 | linear |
| `list.insert(0, x)` | 4,000 | 2.46 ms | 38.04 ms | **1.98** | **quadratic** |
| `deque.appendleft(x)` | 4,000 | 0.06 ms | 0.25 ms | 1.03 | linear |
| `x in list`, in a loop | 500 | 0.41 ms | 6.49 ms | **1.99** | **quadratic** |
| `x in set`, in a loop | 500 | 0.01 ms | 0.07 ms | 1.11 | linear |
| `sum(list_of_lists, [])` | 4,000 | 10.17 ms | 235.37 ms | **2.27** | **quadratic** |
| `chain.from_iterable` | 4,000 | 0.20 ms | 0.87 ms | 1.05 | linear |

**The method transfers unchanged.**
Nothing about the technique changed when the counter became a clock; only the precision did. Exponents that were exact to two decimals from counting are exact to about one from timing, which is enough to separate 1 from 2 with no ambiguity.

**Every quadratic row has a linear neighbour that is also simpler.**
`deque.appendleft` is not a clever trick, it is the data structure designed for the operation. `chain.from_iterable` is not obscure, it is what the standard library provides for flattening. In every pair here the linear form is at least as readable as the quadratic one, which is worth stating because it removes the usual objection: this is not a readability-for-speed trade.

**The two string rows are the chapter's warning.**
Plain `+=` is linear; the same loop with one extra reference is quadratic, and the difference between the two programs is one `append` that has nothing to do with the string building. At `n = 16,000` that is 0.49 ms against 21.9 ms, a factor of **45**, and it grows.

**`sum(list_of_lists, [])` at 2.27 is worse than quadratic-looking for a reason.**
It builds a new list on every addition, so it both copies quadratically *and* allocates linearly-many objects, and the allocator's behaviour at increasing sizes adds a little above the clean exponent. The direction of the error does not matter; the classification does.

**And the honest scope of the chapter.**
None of this is about the interpreter. These exponents would be identical in any language, and Chapter 78's ceiling is irrelevant to them: an O(n²) loop written in C is still O(n²). That is precisely why this chapter comes before any of the escape hatches. **Book I** cannot rescue a quadratic algorithm, it can only run it faster, and the shared order-book system's price-level lookups are a dictionary rather than a list scan on both sides for exactly this reason.

---

## 87.4 Edges and failure modes

**A 4x span averages over a range.** §87.3.
If an algorithm changes behaviour partway (a cache fills, a container switches representation), the measured exponent is an average across the transition. Measure at three or four sizes and look at the sequence, not one ratio.

**Amortised costs need enough operations to amortise.**
`list.append` is amortised O(1) but a single append that triggers a reallocation is O(n). Measuring at very small `n`, or measuring one operation rather than a loop of them, reports the worst case as if it were typical.

**Asymptotics say nothing about your actual `n`.**
An O(n²) algorithm on `n = 20` is instant, and the linear rewrite may be slower there because of its constant. The exponent tells you what happens as `n` grows; whether `n` grows is a question about your system, not your code.

**The exponent can hide in a dependency.**
An ORM's `for row in query:` may be O(n) queries. A `pathlib` walk may be O(n) `stat` calls. Counting the primitive that crosses a boundary, queries, syscalls, requests, finds these where a CPU profile will not.

**Sorting is not a way to avoid a scan; it is a way to pay for many.**
Sorting to enable binary search is `n log n` up front to make each of `m` lookups `log n`. That wins when `m` is large and loses when it is 1. Set or dict construction is the usual better answer in Python because building is linear and lookup is constant.

**A quadratic that is fast enough is fine.**
This chapter's rule is "measure the exponent first", not "eliminate every quadratic". A quadratic over a bounded 50-element list inside a request handler is not a bug. Knowing it is quadratic is what lets you say so with confidence, and what tells you which line to revisit when the bound changes.

**Beware measuring with sorted or degenerate input.** §87.1 and Chapter 85.
Timsort on sorted input is linear. A hash table with adversarial keys degrades to linear lookups. The exponent you measure is the exponent for the input you used.

---

## 87.5 Connections

**Backward.**
Finding which function to apply this to is Chapter 86. The honest-measurement rules that make the timing version trustworthy are Chapter 85. The string case, and why `join` allocates once, is Chapter 74. The interpreter's per-element cost, which is a constant and therefore not this chapter's subject, is Chapter 78.

**Forward.**
Choosing the container that gives you the exponent you want is Chapter 88. Memory growth, which has its own exponent and is invisible in a time profile, is Chapter 89. Caching, which changes the exponent by removing repeated work, is Chapter 90. Streaming, which changes the memory exponent rather than the time one, is Chapter 91. `list`, `dict`, `set`, and `deque` internals are Deep Q.

**Across books.**
This is the chapter whose conclusions are identical in both books, which is unusual enough to be worth saying. **Book I**'s C++ has different constants and the same exponents, and its own accidental quadratics (`std::vector::insert` at the front, `std::list` traversal, string concatenation in a loop) map one-to-one onto this table. The shared system's data structures were chosen by this analysis before either implementation was written.

---

## 87.6 Exercises

**1. Count, do not time.** Reproduce §87.1. Then add an operation of your own whose exponent you can predict, and confirm the prediction. If it disagrees, work out which of you is wrong before reading further.

**2. Break the string optimisation.** Reproduce §87.3's first two rows. Then find three different ways to hold a second reference to the string being grown, and confirm each one makes the loop quadratic.

**3. Audit a function you did not write.** Take a function from a dependency, instrument it at `n` and `2n`, and report its exponent. Say what primitive you counted and why.

**4. The crossing point.** For `list.insert(0, x)` against `deque.appendleft`, find the `n` at which they take the same time. Explain why the crossing exists at all, given one is quadratic.

**5. Count something that is not a comparison.** Measure the exponent of an operation in queries, syscalls, or allocations rather than in CPU time. Say what a CPU profile would have shown instead.

**6. The design question.** CPython could make `list.insert(0, x)` amortised O(1) by keeping spare capacity at both ends, as a deque does. Argue why it does not: what that would cost every other list operation, what it would do to the C-API's guarantee that a list's items are contiguous (Chapters 79 and 82), and why the standard library ships `deque` as a separate type instead.

---

## 87.7 Summary and cross-references

- **Measure the exponent before the constant.** A constant-factor win is bounded; a change of exponent wins by a growing factor at every doubling.
- **The doubling method is exact when you count rather than time.** `cost(n) = c·n^k` implies `cost(2n)/cost(n) = 2^k`, so `log2` of the ratio is the exponent and the constant cancels. Verified counts: `x in list` **1.00**, `x in set` **0.00**, nested-loop duplicates **2.01**, set-based duplicates **1.00**, `list.sort()` **1.22** (correctly `n log n`, not rounded to a neighbour).
- **Count whatever the algorithm does per step** when comparisons are not available: rows, syscalls, requests, allocations. Usually easier than timing and always more exact.
- **The accidental quadratics:** `s += x` in a loop, `list.insert(0, x)`, `list.pop(0)`, `x in list` inside a loop, `sum(list_of_lists, [])`, `del lst[0]` in a loop, repeated `str.replace`. Each has a linear alternative that is at least as readable.
- **Measured on a clock over a 4x span:** `s += x` **1.00** (linear), the same loop **with one extra reference to the string 1.99** (quadratic), `list.insert(0, x)` **1.98**, `x in list` in a loop **1.99**, `sum(list_of_lists, [])` **2.27**; the linear alternatives measure 0.99 to 1.11.
- **The string case is the dangerous one:** CPython's in-place resize hides the quadratic until something takes a second reference, which is invisible at the call site. `"".join` is linear unconditionally.
- **None of this is about the interpreter.** These exponents are the same in any language, which is why this chapter precedes every escape hatch: a quadratic algorithm written in C is still quadratic.
- **Edges:** a wide span averages over transitions; amortised costs need many operations; asymptotics say nothing about your actual `n`; the exponent can hide in a dependency's query or syscall count; a bounded quadratic is fine, and knowing it is quadratic is what lets you say so.

**Cross-references.** Finding the function → Chapter 86. Honest measurement → Chapter 85. `join` and allocation → Chapter 74. The interpreter's constant → Chapter 78. Container choice → Chapter 88. Memory growth → Chapter 89. Caching → Chapter 90. Streaming → Chapter 91. Container internals → Deep Q.
