# Chapter 55: Function Call Overhead

Chapter 54 established that calling a function creates a **frame**, the workspace holding that call's local variables and its position in the bytecode.
This chapter follows the consequence: because every call *builds a frame*, a call is not free.
The interpreter must allocate the frame, bind the arguments to its local slots, run the body, and tear the frame down on return, and that per-call machinery, measured at a few nanoseconds and about **1.5x** overhead for a per-iteration call, is negligible for ordinary code but real in a hot loop that calls a trivial function millions of times.

The frame-per-call model is also *why Python has the behaviours it does*: recursion works because each call gets an independent frame with its own copy of the parameters; closures capture per-call state because it lives in a frame; and the call stack has a **depth limit** (`RecursionError`) because each frame consumes memory and C stack, so unbounded recursion is turned into a catchable exception rather than a crash.
So this chapter is both a performance lesson (calls cost, frames are why) and a model lesson (recursion, closures, and the recursion limit all follow from frame-per-call).

**This is Deep H's call-model chapter.**
It builds on Chapter 54 (the frame) and explains a cost that motivates the rest of the volume: the specializing interpreter and JIT work partly to *reduce* call overhead, and vectorization (Deep T) sidesteps it by doing a whole loop in one call. It connects to recursion, closures (Deep F), and the recursion limit.

## Section index

- **55.1** Every call is a frame: recursion, locals, the limit
- **55.2** What a call costs, and when it matters
- **55.3** Measurement: the price of a frame
- **55.4** Edges and failure modes
- **55.5** Connections
- **55.6** Exercises
- **55.7** Summary and cross-references

Listings live under `code/ch136/` and are re-executed by `make verify` on both verification interpreters.

---

## 55.1 Every call is a frame: recursion, locals, the limit

```python
# code/ch136/l01_call_frames.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- every call pushes a NEW frame; recursion stacks them ---
  recurse(5) created this many extra frames : 6   (n=5..0 plus the counter)
--- each frame has its OWN locals: recursion computes correctly ---
  factorial(5) : 120   (each call's n is independent)
--- the call stack has a depth LIMIT (frames cost memory + C stack) ---
  sys.getrecursionlimit() is positive : True
--- unbounded recursion raises RecursionError, not a crash ---
  deep recursion raised RecursionError (caught, no crash) : True
--- the rule ---
  every call creates a frame with its own locals; that enables recursion
  and closures, bounds depth (RecursionError), and makes calls non-free
```

**Every call pushes a frame.**
`recurse(5)` produces a chain of frames, one per nested call (`n = 5, 4, 3, 2, 1, 0`), and counting the `f_back` chain confirms the recursion stacked them. The call stack literally grows one frame per call and shrinks one frame per return.

**Each frame has its own locals**, which is *why recursion works*.
`factorial(5)` is `120` because each recursive call's frame holds its *own* `n`, independent of every other call's, so the `n * factorial(n-1)` at each level multiplies the right value. If calls shared locals (one `n` for all), recursion would be impossible. The same per-frame locals are why a closure captures the state of the specific call that created it (Deep F).

**The stack has a depth limit.**
Because each frame consumes memory and C stack, CPython caps recursion depth (`sys.getrecursionlimit()`, default ~1000) and raises **`RecursionError`** when exceeded, turning what would be a C-stack overflow (a hard crash, undefined behaviour) into a *catchable Python exception*. The listing's `forever` recurses without bound and is caught cleanly. This limit is a safety feature: it trades the ability to recurse arbitrarily deep for the guarantee that runaway recursion fails gracefully.

So frame-per-call is not just a performance fact; it is the mechanism behind three language behaviours, recursion, closures, and the recursion limit, all of which follow from "each call gets its own frame with its own locals."

---

## 55.2 What a call costs, and when it matters

A frame is cheap but not free, and knowing the components tells you when the cost matters.

**What a call does:**

1. **Evaluate the arguments** and resolve the callable.
2. **Create a frame** for the call (allocate it, though CPython reuses/optimizes frame allocation heavily, notably the 3.11 "zero-cost" frame changes that made frames much cheaper).
3. **Bind the arguments** to the frame's local slots (positional, keyword, defaults, `*args`/`**kwargs` handling).
4. **Run the body's bytecode** in the frame.
5. **Tear down** the frame and return the value.

The overhead is steps 2, 3, and 5, the frame management and argument binding, on top of the actual work in step 4.
For a function that does *substantial* work, this overhead is a rounding error. For a *trivial* function (the body does almost nothing), the overhead can rival or exceed the work, which is the §55.3 result.

**When it matters:**

