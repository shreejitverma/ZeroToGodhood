# Chapter 17: Faster CPython, the Specializing Adaptive Interpreter (Python 3.11)

Two functions read an attribute in a hot loop. They are byte-for-byte identical:

```python
def read(o):
    return o.x
```

One is called a million times with objects that are always the same type. The other is called a
million times with objects that alternate between two types. On CPython 3.11 and later, the first is
about **1.5x faster** than the second, and nothing in the source explains why. The difference is
entirely in what the interpreter did to the bytecode *while the loop ran*, and understanding it is the
difference between writing hot Python that the interpreter can help and hot Python that fights it.

Python 3.11 was the first release of the multi-year "Faster CPython" project, and it made typical
programs meaningfully faster without changing a line of your code. The engine is **PEP 659: the
specializing adaptive interpreter**, which *rewrites its own bytecode at runtime*, replacing generic
opcodes with type-specialized ones backed by inline caches. This is not a JIT (that is PEP 744,
Chapter 21); no machine code is generated, the interpreter loop simply gets much smarter about the
common case. This chapter explains the mechanism, demonstrates specialization *happening* via
`dis(..., adaptive=True)`, measures the monomorphism lever the two functions above illustrate, and
derives the coding guidelines that keep hot paths on the fast track.

## Section index

- **17.1** PEP 659: the specialization lifecycle
- **17.2** Inline caches and type versioning
- **17.3** Specialization families and deoptimization
- **17.4** The rest of the 3.11 leap: zero-cost exceptions, cheaper frames, PEP 657
- **17.5** Measurement: monomorphism is the lever
- **17.6** Edges and failure modes
- **17.7** Connections
- **17.8** Exercises
- **17.9** Summary and cross-references

Listings live under `code/ch017/` and are re-executed by `make verify` on both interpreters.

---

## 17.1 PEP 659: the specialization lifecycle

**Why this exists.** A generic opcode like `LOAD_ATTR` must handle *any* object: walk the type's MRO,
consult `__getattribute__`, probe instance and class dictionaries. But real code is overwhelmingly
*monomorphic*, a given `p.x` almost always sees the *same* type at that exact call site, run after run.
PEP 659 exploits this: observe what actually flows through each instruction, and once it is stable,
*patch the bytecode in memory* with a specialized opcode that assumes that shape and falls back safely
if the assumption breaks.

Each adaptive instruction moves through a lifecycle:

```text
[ generic ]  LOAD_ATTR
     |  first executions: gather type info, decrement a counter
     v
[ adaptive / warming ]  (counter counting down)
     |  types stayed consistent -> counter hits 0
     v
[ specialized ]  LOAD_ATTR_INSTANCE_VALUE   (fast path, validated by a cheap guard)
     |  guard fails (a different type appears)
     v
[ deoptimize ]  -> run the generic slow path; if it keeps missing, give up specializing
```

The critical property: a specialized opcode is *always guarded*. It first checks a cheap invariant (a
cached type version, §17.2); if the guard holds it takes the fast path, and if not it *deoptimizes* to
the generic behavior. Correctness is never at risk, only speed.

You can watch it happen. Warm a function, then disassemble with `adaptive=True`:

```python
# code/ch017/l01_specialization.py
class P:
    def __init__(self, x): self.x = x
def hot(p):
    return p.x + p.x
for _ in range(1000):       # make the call site hot and monomorphic
    hot(P(5))
```

Verified output (CPython 3.13.5):

```text
--- after warm-up, generic opcodes are patched to specialized ones ---
  specialized opcodes: ['LOAD_ATTR_INSTANCE_VALUE', 'LOAD_ATTR_INSTANCE_VALUE', 'BINARY_OP_ADD_INT']
```

Both the attribute load and the addition specialized: `LOAD_ATTR_INSTANCE_VALUE` reads the slot by
offset with no dict lookup and no MRO walk, and `BINARY_OP_ADD_INT` runs the int-only add that skips
the general `nb_add` dispatch. The generic `LOAD_ATTR` and `BINARY_OP` the compiler first emitted have
been overwritten in place.

---

## 17.2 Inline caches and type versioning

