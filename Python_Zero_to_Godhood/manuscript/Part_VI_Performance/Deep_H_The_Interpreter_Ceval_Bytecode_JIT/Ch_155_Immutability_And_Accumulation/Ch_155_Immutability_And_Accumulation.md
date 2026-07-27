# Chapter 74: Immutability and Accumulation

`s += x` in a loop is the most common performance mistake in Python that *usually gets away with it*, and understanding why, and when it does not, is the subject of this chapter.
The root is **immutability**: a `str` cannot be changed in place, so `s += x` cannot *grow* `s`, it conceptually builds a *new* string of length `len(s) + len(x)`.
Repeat that in a loop and you are, in the naive model, rebuilding the whole string on every iteration, escalating work.

CPython softens this with a *specific optimization*, if the string being concatenated to has *no other references*, the interpreter resizes it in place, so `s += x` avoids the quadratic blow-up *in the common case on CPython*.
But that optimization is **fragile**: it degrades to O(n^2) the moment the string has another reference, and it does not exist on other implementations (PyPy) or in older Python.
So the reliable, portable, and *faster* pattern (measured **2.6x**) is the idiomatic one: **accumulate the pieces in a mutable container (a list) and materialize the immutable result once (`"".join`)**.
`join` computes the total length up front and allocates the result *a single time*.

This generalizes beyond strings into a principle: **do not grow an immutable object incrementally; build in a mutable buffer and convert to the immutable result once.**

**This is a Deep H performance chapter.**
It connects immutability (a language design, Deep A) to its performance implication, uses the code/allocation model of Deep B, and states a pattern that recurs across strings, bytes, and tuples.

## Section index

- **74.1** Immutability and the join pattern
- **74.2** The general accumulation pattern
- **74.3** Measurement: `+=` versus `join`
- **74.4** Edges and failure modes
- **74.5** Connections
- **74.6** Exercises
- **74.7** Summary and cross-references

Listings live under `code/ch155/` and are re-executed by `make verify` on both verification interpreters.

---

## 74.1 Immutability and the join pattern

```python
# code/ch155/l01_accumulation.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- strings are IMMUTABLE: concatenation makes a NEW object ---
  s + 'd' is a different object : True
  the original is unchanged      : abc
--- the reliably fast pattern: accumulate in a list, join once ---
  ''.join(['0','1','2','3','4']) : '01234'
--- compare: the += loop (works, but does escalating allocation) ---
  += loop result (same value)   : '01234'
  same result, but join scales better (the benchmark)
--- the pattern generalizes to bytes: bytearray (mutable) -> bytes ---
  bytearray built then frozen   : b'ABC'
--- and to any immutable result: build in a list, convert at the end ---
  list (mutable, append cheap) -> tuple/str/bytes (immutable) once
--- the rule ---
  do not grow an immutable object incrementally (s += x in a loop); build
  in a mutable container and materialize the immutable result once (join)
```

**Strings are immutable.**
`s + "d"` produces a *different* object (the `id` changes) and leaves the original `s` unchanged. A string's characters cannot be modified or appended *in place*, any "modification" creates a *new* string. This is the language design (Deep A): strings are immutable, which makes them hashable (dict keys, Chapter 23), safely shareable, and interned (Chapter 19), but it means you cannot *grow* one.

**The consequence for `+=` in a loop.**
Because `s += x` cannot grow `s` in place (immutability), it must, in the naive model, allocate a *new* string of the combined length and copy both parts. Do this `n` times and the total copying is `1 + 2 + 3 + ... + n = O(n^2)`, quadratic, the classic string-building disaster.

**The join pattern avoids it.**
`"".join(parts)` is the idiomatic solution: accumulate the pieces in a *list* (which *is* mutable, `append` is cheap and amortized O(1)), then `join` them into the final string *once*. `join` first computes the *total* length (summing the piece lengths), allocates the result string *one time*, and copies each piece in, O(n) total, one allocation.
The `+=` loop produces the *same value*, but through escalating allocation; `join` produces it with a single allocation.

So the pattern is: **build with a mutable list, materialize the immutable string once with `join`.**

---

## 74.2 The general accumulation pattern

The string case is the most common instance of a *general* principle, and recognizing the pattern lets you apply it everywhere immutability meets incremental building.

**The principle: accumulate in a mutable container, convert to the immutable result once.**

- **Strings:** build a `list` of pieces, `"".join(list)`. §74.1.
- **Bytes:** build a `bytearray` (mutable), convert to `bytes` once (`bytes(buf)`). The listing shows this: `bytearray` `append` is cheap, `bytes(buf)` freezes it once.
- **Tuples:** build a `list`, convert to `tuple` once (`tuple(lst)`), rather than `t += (x,)` in a loop (which rebuilds the tuple each time).
- **Frozensets:** build a `set`, convert to `frozenset` once.

