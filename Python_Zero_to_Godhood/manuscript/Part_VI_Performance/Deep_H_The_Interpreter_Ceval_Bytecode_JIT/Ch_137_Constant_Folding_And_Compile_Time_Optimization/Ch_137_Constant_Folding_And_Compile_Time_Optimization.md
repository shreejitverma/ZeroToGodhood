# Chapter 56: Constant Folding and Compile-Time Optimization

Chapter 54 showed that `def` compiles a function into a code object *once*.
This chapter is about what the compiler *does* during that one compilation beyond a literal translation: it **optimizes**.
The most visible optimization is **constant folding**, evaluating expressions made entirely of constants at compile time and storing the *result*.
`60 * 60 * 24` never multiplies anything at runtime; the compiler computes `86400` while compiling and emits a single `LOAD_CONST`.
`"ab" * 3` becomes `"ababab"`; `(1, 2, 3)` becomes one constant tuple.

This has a lovely practical consequence that the measurement confirms: **you can write readable constant expressions for free.**
`60 * 60 * 24` is exactly as fast as the opaque magic number `86400`, and far clearer, so "seconds per day" written as a factored expression costs nothing (the folded version is **1.84x** faster than the same value computed from *variables*, which cannot be folded).
The compiler rewards clarity here.
But the boundary matters: folding applies only to *constants*. An invariant computation involving *variables* is **not** folded and runs every iteration, which is where *you* must still hoist loop-invariant code yourself.

**This is Deep H's compile-time-optimization chapter.**
It complements Chapter 54 (the compiler produces the code object), distinguishes compile-time optimization from the *runtime* specializing interpreter (Chapter 17), and sets the boundary of what the compiler does versus what you must do.

## Section index

- **56.1** What the compiler folds
- **56.2** The boundary: constants versus variables
- **56.3** Measurement: folded versus computed
- **56.4** Edges and failure modes
- **56.5** Connections
- **56.6** Exercises
- **56.7** Summary and cross-references

Listings live under `code/ch137/` and are re-executed by `make verify` on both verification interpreters.

---

## 56.1 What the compiler folds

```python
# code/ch137/l01_constant_folding.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- arithmetic on constants is folded to the result ---
  86400 is in seconds_per_day's co_consts : True
  seconds_per_day() == 86400              : True
--- string and tuple constants are folded too ---
  'ababab' in repeated_str's co_consts    : True
  (1, 2, 3) in const_tuple's co_consts    : True
--- but an expression with a VARIABLE is not fully folded ---
  with_variable still references 60 (runtime multiply) : True
  with_variable(2) == 7200                : True
--- the rule ---
  the compiler folds constant expressions to their result (free at
  runtime); write readable constant expressions, only variables run live
```

**Constant folding** evaluates any expression whose operands are all constants, at compile time, and puts the *result* in the code object's constant table (`co_consts`, Chapter 54):

- **Arithmetic:** `60 * 60 * 24` is folded to `86400` (it is *in* `co_consts`), so `seconds_per_day` at runtime does a single `LOAD_CONST 86400`, no multiplication.
- **Strings:** `"ab" * 3` is folded to `"ababab"`.
- **Tuples of constants:** `(1, 2, 3)` is folded to a single constant tuple object (built once, reused).

The compiler does this during the one compilation of the function (Chapter 54), so the cost is paid *never at runtime*, the multiplication happened while compiling.
This is why the folded expression appears as its *result* in `co_consts`: the source `60 * 60 * 24` has been replaced, in the compiled code, by the number `86400`.

The compiler does more than folding, too: it eliminates dead code (an `if False:` branch is dropped), simplifies some jumps, and interns constants (Chapter 19), a suite of **peephole** and AST-level optimizations that clean up the bytecode.
But folding is the one with a clear, observable, version-stable effect (the result in `co_consts`) and a direct payoff for how you write code.

---

## 56.2 The boundary: constants versus variables

The listing's last block draws the crucial line, and it is where the compiler's help stops and yours begins.

`with_variable(x)` computes `x * 60 * 60`, and because `x` is a **variable**, the whole expression cannot be folded to a single constant, the value depends on `x`, unknown at compile time.
(The compiler may fold the constant *subexpression* `60 * 60` to `3600`, but the `x *` multiplication runs at runtime, every call.)
So the boundary is:

- **All-constant expressions are folded** to their result, free at runtime.
- **Any expression involving a variable is computed at runtime**, every time it executes.

This has two practical implications.