**What the interpreter actually does.** The specialized opcode needs somewhere to store what it
learned, the expected type and the attribute's offset. CPython stores this in an *inline cache*: extra
`_Py_CODEUNIT` slots placed *directly after the instruction* in the code array, so the data is in the
same cache line the interpreter is already reading. For `LOAD_ATTR` the cache is an `_PyAttrCache`:

```c
/* Illustrative; Include/internal/pycore_code.h. The exact tag has changed across versions. */
typedef struct {
    uint16_t counter;        /* adaptive counter: when it hits 0, try to specialize */
    uint16_t version[2];     /* the target type's tp_version_tag (cache guard) */
    uint16_t index;          /* the attribute's offset in the instance values array */
} _PyAttrCache;
```

The guard is the type's **`tp_version_tag`**, a per-type id that CPython *bumps whenever the class is
mutated* (a method added, a class attribute set, the MRO changed). A specialized `LOAD_ATTR` checks the
live object's type version against the cached one; if they match, it reads `obj_values[index]` directly.
If the class was mutated, the tag no longer matches and the opcode deoptimizes. `LOAD_GLOBAL` works the
same way against the module and builtins dictionaries' *keys version*, which is why Chapter 2's
locals-versus-globals folklore no longer holds: a hot `LOAD_GLOBAL` specializes to
`LOAD_GLOBAL_MODULE`, an inline-cached read nearly as cheap as `LOAD_FAST`.

---

## 17.3 Specialization families and deoptimization

PEP 659 specializes the opcodes that dominate real workloads:

| Generic | Specialized examples | Fast path |
|---|---|---|
| `LOAD_ATTR` | `LOAD_ATTR_INSTANCE_VALUE`, `LOAD_ATTR_SLOT`, `LOAD_ATTR_METHOD_*` | direct offset / slot read |
| `LOAD_GLOBAL` | `LOAD_GLOBAL_MODULE`, `LOAD_GLOBAL_BUILTIN` | dict value-array read, no hashing |
| `BINARY_OP` | `BINARY_OP_ADD_INT`, `BINARY_OP_ADD_FLOAT`, `BINARY_OP_ADD_UNICODE` | typed arithmetic/concat |
| `BINARY_SUBSCR` | `BINARY_SUBSCR_LIST_INT`, `BINARY_SUBSCR_DICT` | typed indexing |
| `CALL` | `CALL_PY_EXACT_ARGS`, `CALL_BUILTIN_*` | skip argument re-binding |

**Deoptimization and thrashing.** Specialization is a bet on monomorphism. If a call site is
*polymorphic*, the guard keeps failing, and this is clearest when two types need different fast paths:

```python
# code/ch017/l02_deoptimization.py
class Slotted:
    __slots__ = ("x",)     # attribute read is LOAD_ATTR_SLOT
class Dicted:
    pass                   # attribute read is LOAD_ATTR_INSTANCE_VALUE
```

Verified output (CPython 3.13.5):

```text
--- the same code, monomorphic vs polymorphic call site ---
  read_mono (Slotted only) LOAD_ATTR: ['LOAD_ATTR_SLOT']
  read_poly (Slotted+Dicted) LOAD_ATTR: ['LOAD_ATTR_INSTANCE_VALUE']
```

The monomorphic site holds `LOAD_ATTR_SLOT`. The polymorphic site, seeing both a `__slots__` class and
an ordinary one, settled on `LOAD_ATTR_INSTANCE_VALUE`, whose guard then *misses on every `Slotted`
instance* and deoptimizes, so half its calls run the generic slow path. The worst case, alternating
types that force repeated re-specialization, pays the combined cost of guard checks, slow lookups, and
re-specialization, and can be *worse* than the pre-3.11 generic interpreter for that site. The
disassembly shows only which specialization a site settled on; the runtime cost of the misses is what
§17.5 measures.

---

## 17.4 The rest of the 3.11 leap: zero-cost exceptions, cheaper frames, PEP 657

