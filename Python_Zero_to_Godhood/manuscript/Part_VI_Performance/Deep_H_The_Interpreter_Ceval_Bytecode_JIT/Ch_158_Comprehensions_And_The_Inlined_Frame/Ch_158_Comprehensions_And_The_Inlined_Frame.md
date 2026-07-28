# Chapter 77: Comprehensions and the Inlined Frame

For twenty years a list comprehension was a **function call in disguise**.
`[f(x) for x in xs]` compiled to a nested code object named `<listcomp>`; at runtime the interpreter built a function object from it, called it, pushed a frame, ran the loop, and returned. That is why the iteration variable did not leak, why `<listcomp>` appeared in tracebacks, and why a comprehension over an empty list still cost a function call.

PEP 709 (Python 3.12) **inlined** list, set, and dict comprehensions into the enclosing code object.
There is no nested code object, no function to build, no frame to push. The iteration variable becomes a hidden local of the *enclosing* function, saved and cleared around the comprehension so that it still does not leak.
Generator expressions were **not** inlined, and cannot be: a generator's whole purpose is to be suspended, and the thing that gets suspended is a frame.

Two constructs that differ by one pair of brackets in the source are now structurally different at runtime, and the gap is measurable at both ends: a **3.7x** difference in fixed cost and a **2.9x** difference at a thousand elements.

**This is a Deep H performance chapter.**
It is about what a comprehension actually compiles to now, what the inlining removed, and the scoping consequences that survived it.

## Section index

- **77.1** Four places the inlining is observable
- **77.2** What the inlining did not change
- **77.3** Measurement: fixed cost and per-element cost
- **77.4** Edges and failure modes
- **77.5** Connections
- **77.6** Exercises
- **77.7** Summary and cross-references

Listings live under `code/ch158/` and are re-executed by `make verify` on both verification interpreters.

---

## 77.1 Four places the inlining is observable

```python
# code/ch158/l01_comprehension_frames.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- which frame does the body run in? ---
  list comprehension   : which_frame
  set comprehension    : which_frame
  dict comprehension   : which_frame
  generator expression : <genexpr>
--- an inlined comprehension leaves no nested code object behind ---
  code objects in with_listcomp.co_consts : []
  code objects in with_genexpr.co_consts  : ['<genexpr>']
--- the iteration variable is a hidden local of the ENCLOSING function ---
  with_listcomp.co_varnames : ('xs', 'x')
  with_genexpr.co_varnames  : ('xs',)
--- and it still does not leak: the outer binding is restored ---
  x after [x for x in range(3)] : 'outer'
  the comprehension's result    : [0, 1, 2]
--- no <listcomp> frame on the traceback ---
  frames raising from inside a comprehension : ['failing_frames', 'boom']
--- in a class body, only the FIRST iterable sees class scope ---
  [v * 2 for v in vals]              : [2, 4, 6]
  [(a, b) for a in vals for b in vals] : NameError: name 'vals' is not defined
```

**The frame.**
`sys._getframe().f_code.co_name` evaluated inside a list, set, or dict comprehension names the *enclosing* function, `which_frame`. Evaluated inside a generator expression it names `<genexpr>`. This is the whole of PEP 709 in one measurement: three of the four constructs no longer have a frame of their own, and the fourth still does.

**The code object.**
`with_listcomp.__code__.co_consts` contains **no** nested code object. Before 3.12 it contained one, named `<listcomp>`, and the bytecode built a function from it and called it. `with_genexpr.__code__.co_consts` still contains `<genexpr>`, because the generator's body has to exist as separate code that can be entered, suspended, and re-entered.

**The hidden local.**
`with_listcomp.__code__.co_varnames` is `('xs', 'x')`. The iteration variable `x` is a genuine local of the enclosing function, allocated a slot in its frame's local array (Chapter 75). `with_genexpr.__code__.co_varnames` is `('xs',)`, because its `x` lives in the generator's own frame.

**And yet `x` does not leak.**
`no_leak` binds `x = "outer"`, runs `[x for x in range(3)]`, and `x` is still `"outer"` afterwards. If the iteration variable is a real local of the enclosing frame, something must protect the pre-existing binding. That something is the `LOAD_FAST_AND_CLEAR` opcode introduced with PEP 709: it pushes the slot's current value onto the stack and clears the slot, the comprehension runs using the slot freely, and the saved value is stored back at the end (including on the exception path, which is why the comprehension's bytecode carries a small exception table). The non-leaking semantics of Python 3 were preserved by a save-and-restore rather than by a separate scope.

