# Chapter 76: Pushing the Loop into C

Chapter 75 measured what one bytecode instruction costs and found the answer to be a few nanoseconds, which is the wrong number to optimize.
The number that decides whether a Python loop is fast is **how many instructions run per element**, and the largest available reduction is not from three to two but from six to **zero**, which is what happens when the loop itself moves below the bytecode layer into C.

`sum(xs)` and the equivalent `for` loop compute the same value.
The loop executes six bytecode instructions per element; `sum` executes **none**, because its loop is a C `for` inside `builtin_sum` and the interpreter never sees it.
That is the entire mechanism behind "use the builtin", and stating it as a count rather than as folklore is what makes it possible to say *when it does not apply*: a builtin removes bytecode only for the part of the work it performs in C.
`map` with a Python callable still enters a Python frame per element, and measures **slower** than the comprehension it is supposed to replace.

**This is a Deep H performance chapter.**
It gives the per-element instruction count as a cost model, checks the model against wall time, and marks the boundary where the model stops predicting.

## Section index

- **76.1** Counting instructions per element
- **76.2** Where the boundary actually falls
- **76.3** Measurement: does the count predict the time
- **76.4** Edges and failure modes
- **76.5** Connections
- **76.6** Exercises
- **76.7** Summary and cross-references

Listings live under `code/ch157/` and are re-executed by `make verify` on both verification interpreters.

---

## 76.1 Counting instructions per element

```python
# code/ch157/l01_c_level_loops.py
```

Verified output (CPython 3.13.5):

```text
--- bytecode instructions executed PER ELEMENT (the slope) ---
  reduce   for-loop sum                  6
  reduce   sum(xs)                       0
  map      for-loop + append            14
  map      list(map(python_fn, xs))      4
  map      list(map(str, xs))            0
  build    s += 'x' in a loop            7
  build    ''.join(genexpr)              6
  reduce   min(xs)                       0
--- the same measure, for bodies containing a comparison ---
  compare  for-loop min                  6
  compare  for-loop with a test          7
  compare  any(genexpr)                  7
--- what the zeros mean ---
  a builtin that loops in C executes NO bytecode per element: its loop is
  below the interpreter, so the per-instruction cost never applies to it
--- what the non-zeros mean ---
  a Python-level loop pays the interpreter once per instruction per element;
  a genexpr fed to a C builtin still resumes a Python frame per element
--- the rule ---
  the cheapest bytecode instruction is the one that never executes; push the
  loop into C when a builtin expresses it, and shrink the body when it cannot
```

**How the count is obtained, and why it is a slope.**
`sys.monitoring` (PEP 669, 3.12+) can deliver a callback on every executed instruction. Registering one and counting invocations gives the exact number of bytecode instructions an operation executed, with no sampling and no estimation. But the *absolute* count carries a per-version constant: the call and return sequence around the measured function differs between 3.13 and 3.14. So the listing runs each case at 100 and at 200 elements and reports the **difference divided by 100**. Differencing cancels the constant and leaves the per-element slope, which is exact and, for every case whose body contains no comparison, identical on both interpreters.

This is worth dwelling on as a measurement technique, not just as a result. A count that varies by interpreter version looks like an unstable measurement and is in fact a stable measurement plus a constant. Subtracting two points of the same measurement is how you find out which it is.

**The zeros are the whole argument.**
`sum(xs)`, `min(xs)`, and `list(map(str, xs))` execute **zero** bytecode instructions per element. Not few: none. Their per-element work happens inside a C loop, and `sys.monitoring` cannot see it because there is no bytecode there to instrument. The interpreter dispatches the `CALL` once, and control does not return to the evaluation loop until the entire reduction is finished.

**The non-zeros show what the builtin did not take.**
`any(x > 1_000_000 for x in xs)` scores 7 instructions per element even though `any` itself loops in C. The generator expression is Python code, and `any` resumes its frame once per element to get the next value. `any` took the loop; it did not take the body. Likewise `"".join("x" for _ in xs)` scores 6, while `"".join(list_of_strings)` (measured in §76.3) has no Python-level per-element cost at all.

