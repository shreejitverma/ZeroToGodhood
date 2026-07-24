# Chapter 3: Comprehensions, Nested Scopes, and Cyclic GC (Python 2.0-2.1)

Here is a function that returns the wrong answer, and a version that returns the right one, and the
only difference is three characters:

```python
callbacks = [lambda: i for i in range(3)]
print([f() for f in callbacks])        # [2, 2, 2]  -- not what anyone wanted

callbacks = [lambda i=i: i for i in range(3)]
print([f() for f in callbacks])        # [0, 1, 2]  -- correct
```

Every Python programmer writes the first version at least once, usually while building a list of
event handlers or partially-applied functions, and every one of them is briefly certain the
interpreter is broken. It is not. The bug is a direct consequence of how closures capture variables,
which is a consequence of how nested scopes work, which is a consequence of decisions made in Python
2.0 and 2.1. This chapter follows that chain to its end, and in the process explains the second thing
those releases introduced: a garbage collector that exists for one reason only, to clean up after the
first thing.

The three features, list comprehensions (2.0), lexically nested scopes (PEP 227, 2.1), and the cyclic
collector (2.0), look like conveniences and are in fact deep statements about the execution model.
This chapter treats them at their modern depth, including the two changes, PEP 709 comprehension
inlining (3.12) and PEP 442 finalization (3.4), that make the original 2.x descriptions obsolete.

## Section index

- **3.1** List comprehensions: the leak, the fix, and PEP 709 inlining
- **3.2** Nested scopes and LEGB resolution (PEP 227)
- **3.3** Closures, cells, and the late-binding trap
- **3.4** The cyclic garbage collector
- **3.5** Measurement: when disabling the collector helps, and when it hurts
- **3.6** Edges and failure modes
- **3.7** Connections
- **3.8** Exercises
- **3.9** Summary and cross-references

Listings live under `code/ch003/` and are re-executed by `make verify` on both interpreters.

---

## 3.1 List comprehensions: the leak, the fix, and PEP 709 inlining

**Why this exists.** A list comprehension is sugar for "build a list by iterating," but *where the
loop variable lives* turned out to be a subtle, evolving design decision that touches frames,
isolation, and performance.

**The original leak (Python 2.x).** Python 2.0 compiled a comprehension as an inline loop in the
enclosing function; the loop variable was written straight into the host's locals and leaked out:

```python
# Python 2.x behaviour, historical. NOT how Python 3 works.
x = 999
data = [x for x in range(5)]
print(x)   # -> 4 in Python 2: the comprehension clobbered the outer x
```

This is not runnable on a modern interpreter, and this book does not pretend otherwise; it is quoted
from the 2.x semantics, and the listing below shows what actually happens now.

**The fix (Python 3.0), then the re-fix (PEP 709, 3.12).** Python 3.0 gave each list, set, and dict
comprehension its own scope by compiling it as an implicit nested function. The loop variable became
local to that hidden function and stopped leaking. But a function frame per comprehension is pure
overhead, so PEP 709 inlined them back into the enclosing code object in 3.12, preserving isolation by
*saving and restoring* the loop variable instead of creating a scope. The proof that the frame is
gone is that an inlined comprehension leaves no nested code object, while a generator expression,
which must suspend and genuinely needs its own frame, still does:

```python
# code/ch003/l01_comprehension_isolation.py
def make_list(n):
    return [i * i for i in range(n)]

def make_gen(n):
    return (i * i for i in range(n))
```

Verified output (CPython 3.13.5):

```text
--- isolation: the outer x is untouched (since 3.0) ---
  x after comprehension: 999
  data: [0, 1, 2, 3, 4]

--- PEP 709: the list comprehension has no nested code object ---
  nested code objects in make_list: []
  nested code objects in make_gen:  ['<genexpr>']
  the generator still gets its own frame because it suspends.
```

The save/restore mechanism is visible in the inlined bytecode as `LOAD_FAST_AND_CLEAR` on entry
(stash the outer name and blank its slot) with a matching restore threaded into the code object's
exception table, so the outer name survives even if the comprehension raises.

**Old-versus-new, three eras.** 2.x: inline, leaks. 3.0 through 3.11: hidden function frame, isolated
but slower. 3.12+: inlined with save/restore, isolated *and* fast. The user-visible semantics,
isolation, has held since 3.0; only the mechanism changed, and it was re-engineered twice. The
lasting lesson: **a comprehension's loop variable does not leak, but the reason has moved.**

---

## 3.2 Nested scopes and LEGB resolution (PEP 227)

**Why this exists.** Before Python 2.1, name lookup was three-tier, **LGB**: Local, Global, Built-in.
A nested function could not see its enclosing function's locals, so this raised `NameError`:

```python
# Pre-2.1 behaviour, historical.
def outer():
    x = 10
    def inner():
        return x        # NameError before PEP 227: x is neither local, global, nor builtin
    return inner
```