**The traceback.**
An exception raised inside a comprehension used to show a `<listcomp>` frame between the raising line and its caller. It no longer does: the frames are `['failing_frames', 'boom']` and nothing else. This is the observable that matters most in practice, because it is what makes profiler output and traceback reading different on 3.12+ from every tutorial written before it.

**The class-scope survivor.**
In a class body, `[v * 2 for v in vals]` works and `[(a, b) for a in vals for b in vals]` raises `NameError: name 'vals' is not defined`. The rule is that the **first** (outermost) iterable is evaluated eagerly in the enclosing scope, and every subsequent iterable is evaluated inside the comprehension, which does not see class scope. That asymmetry predates PEP 709 and survived it unchanged, because inlining changed the frame, not the name-resolution rules the compiler applies to comprehension bodies.

---

## 77.2 What the inlining did not change

It is easy to read "comprehensions are inlined" as "comprehensions are now just loops", and three things stop that from being true.

**The scope is still a scope, for name resolution.**
The body of a comprehension still cannot see class-level names (§77.1), and a name assigned in the body is still not visible after it. What PEP 709 removed was the runtime *frame*, not the compile-time scope. The compiler resolves the body's names as it always did and then arranges to execute the result in the enclosing frame with the iteration variables save-and-restored. The observable consequence is that the class-body `NameError` above is unchanged, which surprises people who expected inlining to fix it.

**A generator expression is a different construct, not a lazy comprehension.**
`(x for x in xs)` is not `[x for x in xs]` with laziness bolted on; it is an object that owns a frame and a suspension point. The frame is what `yield` suspends. This is why it could not be inlined, and why it costs what §77.3 measures. The practical consequence is the reverse of the common advice: for a collection you are going to materialize anyway, and especially for a small one, the generator expression is the slower choice, not the more efficient one.

**Inlining is not vectorization.**
The comprehension still executes one bytecode sequence per element, and Chapter 76's count applies to it unchanged. PEP 709 removed a *fixed* cost per comprehension and a small per-element cost; it did not remove the per-element interpreter cost, and it did not turn the comprehension into a C loop. `list(xs)`, which is a C copy, is still four to five times faster than `[x for x in xs]`.

**What it did change, stated plainly.**
A comprehension no longer costs a function call, so the shape of code that uses many small comprehensions, a comprehension inside a loop, a comprehension per row of a table, a comprehension in a `__init__` that runs per object, got materially cheaper without anyone editing it. That is the class of program PEP 709 was aimed at, and §77.3's fixed-cost table is where it shows.

---

## 77.3 Measurement: fixed cost and per-element cost

**Methodology.** `code/ch158/bench_comprehension.py`.
Both verification interpreters are post-PEP-709, so this cannot measure the 3.11-to-3.12 change directly. It measures what PEP 709 removed by comparing against the construct that still pays it, the generator expression. Every case is wrapped in a function of the same shape so the one Python call per measurement is common to all rows and cancels from the ratios. `min` of 15 batches at 200,000 calls (fixed cost) and 9 batches at 2,000 calls (bulk).
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**Fixed cost, over an empty iterable.** No body runs; what is left is setup.

| construct, empty input | time | vs list comprehension |
|---|---|---|
| list comprehension | 35 ns | 1.00x |
| dict comprehension | 36 ns | 1.02x |
| set comprehension | 46 ns | 1.3x |
| `for` loop with `.append` | 32 ns | 0.90x |
| `list(genexpr)` | 131 ns | **3.7x** |

The generator expression costs nearly **four times** the inlined comprehension to do nothing at all. That 96 ns gap is the function object, the generator object, and the frame, exactly the costs PEP 709 removed from the other three. The set comprehension's 1.3x is not frame cost; it is the set's larger initial allocation and its hash-on-insert path, which is Deep Q's subject.

The row worth pausing on is the `for` loop at **0.90x**: an explicit empty loop is about 10% *cheaper* than an empty comprehension. The comprehension's save-and-restore of the iteration variable (§77.1) is real work, and with no elements to amortize it over, it loses. This inverts at any realistic size.

**Per-element cost, over 1,000 elements.**