`list(map(double, xs))` at 4 instructions per element against the hand-written loop's 14 is the same story from the other side: `map` removed the loop scaffolding (the `FOR_ITER`, the `LOAD_FAST` of the accumulator list, the `LOAD_ATTR append`, the `CALL`, the `POP_TOP`) and left the four instructions that are `double`'s body. Whether removing ten instructions and adding a C-level callback per element is a net win is a question the count cannot answer, and §76.3 does.

**Version drift, shown rather than hidden.**
The three rows whose bodies contain a comparison differ between the interpreters.

Verified output (CPython 3.14.6):

```text
  compare  for-loop min                  7
  compare  for-loop with a test          8
  compare  any(genexpr)                 12
```

Each comparing loop costs one more instruction on 3.14.6 than on 3.13.5, and the generator-expression case costs five more. This is reported as observed, not explained: attributing it would require a version-by-version read of the compiler's branch emission and the generator resume sequence, which this chapter has not done. It is here because a book that only quoted the numbers that agreed would be quietly lying about how stable these counts are.

---

## 76.2 Where the boundary actually falls

The rule "use a builtin, it loops in C" is true and is routinely applied where it does not hold. The count in §76.1 says exactly where the line is.

**A builtin removes the bytecode for the work it does in C, and no other bytecode.**

| what you write | who runs the loop | who runs the body | per-element bytecode |
|---|---|---|---|
| `for x in xs: total += x` | Python | Python | 6 |
| `sum(xs)` | C | C | 0 |
| `list(map(str, xs))` | C | C | 0 |
| `list(map(py_fn, xs))` | C | **Python** | 4 |
| `any(x > k for x in xs)` | C | **Python** | 7 |
| `[f(x) for x in xs]` | Python (inlined frame) | Python | body + scaffold |

The first three rows are the good case: the entire per-element computation is expressible as something the C implementation already does. The last three are the case that gets mis-sold. A generator expression handed to `any`, `all`, `sum`, `max`, or `join` is *still Python code being resumed once per element*; the builtin has taken the loop and left the body, and the body is usually the larger half.

**The practical decision procedure.**
Ask what the per-element work is, not what the loop looks like.

- If the per-element work is a C operation the builtin already performs (adding numbers, comparing, converting to `str`, copying bytes into a buffer), the builtin takes everything and the win is large.
- If the per-element work is a Python function or a Python expression, the builtin takes the scaffolding only, and the win is small, zero, or negative.
- If the per-element work is a Python function *and* you were going to write a comprehension anyway, write the comprehension: §76.3 measures it as the fastest of the three.

**The largest win is one level up.**
Both branches above are still per-element Python. The step that actually changes the exponent is moving the *data* into a representation whose operations are bulk C: NumPy's vectorized ufuncs (Deep T), a `bytes`/`memoryview` buffer handed to a C routine (Deep M), a compiled extension. Those are not "a builtin instead of a loop"; they are "no per-element Python at all", and they are where a hot loop goes when 4x is not enough. Chapter 78 returns to this as the ceiling on what the interpreter can do for you.

---

## 76.3 Measurement: does the count predict the time

**Methodology.** `code/ch157/bench_c_level_loops.py`.
The same operations over a 10,000-element list. Rows are only comparable when they do the same per-element work, so each table below is a fair group with its own baseline. `min` of 9 batches, 200 calls per batch.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**Reductions, where the builtin takes the whole computation.**

| reduction over 10,000 ints | time | within-pair |
|---|---|---|
| `for` loop summing | 113 us | |
| `sum(xs)` | 28 us | **4.0x faster** |
| `for` loop taking the max | 105 us | |
| `max(xs)` | 57 us | **1.85x faster** |

The instruction count predicted the direction and roughly the size for `sum`: removing 6 bytecode instructions per element removed about three-quarters of the time. `max` wins by less than half as much, and the reason is visible in the count from §76.1: both loops execute 6 instructions per element, but `max`'s C loop still performs a *rich comparison* per element, which is a type-dispatched call, while `sum`'s C loop performs an integer add on the unboxed fast path. The builtin took the same amount of bytecode away in both cases; it replaced it with different amounts of C.

**Transforms with a Python callable, where the builtin takes only the scaffolding.**

| build a 10,000-element list, Python callable | time | vs comprehension |
|---|---|---|
| list comprehension | 204 us | 1.00x |
| `for` loop with `.append` | 229 us | 1.12x slower |
| `list(map(fn, xs))` | 242 us | **1.18x slower** |