**Write readable constant expressions freely.**
Because `60 * 60 * 24` folds to `86400`, prefer the *factored, self-documenting* form over a magic number: `TIMEOUT = 5 * 60` (five minutes) is clearer than `300` and compiles to the same constant. `BUFFER = 64 * 1024` beats `65536`. The compiler makes the readable form free, so there is never a performance reason to write the opaque literal.

**Hoist loop-invariant *variable* computations yourself.**
The compiler does *not* do loop-invariant code motion for variable expressions.
If a loop repeatedly computes `x * scale * factor` where none change in the loop, the compiler runs it every iteration, so *you* must hoist it: compute `k = x * scale * factor` once *before* the loop and use `k` inside.
This is a real optimization the compiler leaves to you, and the §56.3 measurement shows what it costs when you do not: the variable version is ~1.8x the folded one because it recomputes.

So the division of labour is: **the compiler folds constants; you hoist invariant variable computations.**
Knowing this boundary tells you exactly which optimizations are automatic (write constants clearly, they fold) and which are manual (move invariant variable work out of loops).
It also corrects a common misconception, that "the compiler optimizes everything", or its opposite, "I must precompute every constant". Neither: constants are handled, variables are not.

---

## 56.3 Measurement: folded versus computed

**Methodology.** `code/ch137/bench_folding.py`.
A loop summing `60 * 60 * 24` (compile-time folded to `LOAD_CONST 86400`) versus a loop summing `a * b * c` from variables (computed each iteration).
`min` of 5 runs.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 1000-iteration loop | us | vs folded |
|---|---|---|
| folded constant (`60*60*24`) | 15.7 | 1.0x |
| runtime compute (`a*b*c`) | 29.0 | **1.84x** |

The folded loop is **1.84x** faster (1.77x on 3.14.6), because it does a single `LOAD_CONST` per iteration while the variable loop does two multiplications.
The value computed is identical; the difference is entirely *when* it is computed, once at compile time (folded) versus every iteration (variables).

The two lessons are the §56.2 boundary in numbers.

**Constant expressions are free, so favour clarity.**
`60 * 60 * 24` costs exactly what `86400` costs (they compile to the same `LOAD_CONST`), so write the meaningful expression. There is no performance argument for magic numbers; the readable factored form is both clearer and equally fast. This is a rare, pure win: the compiler makes the better-written code identical in speed to the worse-written code.

**Loop-invariant variable code is your job.**
The 1.84x is the cost of *not* hoisting an invariant computation out of a loop. The compiler will not move `a * b * c` out for you (it cannot prove `a`, `b`, `c` are invariant in general), so if a variable computation does not change across loop iterations, compute it once before the loop. This is the most common form of the optimization the compiler leaves to you, and it is worth doing in a measured hot loop (though, as always, not worth obscuring ordinary code for).

This is Deep H's third performance theme.
Chapter 54 was "compile once" (amortize compilation), Chapter 55 was "calls cost a frame" (amortize the call boundary), and this is "the compiler folds constants but not variable-invariants" (know the boundary of automatic optimization).
Together they map what CPython optimizes *for* you (compilation caching, constant folding) versus what remains *your* responsibility (hoisting invariants, reducing hot-loop calls, vectorizing), which is exactly the knowledge that lets you write clear code everywhere and optimize precisely where measurement demands.

---

## 56.4 Edges and failure modes

**Folding applies only to constants.** §56.2.
An expression with a variable is not folded and runs at runtime. Do not assume the compiler precomputes anything involving a variable.

**The compiler does not hoist loop invariants.** §56.2, §56.3.
Invariant *variable* computations run every iteration. Hoist them out of the loop yourself where it matters (measured hot loop).

**Very large folded constants can bloat the bytecode.**
Folding `10 ** 100000` produces a gigantic integer *constant* stored in the code object (and computed at compile time, slowing compilation). CPython limits some folding to avoid this. Do not rely on folding arbitrarily large or expensive constant expressions.

**Folding is compile-time, not runtime specialization.** §56.5.
Constant folding is done once by the compiler; the *specializing adaptive interpreter* (Chapter 17) is a separate, *runtime* optimization that adapts bytecode to the types it observes. Do not conflate them.

**A tuple of constants is folded but a list is not.**
`(1, 2, 3)` folds to a constant tuple (immutable, safe to reuse); `[1, 2, 3]` is *not* folded to a constant (a list is mutable, so each execution must build a fresh one). This is why a constant tuple is cheaper than a constant-looking list.