| construct, 1,000 elements | time | vs list comprehension |
|---|---|---|
| `list(xs)` (C copy) | 1.1 us | **0.23x** |
| list comprehension | 4.9 us | 1.00x |
| `for` loop with `.append` | 7.8 us | 1.6x |
| `list(genexpr)` | 14.0 us | **2.9x** |

The generator's fixed 96 ns is now a rounding error; its 2.9x comes from suspending and resuming a frame once per element. The explicit loop's 1.6x is the `LOAD_ATTR append` and the `CALL` per element that the comprehension's `LIST_APPEND` opcode does not need. And `list(xs)` at 0.23x is Chapter 76's point restated: the fastest loop is the one that runs in C.

**Reading the two tables together.**
The comprehension wins the bulk case on per-element instructions and the empty case on setup, and it loses the empty case to a plain loop by a hair. So the guidance falls out cleanly. Use a comprehension when you want a list; it is the fastest Python-level form at every size that matters. Use a generator expression when the point is *not materializing* the sequence, streaming, early exit, or a collection too large for memory, and accept a factor of roughly three when you do materialize it. Use `list()`, `sum()`, `"".join()` and friends when a C-level operation expresses the whole thing.

**Book I**'s side of the shared system never has this decision to make: a C++ range algorithm has no frame per element and no fixed cost to remove. The Python side's equivalent lever is choosing the construct whose per-element bytecode is smallest, and after PEP 709 that is the comprehension, which is a rare case of the most readable form also being the fastest one.

---

## 77.4 Edges and failure modes

**Tracebacks and profiles changed shape in 3.12.** §77.1.
An exception from inside a comprehension no longer shows a `<listcomp>`, `<setcomp>`, or `<dictcomp>` frame. Profilers attribute the comprehension's time to the enclosing function. Tooling and documentation written before 3.12 that keys on those frame names is wrong on current Python, and any assertion in a test suite that matches a traceback containing `<listcomp>` broke silently on upgrade.

**The class-body `NameError` is unchanged.** §77.1.
Only the outermost iterable is evaluated in the enclosing scope. `[x for x in a for y in b]` inside a `class` body sees `a` and not `b`. The fix is to bind what you need to a local first, or to move the computation out of the class body.

**A generator expression cannot be inlined, so `genexpr` advice inverts for small inputs.** §77.3.
`sum(x for x in small_list)` pays 131 ns of setup before it does anything. `sum(small_list)` or a comprehension is faster. The generator earns its cost when the sequence is large, lazy, or infinite.

**The generator expression is the only bracketed form that still owns a frame.**
It is tempting to assume anything suspendable falls back to a hidden function, and that is not what happens. An **async comprehension** (`[x async for x in agen]`) *is* inlined: on both 3.13.5 and 3.14.6 its enclosing function's `co_consts` contains no nested code object, because the `await` suspends the enclosing coroutine's frame, which already exists. And a comprehension containing `yield` is not a runtime question at all: it has been a `SyntaxError` since 3.8 (`'yield' inside list comprehension`). So the line is exactly where §77.1 draws it, generator expressions on one side, every comprehension form on the other.

**`locals()` inside a comprehension changed meaning.**
Because the body runs in the enclosing frame, `locals()` inside an inlined comprehension returns the enclosing function's locals, including the comprehension's iteration variable. Before 3.12 it returned the hidden function's locals. Code that introspected `locals()` from inside a comprehension, rare but real in template engines and debuggers, behaves differently.

**The iteration variable occupies a slot even when the comprehension does not run.**
`co_varnames` grows by one name per comprehension iteration variable in the enclosing function. This is invisible in practice but does mean a function containing many comprehensions has a larger local array, and that two comprehensions in one function using the same variable name share one slot, each save-and-restoring around its own body.

**Do not rewrite a loop as a comprehension for the 1.6x.** §77.3.
It is a real factor and it is the right default for building a list, but a loop that does several things per element does not become a comprehension without becoming unreadable. The measurement supports "prefer a comprehension when it is natural", not "convert every loop".

---

## 77.5 Connections

**Backward.**
The local array that the iteration variable now lives in, and the `LOAD_FAST` family that reads it, are Chapter 75. The per-element instruction count that the comprehension does *not* escape is Chapter 76. The frame and the call that PEP 709 removed are Chapter 55. The code object that no longer contains a `<listcomp>` constant is Chapter 54.