This is the row that contradicts the folklore. `map` executes fewer bytecode instructions per element than the hand-written loop (4 against 14, §76.1) and is nonetheless the **slowest** of the three. The instructions it removed were cheap ones; what it added is a C-level callback that must build an argument tuple-equivalent and re-enter the interpreter for `double`'s frame on every element. The comprehension wins because since 3.12 it runs in the *enclosing* frame with no per-element function call at all beyond `double` itself (PEP 709, Chapter 77).

The honest summary of this table is that when the body is Python, all three forms cost about the same, the differences are under 20%, and the choice should be made on readability.

**Transforms with a C callable, where the builtin can take the body too.**

| build a 10,000-element list, C callable | time | vs `map` |
|---|---|---|
| `list(map(str, xs))` | 265 us | 1.00x |
| `[str(x) for x in xs]` | 272 us | 1.03x slower |

With `str` in place of a Python function, `map` moves from 18% slower to 3% faster, and 3% is not a reason to choose either. The direction flipped exactly where §76.2 predicts, and the magnitude is small enough to say plainly: `map` with a C callable is a wash, and `map` with a Python callable is a small loss.

**Building an immutable result, where the difference is an allocation strategy.**

| build a 10,000-piece string | time | vs `join(list)` |
|---|---|---|
| `"".join(list)` | 42 us | 1.00x |
| `"".join(genexpr)` | 152 us | 3.6x slower |
| `s += "x"` in a loop | 258 us | **6.2x slower** |

`"".join` over a materialized list is the only row here with no per-element Python: `join` walks a C array of string pointers, sums the lengths, allocates once, and copies. Feeding it a generator instead costs 3.6x, and that cost is exactly the 6 instructions per element from §76.1, the generator frame being resumed 10,000 times. The `+=` loop is 6.2x, for the reasons Chapter 74 measured.

**What the model got right and where it stopped.**
The per-element instruction count correctly predicted every *direction* except one: it says `map` should beat the hand-written loop, and `map` loses. The count measures bytecode removed and is blind to C-level cost added. That is the model's boundary, and knowing it is the difference between using the count as a tool and trusting it as an oracle. When the two disagree, the timing is right and the count is telling you where to look for the reason.
**Book I**'s side of the shared system is what the last row of §76.2 points at: when the per-element work must be genuinely fast, the loop does not move from Python bytecode into a Python builtin, it moves out of Python entirely, and the buffer protocol (Deep M) is how the data gets there without a copy.

---

## 76.4 Edges and failure modes

**`sys.monitoring` instruction counting disables specialization while it is active.**
The counts in §76.1 are counts of instructions *executed*, which is what the model needs, but they are gathered on an interpreter that is not specializing those sites. The count is right; do not read timing into it. That is why §76.3 exists as a separate measurement.

**A generator expression is not free just because a builtin consumes it.** §76.1.
`any(genexpr)`, `sum(genexpr)`, `"".join(genexpr)`, and `max(genexpr)` all resume a Python frame per element. If the elements are already in a list, pass the list. If they are not, the generator is often still the right call for memory reasons, and §76.3 quantifies the price at 3.6x for `join`.

**`map` and `filter` are lazy; wrapping them in `list()` is part of the cost.**
`map(f, xs)` alone does nothing. Benchmarks that time `map(f, xs)` without consuming it measure the construction of a map object and report absurd speedups. Every row in §76.3 consumes the result.

**`sum` on strings is a `TypeError`, deliberately.**
`sum(list_of_strings, "")` raises, precisely to push you to `"".join`. `sum` on lists (`sum(list_of_lists, [])`) is not blocked and is quadratic; use `itertools.chain.from_iterable`.

**The reduction win depends on the element type.**
`sum` over `int` uses a fast path for machine-word integers. `sum` over `Decimal`, `Fraction`, or an object with `__add__` calls back into Python per element and the win largely evaporates. Measure with your element type, not with `range`.

**Do not rewrite readable code for a 3% ratio.** §76.3.
Two of the four tables here have differences under 20%, which for most code is below the threshold at which a rewrite pays for the review it costs. The `sum` and `join` tables are the ones worth acting on.

**The count is a slope, so it says nothing about small inputs.**
An operation with a 0 slope and a large constant loses to a 6-slope operation with a small constant, on short inputs. `sum` beats a loop at 10,000 elements; at 3 elements the difference is the call overhead and the loop may win. Hot means hot.