In every case, the *mutable* type (`list`, `bytearray`, `set`) supports cheap incremental growth (amortized O(1) `append`/`add`), while the *immutable* type (`str`, `bytes`, `tuple`, `frozenset`) cannot be grown, so you grow the mutable one and convert *at the end*.

**Why the mutable containers are cheap to grow.**
A `list` (or `bytearray`) over-allocates: it keeps spare capacity, so most `append`s just write into the existing buffer, and only occasionally does it reallocate (to a larger buffer, geometric growth), giving *amortized* O(1) append (the `list` internals are Deep Q). So building an `n`-element list is O(n) total, not O(n^2). The immutable types cannot do this (they have no spare capacity to grow into; they are fixed at creation), which is *why* you build in the mutable one.

**When it matters:**

- **A loop building a large string/bytes/tuple.** The larger the result and the more iterations, the more the pattern matters (the `+=` cost grows faster). For a few concatenations, `+=` is fine (readable, and the CPython optimization covers it); for a *loop* over many pieces, use the accumulate-and-convert pattern.
- **Portable, reliable performance.** Even where CPython's `+=` optimization saves you, the `join` pattern is *reliably* O(n) (no dependence on refcounts or implementation), so it is the right default for code that must be fast *regardless* of the interpreter.

The rule: **do not grow an immutable object incrementally in a loop; accumulate in the corresponding mutable container and materialize the immutable result once.**
This is the general form of "use `join` for strings", and it is a direct consequence of immutability, the property that makes immutable types safe and hashable also makes them un-growable, so incremental building belongs to the mutable types.

---

## 74.3 Measurement: `+=` versus `join`

**Methodology.** `code/ch155/bench_accumulation.py`.
Building a 50,000-piece string three ways: `+=` in a loop, a list of pieces then `"".join`, and `"".join` over a generator.
`min` of 5 runs, 100 builds.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| build a 50,000-piece string | time | vs list+join |
|---|---|---|
| list + `"".join` | 0.68 ms | 1.0x |
| `"".join(genexpr)` | 1.02 ms | 1.5x |
| `+=` in a loop | 1.75 ms | **2.6x** |

`list + "".join` is the fastest; `+=` is **2.6x** slower (2.4x on 3.14.6), and the generator-`join` sits in between (the generator has per-item overhead but avoids materializing the list, a memory-time trade).

The `+=` here is *not* the O(n^2) catastrophe it would be without CPython's optimization, because CPython *does* resize the string in place (the string has only one reference, `s`), so it is "only" 2.6x slower, not thousands of times.
But that 2.6x, and the *fragility* behind it, is the lesson.
`join` wins because it does *one* allocation of the known total size and copies once; `+=`, even optimized, does incremental resizing (reallocating as the string outgrows its buffer) and re-checks the single-reference condition each time.
And the `+=` optimization is *conditional*: give the string another reference (a second variable, a list holding it, a closure capturing it) and CPython *cannot* resize in place, so it falls back to O(n^2), and on PyPy or older Python the optimization is absent entirely.

So the guidance is unconditional: **build strings (and other immutable sequences) with the accumulate-and-convert pattern, not `+=` in a loop.**
It is faster (2.6x here, reliably), portable (no dependence on a fragile optimization), and idiomatic (`"".join` is the Pythonic way).
This is a Deep H performance theme, immutability has a *cost model* (you cannot grow immutable objects, so incremental building copies), and the pattern (mutable buffer, convert once) is how you work *with* immutability rather than against it.
It fits the volume's arc: just as the code object is compiled once (Chapter 54), constants are folded once (Chapter 56), and the exception guard is free (Chapter 73), here the string is *allocated* once (join), the recurring performance principle of *do the expensive thing once*, applied to allocation.
**Book I**'s hot paths that build strings, bytes, or other immutable results (serializing a message, formatting output, assembling a buffer) use the accumulate-and-convert pattern, so a large result is built with one allocation rather than rebuilt incrementally, and the fragile `+=` optimization is never relied upon on a path that must be fast.

---

## 74.4 Edges and failure modes

**`+=` on a string in a loop is fragile, not just slow.** §74.3.
CPython's in-place optimization degrades to O(n^2) if the string has another reference, and does not exist on PyPy/older Python. Use `"".join`, which is reliably O(n).

**For a few concatenations, `+=` is fine.** §74.2.
The pattern matters for *loops* over *many* pieces. A handful of concatenations is readable and fast enough; do not over-engineer small cases.

**`list + join` versus `generator + join`.** §74.3.
The list materializes all pieces (more memory, slightly faster); the generator streams them (less memory, slight per-item overhead). For huge results, the generator saves memory; for speed, the list wins. Choose by the memory/time trade.

**`join` needs an iterable of the right type.**
`"".join(x)` requires `x` to yield *strings*; a list of ints raises `TypeError`. Convert first (`"".join(str(i) for i in nums)`). `bytes.join`/`b"".join` for bytes.