- **A trivial function called in a hot loop.** Calling `square(i)` a million times pays the frame cost a million times; inlining `i * i` avoids it. This is the case where call overhead is visible.
- **Deep call chains in a hot path.** Each layer of abstraction (a call that calls a call that calls...) adds a frame per level; in a hot path, deep delegation compounds the overhead.
- **Per-element callbacks.** A function called *per element* of a large collection (a `key=` function, a `map` callback, a comparator) pays the call cost per element, which is why `sorted(data, key=pyfunc)` is slower than sorting native-comparable data, and why NumPy (one call over the whole array) beats a Python element loop (Deep T).

**When it does NOT matter (the common case):**

- **Ordinary code.** A few nanoseconds per call is invisible next to any real work. Do not restructure normal code to avoid calls.
- **Functions that do real work.** If the body does meaningful computation or IO, the call overhead is negligible.

The rule, stated carefully to avoid the wrong lesson: **calls cost a little; that is a reason to be aware in *measured* hot loops, never a reason to inline everywhere.**
Functions are the primary tool of clarity and reuse, and trading readability for a few nanoseconds is almost always wrong.
Reach for inlining, reduced call depth, or vectorization *only* where a profiler shows a trivial call dominating a hot loop, exactly as the rest of Deep E and Deep M counsel "amortize the boundary": a Python call is a small boundary, cheap to cross occasionally, worth minimizing only when crossed millions of times in a measured hot path.

---

## 55.3 Measurement: the price of a frame

**Methodology.** `code/ch136/bench_call_overhead.py`.
The same computation via a per-iteration function call versus inlined, and the pure overhead of calling an empty function versus an empty loop iteration.
`min` of 5 runs.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 1000-iteration loop | time | |
|---|---|---|
| work via per-iteration call | 31.0 us | 1.0x |
| same work inlined | 21.7 us | **1.43x faster** |
| pure call overhead (`noop` vs `pass`) | | **~8 ns/call** |

Two numbers.
A per-iteration function call makes the loop **1.43x** slower than inlining the same work (1.54x on 3.14.6), and the pure overhead of calling an empty function is **~8 ns** (frame management plus argument binding, over an empty loop iteration).

Eight nanoseconds is genuinely small, that is the point.
CPython's 3.11 frame optimizations made calls much cheaper than they used to be, and for any function doing real work, 8 ns is invisible.
The 1.43x in the first row appears only because the *work* (`i * i`) is itself trivial, so the call overhead is a large *fraction* of a tiny total; give the function real work to do and the ratio collapses toward 1.0x.

So the measurement calibrates the lesson precisely.
**Call overhead is real but small**, so:

- **In ordinary code, ignore it.** Write functions freely; the clarity is worth far more than 8 ns.
- **In a measured hot loop over a trivial operation, it is one of the things to reduce**, by inlining the trivial body, flattening deep call chains, or, best, **vectorizing** so a *single* call does the whole loop in C (NumPy, Deep T) rather than a Python call per element. The per-element call overhead is a large part of *why* pure-Python numeric loops are slow and NumPy is fast: not just the interpreter per operation, but a *frame* per operation, versus one crossing for the whole array.

This is Deep H's second performance theme (after Chapter 54's "compile once"): the interpreter's per-call machinery has a cost, the specializing interpreter and JIT work to shrink it (inlining, avoiding frame setup for hot calls), and the durable escape for hot numeric work is to *not call per element at all*, the same "one crossing, whole buffer" rule as the C boundary (Chapter 44), now at the Python call boundary.

---

## 55.4 Edges and failure modes

**Do not inline for performance by default.** §55.2, §55.3.
8 ns per call is negligible in ordinary code. Inlining trades clarity for micro-speed; do it only where a profiler shows a trivial call dominating a hot loop.

**Recursion depth is limited.** §55.1.
Deep recursion hits `RecursionError` (~1000 by default). For deep or unbounded recursion, convert to iteration (an explicit stack/loop), which has no frame-depth limit. `sys.setrecursionlimit` raises the cap but risks a real C-stack crash if set too high.

**Python has no tail-call optimization.**
A tail-recursive call still creates a frame (Python does not reuse the frame for a tail call, by deliberate design, to keep tracebacks complete). So tail recursion does *not* avoid the depth limit; rewrite as a loop.

**Per-element callbacks pay per-call overhead.** §55.2.
`sorted(key=f)`, `map(f, xs)`, comparators, and filters call `f` per element. For large data, this dominates; prefer vectorized operations (Deep T) or native-comparable keys where possible.

**Argument binding adds cost.**
`*args`/`**kwargs`, keyword arguments, and defaults add to the per-call binding work versus simple positional arguments. In a measured hot path, a simpler signature is marginally cheaper, though rarely worth restructuring for.