Specialization is the headline, but 3.11's speedup is the sum of several changes. *Zero-cost
exceptions* (Chapter 6) replaced the runtime block stack with a static exception table, so a `try` that
does not raise costs nothing on the happy path (Chapter 6 measured this at 1.01x). *Cheaper, lazy
frames* were slimmed and are created more cheaply (allocated inline on a per-thread data stack), making
Python-to-Python calls markedly faster, the foundation `CALL_PY_EXACT_ARGS` builds on. And *fine-grained
error locations (PEP 657)* point a caret at the exact sub-expression that failed:

```text
return a / b / c
~~~~~~^~~
```

The carets isolate `(a / b) / c`'s failing division, invaluable for debugging compound expressions.
This location data lives in the code object's line table; it costs a little memory, disable-able via
`-X no_debug_ranges`.

---

## 17.5 Measurement: monomorphism is the lever

The chapter opened with two identical functions differing 1.5x in speed. Here is that measurement, and
it is the whole practical payoff of understanding PEP 659.

**Methodology.** `code/ch017/bench_monomorphism.py`. The same attribute-read and add loops, run over a
single type (the specializer holds its bet) and over two types at one instruction (it thrashes). `min`
over 15 batches; within one interpreter; CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| hot site | ratio |
|---|---|
| attribute read, monomorphic | 1.00x |
| attribute read, polymorphic (two types) | **1.28x** |
| int add, monomorphic | 1.00x |
| int add, polymorphic (int and str) | **1.48x** |

Keeping a hot site monomorphic is **1.3x to 1.5x** faster than letting it see two types, on
byte-identical source. The monomorphic sites hold `LOAD_ATTR_INSTANCE_VALUE` and `BINARY_OP_ADD_INT`
and take the fast path every time; the polymorphic sites' guards miss on half the calls and deoptimize.

This is the coding guidance for 3.11+ code, and it is different from the folklore of earlier chapters:

- **The biggest wins come from consistent types at hot sites**, not from chasing opcode counts by hand.
  If a hot function is polymorphic (it funnels structurally different types through the same attribute
  access or arithmetic), split it into separate monomorphic functions when the profile shows it matters.
- **Do not mutate classes in steady state.** Adding a method or a class attribute bumps `tp_version_tag`
  and invalidates every inline cache that depended on it. Configure behavior at class-definition time.
- **`__slots__` specializes well** (`LOAD_ATTR_SLOT`) and removes the per-instance dict, a double win
  for hot, numerous objects, and consistent with Chapter 4's finding that `__slots__` is a memory win
  that the specializer makes cost-free for access.

And the honest scope, stated because the temptation is to over-claim: this is *interpretation, not
compilation*. Specialization removes interpreter overhead on the fast path but does not vectorize,
inline across calls, or escape-analyze. For order-of-magnitude numeric speed you still drop to
NumPy/Cython/C (**Deep T**), or, in 3.13+, the experimental JIT (Chapter 21), which builds *on top of*
these specialized opcodes.

> **On the headline number.** The "Faster CPython" project reported typical speedups in the tens of
> percent over 3.10, but this book does not reproduce that figure, because a fair 3.10-versus-3.11
> comparison requires both interpreters built from source with identical flags (the two on this machine
> differ in optimization level and computed-goto settings, per `make interpreters`). The number is
> sourced to the CPython team's published tracking, not measured here; what §17.5 measures is the
> *within-interpreter* monomorphism lever, which is reproducible.

---

## 17.6 Edges and failure modes

**Polymorphic hot sites.** §17.3, §17.5. A site that sees structurally different types thrashes and can
be slower than the pre-3.11 generic interpreter. Keep hot sites monomorphic; split if needed.

**Runtime class mutation.** §17.2. Monkeypatching or setting a class attribute in steady state bumps
`tp_version_tag` and de-optimizes every dependent site. Configure at class-definition time.

**Benchmarking cold code.** A cold function runs generic opcodes; measure steady-state, after warm-up,
with `timeit` or the harness, not the first call. §17.5's numbers are all steady-state.

**Chasing opcode counts by hand.** §17.5. The lever is monomorphism, not micro-tweaks. Reducing opcode
count rarely helps if the site is already specialized; keeping types consistent does.