**Forward.**
The dispatch loop that charges per instruction regardless of which construct emitted it is Chapter 78. Generators, coroutines, and what a suspended frame actually holds are Deep F. `set` and `dict` construction costs, which explain the set comprehension's 1.3x, are Deep Q. Class-body execution and why it is not a closure scope are Deep C. PEP 709 as a release event, and the rest of what 3.12 did to scopes, is Volume 16.

**Across books.**
This chapter is the clearest case in the book of a language change that made existing code faster with no source edit, which is the kind of change **Book I**'s readers get from a compiler upgrade and Python readers usually do not. The shared order-book system builds per-tick lists with comprehensions rather than loops, which after 3.12 costs one function call less per tick than the same source cost on 3.11.

---

## 77.6 Exercises

**1. Find the frame.** Reproduce §77.1's first block. Then add an async comprehension inside an `async def` and report whether its enclosing function carries a nested code object. Explain why `await` does not force a hidden function back, and why `yield` in the same position is a `SyntaxError` rather than a slower comprehension.

**2. Watch the save-and-restore.** Disassemble a function containing `[x for x in range(3)]` and find `LOAD_FAST_AND_CLEAR`. Explain what it saves, when it is restored, and why the comprehension's bytecode needs an exception-table entry.

**3. Reproduce the inversion.** Reproduce §77.3's two tables. Find the input size at which the explicit loop stops being cheaper than the comprehension. Explain the crossover in terms of fixed cost versus per-element cost.

**4. The class-body rule.** Write a class body containing a two-iterable comprehension, observe the `NameError`, then fix it three ways: bind a local first, use a `staticmethod`, and move it out of the class. Say which you would ship and why.

**5. Break a traceback assertion.** Write a test that asserts on a traceback from inside a comprehension in the way a pre-3.12 test would have. Explain exactly what changed and what the version-robust assertion looks like.

**6. The design question.** PEP 709 preserved non-leaking semantics with a save-and-restore rather than by keeping a real scope. Argue the alternative: what would break if the iteration variable simply leaked, as it did in Python 2, and what the save-and-restore costs when the comprehension is empty (§77.3 measures it).

---

## 77.7 Summary and cross-references

- Before 3.12, a list/set/dict comprehension compiled to a **hidden function**: a nested code object, a function object built at runtime, a call, and a frame. **PEP 709 (3.12) inlined all three** into the enclosing code object.
- **Four observables:** `sys._getframe()` inside a comprehension names the *enclosing* function; `co_consts` holds no nested code object; the iteration variable appears in the enclosing function's `co_varnames`; and no `<listcomp>` frame appears on a traceback.
- **The variable still does not leak**, because `LOAD_FAST_AND_CLEAR` saves and restores the enclosing slot around the body, including on the exception path.
- **Generator expressions were not inlined and cannot be**: a generator must own a frame, because a frame is what gets suspended.
- **What did not change:** the comprehension body is still a *scope* for name resolution, so the class-body `NameError` on the second and later iterables survives; and inlining is not vectorization, the per-element bytecode of Chapter 76 still applies.
- **Measured on 3.13.5.** Fixed cost over an empty iterable: list comprehension 35 ns, dict 36 ns, set 46 ns, plain loop 32 ns (**0.90x**, cheaper, the save-and-restore has nothing to amortize over), `list(genexpr)` 131 ns (**3.7x**). Over 1,000 elements: comprehension 4.9 us, plain loop 7.8 us (**1.6x**), `list(genexpr)` 14.0 us (**2.9x**), `list(xs)` 1.1 us (**0.23x**).
- **Guidance:** comprehension when you want the list, generator expression when the point is not materializing it, a C-level builtin when one expresses the whole operation.
- **Edges:** traceback and profile shape changed in 3.12; `locals()` inside a comprehension now returns the enclosing frame's locals (plus the iteration variable); **async comprehensions are inlined too**, verified on both interpreters, and `yield` inside a comprehension is a `SyntaxError`, not a slow path.

**Cross-references.** Local slots and `LOAD_FAST` → Chapter 75. Per-element instruction cost → Chapter 76. Frames and calls → Chapter 55. Code objects → Chapter 54. Dispatch → Chapter 78. Generators and suspension → Deep F. `set`/`dict` construction → Deep Q. Class-body scope → Deep C. PEP 709 as a release event → Volume 16.