**Frames pin their locals and stack.** (Chapter 54.)
A stored frame or traceback keeps its locals and the frames above it alive. Deep call chains captured in a stored traceback pin a lot; clear them.

**Method calls have extra steps.**
A method call adds attribute lookup and bound-method creation (Chapter 20, 32) on top of the frame cost. The specializing interpreter optimizes the common `obj.method()` pattern (`LOAD_METHOD`), but a method call is not identical to a plain function call.

**The overhead changed across versions.**
Frame costs dropped substantially in 3.11 (the "faster CPython" work) and continue to change with the specializing interpreter and JIT. Any specific nanosecond figure is version-specific; the *shape* (calls cost a little, matter in hot loops) is stable.

---

## 55.5 Connections

**Backward.**
The frame that each call creates is Chapter 54. Per-frame locals enabling recursion connect to closures and scope (Deep F). The recursion limit turning a crash into an exception is exceptions-as-control-flow. Method-call overhead adds Chapter 20's dispatch and Chapter 32's bound-method creation.

**Forward.**
The **specializing adaptive interpreter** (Chapter 17) and the **JIT** reduce call overhead (inlining hot calls, cheaper frames), the rest of **Deep H**. **Vectorization** (Deep T, Chapter 96) is the escape from per-element call overhead. **Generators/coroutines** (Deep F) are frames that *suspend and resume* instead of being torn down. Iterative-versus-recursive algorithm design connects to the recursion limit.

**Across books.**
Call-overhead awareness shapes **Book I**'s hot paths: a matching loop or a pricing kernel avoids trivial per-element function calls (inlining or vectorizing the inner operation), and deep abstraction layers are flattened *only* where profiling shows them dominating. The order-book system writes clear, well-factored code everywhere except the few measured hot loops, where it inlines trivial operations and, critically, vectorizes numeric work (one NumPy call over an array, not a Python call per tick), so the ~8 ns-per-call cost never accumulates on the critical path, the §55.3 rule applied with a profiler, not a reflex, keeping the code readable while removing the overhead exactly where it was measured to matter.

---

## 55.6 Exercises

**1. Frames and recursion.** Reproduce §55.1: confirm recursion stacks frames, each with its own locals, and that unbounded recursion raises `RecursionError`. Then rewrite a recursive function iteratively and show it has no depth limit. Explain why frame-per-call enables recursion but bounds its depth.

**2. Measure the call.** Reproduce §55.3. Confirm the ~8 ns per-call overhead and the ~1.4x for a trivial per-iteration call. Then give the function real work and show the ratio collapse toward 1.0x. Explain why the overhead is a large *fraction* only for trivial work.

**3. The callback cost.** Sort a large list with a trivial Python `key=` function and compare to sorting native-comparable data. Show the per-element call cost. Relate it to why NumPy beats a Python element loop.

**4. No TCO.** Write a tail-recursive function and show it still hits `RecursionError` (Python has no tail-call optimization). Rewrite as a loop. Explain why CPython deliberately keeps the frames.

**5. The design question.** CPython builds a frame per call (enabling recursion, closures, tracebacks) at a small per-call cost, and does *not* do tail-call optimization or automatic inlining. Argue the trade: what does frame-per-call buy, what does it cost, and why is "don't inline for performance by default" the right guidance given §55.3? How do the specializing interpreter and vectorization address the cost without changing your source?

---

## 55.7 Summary and cross-references

- **Every function call creates a frame** (Chapter 54): allocate it, bind arguments to its locals, run, tear down. This is why **recursion** works (each call's own locals), why **closures** capture per-call state, and why the stack has a **depth limit** (`RecursionError`, turning a C-stack overflow into a catchable exception).
- **Measured:** a per-iteration trivial call is **~1.43x** the inlined work, and pure call overhead is **~8 ns** (frame management + argument binding). Small in absolute terms, large only as a *fraction* of trivial work.
- **The rule:** call overhead is real but small, **ignore it in ordinary code** (functions are for clarity and reuse), and reduce it (inline, flatten, or **vectorize**) **only** in a measured hot loop over a trivial operation. Per-element callbacks pay it per element, which is why NumPy (one call per array) beats a Python element loop.
- **Edges:** no tail-call optimization (tail recursion still hits the limit, use a loop); deep recursion needs iteration; method calls add dispatch; frame costs are version-specific (dropped in 3.11), the shape is stable.

**Cross-references.** The frame → Chapter 54. Closures and per-frame state → Deep F. The specializing interpreter / JIT (reduce call cost) → Chapter 17, the rest of Deep H. Vectorization (escape per-element calls) → Chapter 96 (Deep T). Method dispatch / bound methods → Chapters 20, 32. The "amortize the boundary" rule → Chapters 44, 47, 48.