The workaround was to smuggle the value through a default argument, `def inner(x=x):`, which is the
same trick §3.3's bug fix uses and is not a coincidence. **PEP 227** (optional in 2.1 via
`from __future__ import nested_scopes`, standard in 2.2) inserted the **Enclosing** scope, giving the
modern **LEGB** order:

| Tier | Searches | Opcode (3.13) |
|---|---|---|
| **L**ocal | the active frame's fast-locals array | `LOAD_FAST` |
| **E**nclosing | cells captured from outer functions | `LOAD_DEREF` |
| **G**lobal | the module `__dict__` | `LOAD_GLOBAL` |
| **B**uilt-in | the `builtins` namespace | `LOAD_GLOBAL` (falls through after globals) |

The critical fact: **LEGB is resolved statically by the compiler** (Chapter 2's symbol-table pass),
not by searching dictionaries at runtime. The opcode chosen *is* the lookup decision. A local is a
fast-locals read, a free variable is a cell dereference, a global is a global load; only module-top-
level and dynamic scopes fall back to the dictionary-based `LOAD_NAME`.

```python
# code/ch003/l02_legb_in_opcode.py
def fast_local_demo(x):
    y = x + 1
    return y
```

Verified output (CPython 3.13.5):

```text
bytecode of fast_local_demo (loads and stores):
  LOAD_FAST  x
  STORE_FAST  y
  LOAD_FAST  y
```

Both `x` and `y` resolve through the fast-locals array, no dictionary involved. (On 3.14 these read
`LOAD_FAST_BORROW`, the borrowed-reference variant from Chapter 2; the scope *class* is the point, not
the spelling, and both interpreters' output is recorded.)

---

## 3.3 Closures, cells, and the late-binding trap

**Why this exists.** When `inner` reads `outer`'s local `x`, that local must outlive `outer`'s frame.
Chapter 2 introduced the solution: the compiler promotes `x` to a **cell** (`PyCellObject`), a heap
box shared by reference between the two functions. Here the mechanism becomes observable, and the bug
it causes becomes explicable.

```python
# code/ch003/l03_late_binding.py
def outer_scope(multiplier):
    secret_value = 100
    def inner_scope(val):
        return val * multiplier + secret_value   # two free variables
    return inner_scope
```

Verified output (CPython 3.13.5):

```text
--- closure cells are live, shared boxes, inspectable at runtime ---
  closure cells: [5, 100]
  inner co_freevars: ('multiplier', 'secret_value')
  outer co_cellvars: ('multiplier', 'secret_value')
```

The compiler emits `MAKE_FUNCTION` with the captured cells in the enclosing function, bundling them
into the new function's `__closure__`, and `LOAD_DEREF` inside the closure to read through a cell.

Now the trap from the chapter opening, explained. Because a cell holds a *reference to a live
variable*, not a snapshot, closures created in a loop all share the *same* cell and therefore all see
the loop variable's final value:

```text
--- the late-binding trap: all closures share one cell ---
  late-binding (all see final i): [2, 2, 2]
  default-arg capture fix:        [0, 1, 2]
```

The fix uses the fact that **default arguments are evaluated once, at function-definition time**
(Chapter 5): `i=i` snapshots the current value into the parameter's default, decoupling it from the
shared cell. The contrast with C++ is exact and worth holding onto: a C++ lambda forces you to
*choose* capture-by-value (`[i]`) or capture-by-reference (`[&i]`). Python has only capture-by-
reference, the cell, and `i=i` is how you simulate capture-by-value. The bug exists because Python
made the choice for you and chose the one that surprises people in loops.

---

## 3.4 The cyclic garbage collector

**Why this exists.** Chapter 19 shows that reference counting frees an object the instant its count
hits zero, which handles all acyclic garbage instantly and deterministically. It cannot free a
**cycle**: each object in the cycle keeps the others' counts above zero, so none ever reaches zero.
Python 2.0 added a separate, generational, cycle-detecting collector (the `gc` module) layered on top
of reference counting, for exactly this and nothing else.

**What it tracks.** Only **container** objects can form cycles: lists, dicts, sets, tuples, instances
of Python classes. Atomic objects (`int`, `str`, `float`) cannot reference other objects and are
never tracked, which is why Chapter 19's `object()` reported `gc.is_tracked` as `False`. Tracked
objects carry the `PyGC_Head` header measured there.

**The detection algorithm**, per collected generation: snapshot each tracked object's refcount into a
private field; traverse every tracked object's references and, for each reference to another object
*in the set*, decrement that target's private count, so that afterward the private count holds only
references from *outside* the set; objects with a positive count are reachable roots and are live,
along with everything they reach; objects still at zero are unreachable garbage; break and free the
garbage. This is a copy-and-subtract that finds cycles no refcount can see.

**Generations.** Objects are grouped into three generations. New objects start in generation 0;
survivors are promoted. The collector scans generation 0 frequently and older generations rarely,
betting that most objects die young, so most collections are cheap. That bet is exactly what §3.5
measures.

```python
# code/ch003/l04_cyclic_gc.py
class Node:
    def __init__(self, name):
        self.name = name
        self.ref = None
    def __del__(self):
        print(f"  __del__ {self.name}")
```

Verified output (CPython 3.13.5):

```text
--- the cycle keeps both objects alive despite no outside references ---
  refcount(A) inside the cycle: 2
  after 'del a, b': nothing was freed (no __del__ yet)

--- gc.collect() finds the unreachable cycle and finalizes it ---
  __del__ A
  __del__ B
  objects reclaimed: 2
```

`del a, b` removes the only outside bindings, yet neither `__del__` fires, because `a.ref` and
`b.ref` still hold the cycle up. Only `gc.collect()` breaks it, and both finalizers then run, which
brings up the second modern fact:

- **Finalizers in cycles are now run (PEP 442, Python 3.4+).** Before 3.4, an object with a `__del__`
  inside a cycle was deemed uncollectable and parked in `gc.garbage` forever, because the collector
  could not choose a safe finalization order. PEP 442 reworked finalization so cyclic objects are
  finalized then collected, as the output shows. Designing around `gc.garbage` is obsolete.
- **The generation-0 threshold on this build is 2000**, read via `gc.get_threshold()` as `(2000, 10,
  10)`. Generation 0 is collected when net allocations since the last collection exceed the first
  value; the others count how many younger-generation collections trigger an older one. These are
  build- and version-dependent and adjustable; never hard-code that gen-0 fires at a particular count.

---

## 3.5 Measurement: when disabling the collector helps, and when it hurts

The standard performance advice about the cyclic collector is "disable it in hot code." Like the
locals-versus-globals advice in Chapter 2, it is folklore that is sometimes right, and the honest
version is more useful than the slogan. `gc.disable()` removes tracing work, and tracing is *wasted*
only when the objects being traced will not be collected. That single condition splits the world in
two, and the two halves point in opposite directions.

**Methodology.** `code/ch003/bench_gc_cost.py`, run through `_harness/bench.py`. Two workloads, each
timed with the collector enabled and disabled. `min` is the headline statistic; ratios are within
this one interpreter. CPython 3.13.5, `-O2`, computed gotos on, Apple M3 Pro, macOS 27.0, arm64.
Figures reproduced to one decimal place across runs.

**Case A, building 50,000 long-lived objects.** Every object survives, so each automatic gen-0
collection traces a growing survivor set and reclaims nothing. Disabling the collector for the build
removes that pure waste:

| collector | ratio |
|---|---|
| enabled | 1.00x |
| disabled | **0.69x** (about 1.4x faster) |

**Case B, churning 50,000 short-lived cycles.** Each iteration builds a reference cycle and drops it.
Refcounting cannot reclaim a cycle, so only the collector can. Disable it and the cycles pile up until
a single final `collect()` must trace all of them at once:

| collector | ratio |
|---|---|
| enabled | 1.00x |
| disabled | **1.2x** (about 1.2x *slower*) |

**The rule the two cases teach.** Disabling the collector helps when it would otherwise rescan
survivors for nothing (Case A: startup that builds long-lived state, a large batch load, the moment
before forking a server). It hurts when there is real cyclic garbage to reclaim (Case B), because it
does not remove the work, it defers it into a larger, later batch and grows memory in the meantime.
The naive benchmark that "proves" disabling is faster is measuring Case A and calling it universal;
the naive one that proves it is slower is measuring Case B. Both exist, and which one your code is
determines the sign of the effect.

This is why the durable levers are targeted, not global: `gc.freeze()` (3.7+) moves everything
currently alive into a permanent generation the collector never scans again, which is Case A made
permanent and is the canonical move right after startup and before a fork. `gc.disable()` around a
bounded allocation phase is Case A made temporary. Leaving the collector off in a long-running process
is Case B waiting to happen: it leaks every cycle the process ever creates.

---

## 3.6 Edges and failure modes

**The late-binding closure in a loop.** §3.3. Use `i=i` capture or `functools.partial`. This is the
chapter's opening bug and the single most common closure error in the language.

**A comprehension does not leak, but a `for` loop does.** The comprehension's loop variable is
isolated (§3.1); a plain `for i in ...:` leaves `i` bound after the loop, by design. Confusing the two
produces phantom "leaks" that are not bugs and real reliance on a `for` variable that surprises the
next reader.

**Relying on `gc.garbage`.** Obsolete since PEP 442 (§3.4). Cyclic objects with finalizers are now
collected; do not design finalization to assume they are stranded.

**Comprehension versus generator expression.** A comprehension is eager and inlined (no frame); a
generator expression is lazy and keeps its own frame (§3.1). Reach for the generator when you will not
consume all results or the sequence is large, which is Chapter 9's subject.

**Leaving the collector disabled.** §3.5, Case B. A blanket `gc.disable()` in a long-running process
leaks every cycle it creates. The lever is for bounded phases; pair every `disable()` with an
`enable()` and a `collect()` at a safe point.

**Assuming a fixed gen-0 threshold.** §3.4. It is `(2000, 10, 10)` on this build and is not a language
guarantee. Read it if you need it.

---

## 3.7 Connections

**Backward.** The symbol-table pass that assigns each name its LEGB scope, and the cell mechanism that
implements the E tier, are Chapter 2. Reference counting and why a cycle leaks are Chapter 19, whose
`PyGC_Head` measurement is the header the collector threads its lists through. Default-argument
evaluation timing, the basis of the `i=i` fix, is Chapter 5.

**Forward.** Generator expressions and lazy iteration are Chapter 9. The allocator that groups tracked
objects into the size classes Chapter 19 measured, and the collector's internals in full, are **Deep
B**. `weakref`, which breaks a cycle so plain refcounting can reclaim it with no collector at all, is
**Deep A**. GC tuning in a genuine low-latency context, the trading loop, is **Deep K** and the
capstone.

**Across books.** The collector is a Python-object mechanism, so it does not reach across the **Book
I** boundary: a C++ object held through `nanobind` is reclaimed by C++'s rules, not Python's cyclic
collector, and a cycle that spans the boundary (a Python object referencing a C++ object that
references it back) is exactly the kind the collector cannot see and `weakref` must break. **Deep M**
owns that hazard.

---

## 3.8 Exercises

**1. Predict the captures.** Without running it, give the output of each:

```python
a = [lambda: i for i in range(3)]
b = [lambda i=i: i for i in range(3)]
c = [(lambda x: lambda: x)(i) for i in range(3)]
```

`c` fixes the bug a third way, without a default argument. Explain what the extra lambda does in terms
of §3.3's cells, and why it works.

**2. Make the leak visible.** §3.1 says a comprehension does not leak but a `for` loop does. Write a
single function that demonstrates both facts in one output, and then explain what `LOAD_FAST_AND_CLEAR`
would have to do differently for the `for` loop to also isolate its variable. Should it? Argue both
sides.

**3. Build an uncollectable-in-the-old-world object.** Construct a reference cycle whose objects have
`__del__` methods, and confirm with `gc.collect()`'s return value and the finalizer output that PEP
442 collects it. Then explain, in two sentences, the finalization-order problem that made this
impossible before 3.4.

**4. Find the crossover.** §3.5 shows disabling the collector helps for long-lived objects and hurts
for cycles. Write a workload with a *mixture*, some survivors and some cycles, and find the ratio of
survivors to cycles at which `gc.disable()` stops being a win. Report your methodology to the standard
of §3.5, including why your measurement is or is not comparable across the two interpreters.

**5. The design question.** Python could have used tracing garbage collection alone, with no reference
counting, and then it would have needed no separate cyclic collector at all. Chapter 19's exercise 5
asked you to weigh that trade for the object model; here, weigh it specifically for *this* chapter's
concerns. What would tracing-only GC do to the late-binding closure bug, to `__del__` timing, and to
the `gc.disable()` lever? Which of this chapter's three topics would simply cease to exist?

---

## 3.9 Summary and cross-references

- **Comprehensions** isolate their loop variable (since 3.0) and, since **PEP 709 (3.12)**, do so
  *inlined* with save/restore and no nested frame. Generator expressions still own a frame because
  they suspend.
- **PEP 227** added the **Enclosing** scope, completing **LEGB**, which the compiler resolves
  *statically* into the load opcode; the opcode *is* the scope decision.
- **Closures** capture by **cell**, a shared live reference, which is why the **late-binding loop**
  trap exists; `i=i` simulates the capture-by-value Python lacks.
- The **cyclic collector** exists solely to reclaim what refcounting cannot, cycles, using a
  generational copy-and-subtract; since **PEP 442** it finalizes cyclic objects rather than stranding
  them in `gc.garbage`.
- **Measured:** disabling the collector is **about 1.4x faster** when building long-lived objects and
  **about 1.2x slower** when churning cycles. The folklore is right in one case and wrong in the
  other; the deciding question is whether the traced objects will actually be collected.

**Cross-references.** The symbol-table pass and cell mechanism → Chapter 2. Reference counting and the
GC header → Chapter 19 (Deep A). Default-argument timing → Chapter 5. Generator expressions → Chapter
9. The allocator and collector internals, and `weakref` → Deep A and Deep B. GC tuning under latency
pressure → Deep K.
