# Chapter 50: Reading Bytecode with `dis`

"Comprehensions are much faster than append loops" is one of the most-repeated pieces of Python performance
advice, and `dis` can both explain where it came from and check whether it is still true. Disassemble the
two, and the difference is real and structural: a list comprehension compiles to a dedicated `LIST_APPEND`
opcode, while an append loop looks up `list.append` (a `LOAD_ATTR`) and `CALL`s it on every iteration. That
per-item method call is exactly why comprehensions were historically faster. But *measure* the two on a
current interpreter and the gap is only **1.11x**, because the specializing interpreter (Chapter 17) turns
the repeated `.append` lookup-and-call into a fast specialized path. `dis` shows *what* differs; measurement
shows *how much it is worth now*, and together they turn folklore into a checkable fact.

That pairing, read the bytecode to understand, measure to quantify, is the theme of this chapter. It
continues **Deep S** with `dis`, the disassembler that shows the actual instructions the interpreter runs,
and it is the introspection tool that makes the rest of the book's performance claims verifiable rather than
asserted.

## Section index

- **50.1** What `dis` shows
- **50.2** Structural difference, narrowed at runtime
- **50.3** Measurement: comprehension vs loop today
- **50.4** Edges and failure modes
- **50.5** Connections
- **50.6** Exercises
- **50.7** Summary and cross-references

Listings live under `code/ch050/` and are re-executed by `make verify` on both interpreters.

---

## 50.1 What `dis` shows

```python
# code/ch050/l01_dis.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- comprehension: builds the list with a dedicated opcode ---
  uses LIST_APPEND opcode : True
  CALL instructions       : 1 (just range())
  does a .append lookup?  : False
--- append loop: looks up and calls list.append each iteration ---
  uses LIST_APPEND opcode : False
  looks up .append (LOAD_ATTR): True
  CALL instructions       : 2 (range() and .append())
--- the point: same result, different bytecode ---
  results equal           : True
  comprehension avoids the per-item method call the loop pays
```

`dis.dis(func)` prints the disassembly; `dis.get_instructions(func)` yields the instructions as objects you
can inspect programmatically, which is what this listing does to extract *stable* structural facts. (The raw
disassembly text itself is version-dependent, opcode names and numbering change between releases, which is
why the listing prints the extracted facts rather than the raw dump; those facts, "does a `LIST_APPEND`
appear," "is there a `LOAD_ATTR` for `.append`," are identical on both interpreters.)

The facts: the **comprehension** contains a `LIST_APPEND` opcode and no `.append` attribute lookup, its only
`CALL` is to `range()`. The **loop** contains no `LIST_APPEND`; instead it has a `LOAD_ATTR` (to fetch the
`append` method) and a second `CALL` (to invoke it), executed every iteration. Both produce the identical
list. The bytecode is the evidence: the comprehension has a dedicated fast path for the append; the loop pays
a method lookup and call per element. A representative disassembly of the loop body (on 3.13, abbreviated)
makes it concrete:

```text
    LOAD_FAST     out
    LOAD_ATTR     append      # fetch the bound method, every iteration
    LOAD_FAST     x
    ...
    CALL          1           # call list.append
    POP_TOP
```

---

## 50.2 Structural difference, narrowed at runtime

The bytecode difference is exactly the kind that *used* to translate directly into a speed difference: a
method lookup (`LOAD_ATTR`) plus a call (`CALL`) per iteration is genuinely more work than a single
`LIST_APPEND` opcode. On older interpreters, comprehensions were meaningfully, sometimes ~2x, faster for this
reason, and the folklore formed around real measurements.

The specializing interpreter (Chapter 17) changed the arithmetic. It watches the repeated `LOAD_ATTR` for
`append` on a value that is always a `list`, and specializes it to a fast path that skips the general method-
resolution machinery; likewise the `CALL` specializes to a direct call of the C-level `list.append`. So the
loop's per-iteration overhead, while still more instructions than the comprehension's, is now cheap
*instructions*, and the runtime gap collapses toward parity. The bytecode did not change; the *interpreter's
execution* of that bytecode got faster. This is the recurring lesson of the book's performance thread: an
optimization that folklore attributes to source-level structure (use a comprehension) has been absorbed into
the runtime, so the source-level choice matters less than it once did. `dis` is how you see that the
structural difference persists even as its cost shrinks.

---

## 50.3 Measurement: comprehension vs loop today

**Methodology.** `code/ch050/bench_comp_vs_loop.py`. Building a 1000-element list via a comprehension versus
an append loop. `min` per call; ratio relative to the comprehension. CPython 3.13.5, Apple M3 Pro, macOS
27.0, arm64.

| build a 1000-element list | min per call | ratio |
|---|---|---|
| list comprehension | **18,202 ns** | 1.00x |
| append loop | **20,115 ns** | **1.11x** |

The comprehension is **1.11x** faster, a real but modest edge, not the 2x the folklore promises. The
`dis`-visible structural advantage (no per-item method call) is now worth about 10%, because the specializing
interpreter has made the loop's method call cheap. Both are dominated by the actual work (`x * x` a thousand
times), against which the append overhead is a small fraction.