**Expecting compilation.** §17.5. Specialization is smarter interpretation. It does not vectorize or
inline across calls; for numeric throughput, drop to NumPy or the JIT.

---

## 17.7 Connections

**Backward.** The base interpreter loop and the `RESUME` opcode a specialized function opens with are
Chapter 2. Zero-cost exceptions (§17.4) are Chapter 6, measured there at 1.01x. The `LOAD_GLOBAL`
specialization that overturned Chapter 2's locals-versus-globals folklore is §17.2. `__slots__`
specializing well ties to Chapter 4's memory measurement.

**Forward.** The copy-and-patch JIT (PEP 744) that consumes these specialized opcodes is Chapter 21.
`ceval.c` and the full opcode set are **Deep J**. Benchmarking discipline is **Deep K**. PEP 695
generics and exception groups, the rest of the 3.11-3.12 window, are Chapters 18 and 19.

**Across books.** The specializing interpreter is why the Python analytics layer over a **Book I** C++
kernel can be fast enough to be worth writing in Python at all: the hot dispatch and bookkeeping around
the C++ call specialize to near-C interpreter speed, so only the genuinely numeric inner loop needs to
cross into C++. Monomorphism is also a design constraint on the boundary: a `nanobind`-bound type that
presents one consistent shape lets the Python call sites that use it specialize, where a shape-shifting
wrapper would thrash them. **Deep M** owns that boundary; this chapter is why keeping it monomorphic
matters.

---

## 17.8 Exercises

**1. Watch a specialization form and break.** Warm a monomorphic attribute-read function and confirm it
specialized with `dis(..., adaptive=True)`. Then start feeding it a second type and disassemble again.
Explain what you see in terms of the guard and `tp_version_tag`.

**2. Reproduce the monomorphism lever.** Run §17.5's benchmark, then construct a *three*-type
polymorphic site and predict whether it is slower than the two-type one before measuring. Explain the
result in terms of how many specializations a single inline cache can hold.

**3. Break a cache with monkeypatching.** Warm a hot method-call site, confirm it specialized, then set
a new attribute on the class inside the loop and show the site deoptimizes. Explain, using §17.2, why a
single class mutation invalidates the cache, and estimate the cost if it happens every iteration.

**4. Find the caret.** Write a compound expression that fails (like `a / b / c` with `c == 0`), catch
it, and show the PEP 657 caret isolating the failing sub-expression. Then disable it with
`-X no_debug_ranges` and show the difference. When is the memory cost of the location table worth
paying?

**5. The design question.** PEP 659 chose to specialize the *interpreter* rather than add a JIT (which
came later, and experimentally). Argue why specialization was the right first step. Your answer must
address the correctness guarantee (every specialized opcode is guarded and deoptimizes), the fact that
it needs no compilation and works on every platform, and what it cannot do that a JIT can (§17.5).

---

## 17.9 Summary and cross-references

- **PEP 659** makes the interpreter **specialize its own bytecode at runtime**: generic to adaptive to
  specialized, with a cheap **guard** and safe **deoptimization**, *not* a JIT, no machine code.
- Specialized opcodes are backed by **inline caches** adjacent to the bytecode, guarded by the type's
  **`tp_version_tag`** (and dict keys versions); `dis(..., adaptive=True)` shows them.
- **Polymorphic** call sites **deoptimize** and can **thrash**; the disassembly shows the settled
  specialization, the runtime cost is in the guard misses.
- 3.11 also brought **zero-cost exceptions**, **cheaper frames**, and **PEP 657** caret-precise
  tracebacks.
- **Measured:** keeping a hot site monomorphic is **1.3x to 1.5x** faster than letting it see two types,
  on byte-identical source. Monomorphism is the lever; runtime class mutation is the anti-lever.

**Cross-references.** The interpreter loop and `RESUME` → Chapter 2. Zero-cost exceptions → Chapter 6.
The `LOAD_GLOBAL` specialization → §17.2 and Chapter 2. `__slots__` → Chapter 4. The copy-and-patch JIT
→ Chapter 21. `ceval.c` and the full opcode set → Deep J. Benchmarking discipline → Deep K. The C++
boundary and monomorphism → Deep M.