---

## 76.5 Connections

**Backward.**
The per-instruction cost that makes the per-element count matter is Chapter 75. The frame that a Python callable needs and a C callable does not is Chapter 55. The code object being compiled once is Chapter 54. The `join`-versus-`+=` result is Chapter 74, re-measured here in a different frame.

**Forward.**
Comprehension inlining, which is why the comprehension beats `map` with a Python callable, is Chapter 77. The dispatch loop that charges per instruction, and the JIT that is trying to reduce that charge, are Chapter 78. Vectorized bulk operations, the level above "use a builtin", are Deep T. Getting the data to a C routine without copying is Deep M. `itertools`, the C-level composition of these loops, is Deep Q. Profiling, which is how you find out whether any of this matters in your program, is Deep K.

**Across books.**
The boundary this chapter marks is the boundary the two books share. **Book I** owns the matching engine because its per-element work is exactly the case §76.2 calls "no per-element Python at all"; Python's job on the shared system is to express the loop that *dispatches* to it, not the loop that does it. The tick stream crosses the buffer protocol with no copy, and the Python side then reduces over it with operations whose slope is zero.

---

## 76.6 Exercises

**1. Count your own loop.** Take a loop from your code and measure its per-element slope with the technique in §76.1. Explain the number by naming the instructions in the body.

**2. Find a zero.** Rewrite one of your loops so that its slope becomes 0, and verify it. If you cannot, say which part of the body is Python and why no builtin expresses it.

**3. Reproduce the contradiction.** Reproduce §76.3's Python-callable table. Confirm that `map` executes fewer instructions per element than the loop and is nonetheless slower. Explain where the time goes.

**4. Element type matters.** Repeat the `sum` measurement with `Decimal` elements instead of `int`. Predict the ratio first, then measure it, then explain the difference from the `int` case.

**5. Where the slope lies.** Measure `sum(xs)` against the `for` loop at 3, 30, 300, and 30,000 elements. Find the crossover and explain it in terms of constant versus slope.

**6. The design question.** CPython could compile a comprehension whose body is a single builtin call into a C-level loop, eliminating the per-element frame. Argue why it does not: what would have to be proven about `str` at compile time, and what would break the moment someone rebound the name.

---

## 76.7 Summary and cross-references

- The number that decides a Python loop's cost is **bytecode instructions executed per element**, and it is measurable exactly with `sys.monitoring` (PEP 669) by taking the **slope** between two input sizes, which cancels the per-version constant.
- A builtin whose C loop performs the whole per-element computation executes **zero** bytecode per element: `sum(xs)`, `min(xs)`, `list(map(str, xs))`. The interpreter's per-instruction cost never applies to it.
- A builtin fed **Python** per-element work takes the loop and leaves the body: `any(genexpr)` costs 7 instructions per element, `list(map(py_fn, xs))` costs 4. The builtin removes bytecode only for the part it performs in C.
- **Measured on 3.13.5, 10,000 elements:** `sum` is **4.0x** faster than the loop, `max` **1.85x** (its C loop still does a rich comparison per element). With a **Python** callable, the list comprehension is fastest and `map` is **1.18x slower** than it; with a **C** callable `map` is **1.03x faster**, a wash. `"".join(list)` beats `"".join(genexpr)` by **3.6x** and `+=` by **6.2x**.
- **The model's boundary:** the instruction count is blind to C-level cost *added*, which is why it mispredicts `map`. When count and timing disagree, the timing is right and the count says where to look.
- **Edges:** monitoring disables specialization, so counts are not timings; `map`/`filter` are lazy and must be consumed to be timed; the reduction win depends on the element type; the slope says nothing about short inputs; differences under 20% are usually not worth a rewrite.
- The step beyond "use a builtin" is **no per-element Python at all**: vectorized arrays (Deep T) or a compiled extension over a shared buffer (Deep M).

**Cross-references.** Per-instruction cost → Chapter 75. Frames and call overhead → Chapter 55. Code objects → Chapter 54. `join` versus `+=` → Chapter 74. Comprehension inlining → Chapter 77. Dispatch and the JIT → Chapter 78. Vectorization → Deep T. The buffer protocol → Deep M. `itertools` → Deep Q. Profiling → Deep K.