The lesson is twofold. First, on the specific claim: **prefer comprehensions for readability and a small
speed edge, not for a dramatic speedup that no longer exists.** Second, on method: **`dis` plus a benchmark
is how you check a performance claim instead of repeating it.** When someone asserts "X compiles to faster
bytecode," disassemble both to see if the bytecode really differs, then measure to see whether the difference
survives the specializing interpreter. Most of this book's performance findings were established exactly this
way, and `dis` is the tool that makes the reasoning transparent rather than magical.

---

## 50.4 Edges and failure modes

**Reading a speed conclusion from bytecode alone.** §50.2. Different or "more" bytecode does not reliably mean
slower: the specializing interpreter can make more instructions run as fast as fewer. `dis` shows structure;
only a benchmark shows speed. Never conclude "fewer opcodes, therefore faster" without measuring.

**Version-dependent disassembly.** §50.1. Opcode names, numbering, and the instruction stream change between
releases (and specialization means the *runtime* opcodes differ from the *compiled* ones). Do not hard-code
or assert on exact disassembly text; extract stable structural facts, or pin the interpreter version.

**Adaptive/specialized opcodes are hidden by default.** `dis` shows the *unspecialized* bytecode. To see the
adaptive forms the interpreter actually runs (`LOAD_ATTR_INSTANCE_VALUE`, etc.), use `dis.dis(func,
adaptive=True)` after the function has run and specialized. The default view is the compiler's output, not
the runtime's.

**Disassembling the wrong thing.** `dis` on a generator function shows the generator's code, not the code of
what it yields; `dis` on a decorated function may show the wrapper. Disassemble the exact `__code__` object
you mean (use `func.__wrapped__` or the inner code object as needed).

**Confusing `dis` with profiling.** `dis` tells you what instructions exist, not which run hot. To find the
bottleneck, profile (`cProfile`, `sys.monitoring`, Chapter 22); `dis` explains a hotspot once profiling has
found it. They are complementary, not substitutes.

---

## 50.5 Connections

**Backward.** The specializing interpreter that narrows the §50.3 gap is Chapter 17. The `__code__` object
`dis` disassembles is the function internal of Chapters 5 and 49 (`inspect` reads the same object at a higher
level). The comprehension/loop constructs are Chapter 3. The `LOAD_FAST`/`LOAD_GLOBAL` distinction visible in
disassembly is Chapter 2.

**Forward.** Profiling (`cProfile`, `sys.monitoring`) to find *where* time goes, complementing `dis`'s *what
runs*, is Chapter 22 and later Deep S. The copy-and-patch JIT (Chapter 27) compiles this bytecode further.
The compiler pipeline that produces the bytecode (AST to code object) is a **Deep S** internals topic.

**Across books.** `dis` is the verification tool behind Book II's performance claims, and the same discipline
carries into **Book III**: when an inference or data-path hotspot is suspected, the answer is to disassemble
and measure, not to guess, so an optimization is adopted because it is shown to help on the target
interpreter, not because folklore says it should. **Deep U** and **Deep T** apply this to the numeric and
serving hot paths.

---

## 50.6 Exercises

**1. See the structural difference.** Use `dis.get_instructions` to confirm the comprehension has a
`LIST_APPEND` and the loop has a `LOAD_ATTR` for `append`. Explain what each opcode does and why the loop's is
per-iteration.

**2. Measure the gap.** Run §50.3's benchmark and confirm the comprehension's edge is modest (~1.1x), not the
folklore 2x. Explain, in terms of the specializing interpreter, why the structural difference is worth less
than it once was.

**3. See specialization.** Run a function in a loop many times, then `dis.dis(func, adaptive=True)`, and
observe specialized opcodes that the default disassembly does not show. Explain the difference between the
compiler's bytecode and the runtime's.

**4. Refute a bytecode claim.** Pick another "X is faster than Y" claim (e.g. `a + b` vs `''.join`, or a
generator vs a list), disassemble both, and measure. Report whether the bytecode difference translates to a
speed difference on your interpreter.

**5. The design question.** `dis` shows the compiled bytecode, but the interpreter runs a specialized version
of it. Argue why "read the bytecode" is still the right first step to understand performance despite that gap.
Your answer must address what `dis` reveals that source cannot, why bytecode count is not a speed proxy, and
how `dis` and profiling divide the work.

---

## 50.7 Summary and cross-references

- **`dis`** disassembles a function's `__code__` into the interpreter's bytecode; `get_instructions` yields it
  as inspectable objects. It answers "what does this compile to?" with evidence.
- A **list comprehension** compiles to a dedicated `LIST_APPEND` opcode; an **append loop** does a
  `LOAD_ATTR` + `CALL` for `list.append` every iteration, a real structural difference.
- **Measured:** the comprehension is only **1.11x** faster today, not the folklore 2x, because the
  specializing interpreter (Chapter 17) made the loop's per-item method call cheap. `dis` shows the structure;
  the benchmark shows it is now worth ~10%.
- **`dis` shows structure, not speed:** never conclude "fewer opcodes therefore faster" without measuring; use
  `adaptive=True` to see specialized opcodes; pair `dis` with profiling.

**Cross-references.** Specializing interpreter → Chapter 17. `__code__` and `inspect` → Chapters 5, 49.
Comprehensions → Chapter 3. `LOAD_FAST`/`LOAD_GLOBAL` → Chapter 2. Profiling and `sys.monitoring` → Chapter 22
and the rest of Deep S. The JIT → Chapter 27. Verifying hot paths → Deep T, Deep U.