**The mutable container's growth is amortized, not per-op, O(1).**
`list.append` is *amortized* O(1) (occasional reallocation), so building the list is O(n). But a single append that triggers reallocation is O(current size); the amortization holds over many appends. This is fine for accumulation.

**Do not confuse this with `list` mutation.**
Lists *are* mutable, so building a list incrementally (`append`) is already efficient, the pattern is for building *immutable* results. You do not need to "accumulate and convert" for a list you want to keep as a list.

**`io.StringIO` for very large or streaming text.**
For building very large text (or writing incrementally), `io.StringIO` (a mutable in-memory text buffer) can be cleaner than a list of pieces, `write` to it, `getvalue()` once. It is the file-like accumulator.

**f-strings and format for fixed structure.**
For assembling a string of *known* structure (not a loop), an f-string (Chapter 27) is fastest and clearest. The join pattern is for *variable-length* accumulation (a loop); f-strings for *fixed* templates.

---

## 74.5 Connections

**Backward.**
String immutability (and why it enables hashing/interning) is Deep A (Chapters 19, 23). The mutable-container over-allocation (why `list.append` is amortized O(1)) is Deep Q (`list` internals). The single-allocation principle connects to the allocator (Deep B). The "do the expensive thing once" theme is Chapters 54, 56, 73 (Deep H).

**Forward.**
`list`/`bytearray` internals and over-allocation growth policy are Deep Q. `io.StringIO`/`io.BytesIO` (in-memory buffers) are Deep R (IO). f-strings for fixed structure are Chapter 27. Text/bytes handling in depth is Deep D.

**Across books.**
The accumulate-and-convert pattern is a hot-path idiom in **Book I**: building a serialized message, a formatted log line, a wire-protocol buffer, or any large immutable result uses a mutable buffer materialized once, so a big output is one allocation rather than an incremental rebuild. The order-book system builds its outbound message buffers with `bytearray` (or `io.BytesIO`) accumulation converted to `bytes` once, and assembles text with `"".join`/`io.StringIO`, never `+=` in a loop on a hot path, so string/bytes building never becomes a quadratic surprise or relies on a fragile per-implementation optimization. Immutability's cost model, worked *with* via mutable accumulation, is the Deep H lesson applied to every place a program builds up an immutable result.

---

## 74.6 Exercises

**1. Immutability and join.** Reproduce §74.1: confirm string concatenation makes a new object, and build a string with `"".join(list)`. Explain why immutability forces `+=` to copy and how `join` avoids it.

**2. Measure it.** Reproduce §74.3. Confirm `join` beats `+=`. Then give the string being `+=`'d a second reference (append it to a list each iteration) and show `+=` degrade toward O(n^2). Explain the fragility of CPython's optimization.

**3. Generalize the pattern.** Build a `bytes` result with a `bytearray` and a `tuple` with a `list`, converting once, and contrast with `bytes +=` / `tuple +=` in a loop. Explain the mutable-then-convert principle.

**4. List versus generator join.** Compare `"".join(list)` and `"".join(genexpr)` on memory and time for a large result. Explain the trade-off.

**5. The design question.** Immutability makes strings hashable, shareable, and interned, but un-growable, so incremental building is costly. Argue why the accumulate-in-a-mutable-buffer-convert-once pattern is the right response, using §74.3, and why relying on CPython's `+=` optimization is fragile. When is `+=` acceptable?

---

## 74.7 Summary and cross-references

- **Strings are immutable**, so `s += x` cannot grow `s` in place; it conceptually builds a **new** string. In a loop this is (naively) **O(n^2)**. CPython has a **fragile** in-place-resize optimization (breaks with extra references, absent on PyPy/older Python).
- **The reliable, faster pattern:** accumulate pieces in a **mutable list** and materialize the immutable result **once** with **`"".join`** (which allocates the total size a single time). **Measured:** `join` is **2.6x** faster than `+=`.
- **The pattern generalizes:** build in the **mutable** type (`list`, `bytearray`, `set`) and convert to the **immutable** result (`str`, `bytes`, `tuple`, `frozenset`) **once**. Mutable containers over-allocate (amortized O(1) append); immutable ones cannot grow.
- **The rule:** do not grow an immutable object incrementally in a loop; accumulate and convert once. Use `join` for strings, `bytearray`->`bytes` for bytes, `list`->`tuple` for tuples.
- **Edges:** `+=` is fine for a few concatenations; `list`+`join` (speed) vs generator+`join` (memory); `join` needs the right element type; `io.StringIO`/`io.BytesIO` for very large/streaming builds; f-strings for fixed structure.

**Cross-references.** String immutability / hashing / interning → Chapters 19, 23 (Deep A). `list`/`bytearray` over-allocation → Deep Q. `io.StringIO`/`io.BytesIO` → Deep R. f-strings → Chapter 27. Do-the-expensive-thing-once theme → Chapters 54, 56, 73 (Deep H). Text/bytes → Deep D.