**Named constants at module level are not folded into other functions.**
`SECONDS = 86400` then `x * SECONDS` in a function references `SECONDS` as a *global* (a name lookup), not a folded constant, because the compiler compiles the function without knowing the module global's value. Folding needs the constants *in the expression*, not behind a name.

**`from __future__` and semantics can affect folding.**
Folding must preserve semantics exactly (a folded result must equal the runtime result), so the compiler is conservative, it will not fold where the result could differ (e.g. float rounding edge cases, or operations that could raise). Do not assume every constant expression is folded.

---

## 56.5 Connections

**Backward.**
Folded constants live in `co_consts` (Chapter 54, the code object). Constant interning (a folded constant shared) is Chapter 19. Folding happening once at compile time is the "compile once" of Chapter 54. The readability-is-free lesson complements the naming and clarity defaults throughout.

**Forward.**
The **specializing adaptive interpreter** (Chapter 17) is the *runtime* counterpart, optimizing based on observed types where the compiler cannot. The **JIT** compiles hot code to machine code (further optimization). Loop-invariant hoisting and vectorization (Deep T) are the manual optimizations the compiler leaves to you. The `.pyc` cache (Chapter 66) stores the *optimized* bytecode across runs.

**Across books.**
The "readable constants are free" rule shapes **Book I**'s code: time constants (`60 * 60 * 24` for a day, `252` trading days folded into rate calculations), buffer sizes (`64 * 1024`), and unit conversions are written as *factored, self-documenting* expressions, not magic numbers, at zero runtime cost. And the "hoist invariant variable computations" rule is applied in the hot paths: a matching or pricing loop computes its loop-invariant terms once before the loop, not per iteration, exactly the §56.3 optimization, so the order-book system reads clearly (folded constant expressions everywhere) *and* runs fast (hoisted invariants in the measured hot loops), the compiler handling the constants and the engineer handling the variable-invariants, precisely as this chapter divides the labour.

---

## 56.6 Exercises

**1. See the fold.** Reproduce §56.1: confirm `60 * 60 * 24`, `"ab" * 3`, and `(1, 2, 3)` appear as their results in `co_consts`, and that a variable expression does not fully fold. Use `dis` to see the `LOAD_CONST`. Explain what the compiler did.

**2. Constants are free.** Reproduce §56.3. Confirm the folded constant beats the variable computation. Then replace the folded expression with the magic number `86400` and show identical speed. Argue for readable constant expressions over magic numbers.

**3. Hoist the invariant.** Write a loop that recomputes an invariant *variable* expression every iteration, measure it, then hoist the computation out and re-measure. Explain why the compiler could not do this for you.

**4. Tuple versus list.** Show that a constant tuple `(1, 2, 3)` is folded (in `co_consts`) but a constant-looking list `[1, 2, 3]` is not (built each execution). Explain why mutability prevents folding the list.

**5. The design question.** The compiler folds constants but does not hoist loop-invariant variable computations. Argue why the line is drawn there (what can the compiler *prove*?), and how this divides optimization labour between the compiler (constants) and the engineer (invariants, calls, vectorization). Relate it to the runtime specializing interpreter (Chapter 17), which optimizes what the compiler cannot.

---

## 56.7 Summary and cross-references

- The compiler **folds constant expressions** at compile time, storing the *result* in `co_consts`: `60 * 60 * 24` becomes `86400`, `"ab" * 3` becomes `"ababab"`, `(1, 2, 3)` becomes one constant tuple. This is a **compile-time** optimization (once, per Chapter 54), distinct from the runtime specializing interpreter (Chapter 17).
- **The boundary:** all-constant expressions fold (free at runtime); any expression with a **variable** is computed at runtime. So **write readable constant expressions freely** (`60 * 60 * 24` equals `86400` in speed, and is clearer), but **hoist loop-invariant *variable* computations yourself** (the compiler will not).
- **Measured:** a folded constant is **1.84x** faster than the same value computed from variables in a loop, the cost of *not* folding (variables) or *not* hoisting.
- **The division of labour:** the compiler handles constants (folding, dead-code elimination, interning); you handle invariant variable computations, hot-loop call reduction, and vectorization.
- **Edges:** lists are not folded (mutable); named module constants are globals, not folded into functions; very large folded constants bloat bytecode; folding is conservative (preserves semantics exactly).

**Cross-references.** The code object and `co_consts` → Chapter 54. Constant interning → Chapter 19. The runtime specializing interpreter → Chapter 17, the rest of Deep H. Vectorization (a manual optimization) → Chapter 96 (Deep T). The `.pyc` cache (stores optimized bytecode) → Chapter 66.
