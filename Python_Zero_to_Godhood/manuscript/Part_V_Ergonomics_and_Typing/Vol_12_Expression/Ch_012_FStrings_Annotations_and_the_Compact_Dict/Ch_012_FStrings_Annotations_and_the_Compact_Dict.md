# Chapter 12: F-Strings, Variable Annotations, and the Compact Dict (Python 3.6)

A production service logs a debug line on every request: `log.debug(f"request payload: {payload!r}")`.
Debug logging is disabled in production, so the line produces no output. It is also, on a busy service,
one of the most expensive things the request does, because the f-string computes `repr(payload)` on
every request whether or not anyone will ever read it. Measured against the correct form,
`log.debug("request payload: %r", payload)`, which defers the `repr` until the level check passes, the
f-string version is **107x slower** when the message is suppressed and the payload is large.

That gap is the sharp edge of a feature that otherwise made Python nicer to write than it had ever
been. Python 3.6 is the release that made modern Python *feel* modern, through three changes.
**f-strings** (PEP 498) replaced `%` and `.format()` with compile-time interpolation. **Variable
annotations** (PEP 526) extended type hints from function signatures to any binding, building the
runway for the whole typing ecosystem. And the **compact dict** turned the core mapping ordered and
30-40% smaller, an implementation detail in 3.6 that became a language guarantee in 3.7 and reshaped how
Python is written. We teach each with current mechanics, including two changes the original 3.6
descriptions predate: PEP 701's f-string overhaul (3.12) and, most consequentially, PEP 649's lazy
annotations (3.14), which *reverse* the forward-reference behavior this chapter's material was written
around.

## Section index

- **12.1** Formatted string literals (PEP 498) and the PEP 701 overhaul
- **12.2** Variable annotations (PEP 526)
- **12.3** Forward references, and how PEP 649 changed them in 3.14
- **12.4** The compact, ordered dictionary
- **12.5** Measurement: f-strings, and the logging trap
- **12.6** Edges and failure modes
- **12.7** Connections
- **12.8** Exercises
- **12.9** Summary and cross-references

Listings live under `code/ch012/` and are re-executed by `make verify` on both interpreters.

---

## 12.1 Formatted string literals (PEP 498) and the PEP 701 overhaul

**Why this exists.** The pre-3.6 options both pay runtime cost. `%`-formatting uses rigid C printf
routines and builds a temporary tuple; `"...".format(x)` does an attribute lookup for `.format`, a
function call, *and* re-parses the format string on every call. f-strings move interpolation to compile
time: the parser splits the literal into constant chunks and embedded expression AST sub-trees, and the
compiler emits inline opcodes, no method lookup, no call frame, no runtime format parsing. The 3.13
opcodes are `CONVERT_VALUE` (`!s`/`!r`/`!a`), `FORMAT_SIMPLE` (plain `{x}`), `FORMAT_WITH_SPEC`
(`{x:spec}`), and `BUILD_STRING` (one C-level concat); the original 3.6 implementation used a single
`FORMAT_VALUE` opcode with packed flags, so `FORMAT_VALUE` in a disassembly means pre-3.12 output.

```python
# code/ch012/l01_fstrings.py
x = 3.14159
```

Verified output (CPython 3.13.5):

```text
--- format specs, conversions, and the = debug form (3.8) ---
  f'{x:.2f}'  : 3.14
  f'{chr(65)!r}' : 'A'
  f'{x=}'     : x=3.14159
--- PEP 701 (3.12) relaxations: reuse quotes, multiline, nesting ---
  same-quote nesting f'{val["k"]}': v
  multiline expression            : 3
```

f-strings support `!r`/`!s`/`!a` conversions, full format specs, and the `{expr=}` self-documenting
form (3.8) that prints both the expression text and its value. **PEP 701 (Python 3.12)** reimplemented
f-strings in the PEG grammar and lifted the old restrictions: before 3.12 you could not reuse the
f-string's own quote inside the expression (`f"{val["k"]}"` needed a different quote), embed
backslashes, write multiline expressions, or put comments in the braces. All of that now works. The
trade-off is unchanged and is the chapter's subject: f-strings format *eagerly* (§12.5).

---

## 12.2 Variable annotations (PEP 526)

**Why this exists.** PEP 3107 (Python 3.0) allowed annotations on function parameters and return
values; **PEP 526** extended the syntax to *any* binding, giving static type checkers a place to read
types and the typing ecosystem (mypy, pyright, dataclasses, pydantic) its foundation.

**Annotations are metadata, not checks**, and where they are stored depends on scope:

```python
# code/ch012/l02_annotations.py
class Profile:
    name: str = "Anon"
    age: int                      # annotation only, no value

def process():
    y: int = 42                   # the ': int' is discarded by the compiler
    return y
```

Verified output (CPython 3.13.5):

```text
--- class annotations are stored in __annotations__ ---
  Profile.__annotations__: {'name': <class 'str'>, 'age': <class 'int'>}
--- function-local annotations leave no trace in the bytecode ---
  process() opcodes: ['LOAD_CONST', 'STORE_FAST', 'LOAD_FAST', 'RETURN_VALUE']
  no SETUP_ANNOTATIONS: the ': int' cost nothing.
```

At module or class scope the compiler emits `SETUP_ANNOTATIONS` and records each annotation in an
`__annotations__` dict, introspectable at runtime. At function-local scope the annotation is discarded
entirely, no storage and zero runtime cost, because locals run on hot paths; the disassembly of
`process` is just the load and store of `42`, with no trace of `: int`. And annotations are *not*
runtime validation: `x: int = "nope"` runs fine (§12.6).

---

## 12.3 Forward references, and how PEP 649 changed them in 3.14

This section is where the version matters most, because the answer flips between the two verification
interpreters. A self-referential class annotation names a type that does not yet exist during its own
body:

```python
# code/ch012/l03_forward_refs.py
class Node:
    parent: Node              # Node is not bound yet during its own body
```

On 3.13, class annotations are evaluated *eagerly* at definition time, so this raises:

Verified output (CPython 3.13.5):

```text
--- a bare self-reference in a class annotation ---
  NameError at definition (eager annotations, <= 3.13): name 'Node' is not defined
```

On 3.14, **PEP 649** makes annotations *lazy*, evaluated on demand through a compiler-generated
`__annotate__` function, so the definition succeeds and the annotation resolves when something reads it
(by which time `Node` is bound):

Verified output (CPython 3.14.6):

```text
--- a bare self-reference in a class annotation ---
  DEFINED without error (PEP 649 lazy annotations, 3.14+)
  Node.__annotations__ resolves to: {'parent': 'Node'}
```

This is not a subtle difference; it is the same three lines of code raising an exception on one
interpreter and succeeding on the next. A book that documented only the 3.13 behavior would be teaching
a rule that 3.14 abolished. The portable idiom that works on every version is to quote the forward
reference, `parent: "Node"`, which stores it as a string on 3.13 and is harmless on 3.14. PEP 649 is
also why `from __future__ import annotations` (PEP 563), the older stringize-everything workaround, is
on a path to retirement. The mechanism behind lazy annotations, the `__annotate__` function and the
lazy-evaluation scope it shares with PEP 695, is Chapter 18; the type system in depth is **Deep I**.

---

## 12.4 The compact, ordered dictionary

**Why this exists.** `dict` is the most-used container in Python and the backbone of every namespace,
object `__dict__`, and keyword-args bundle, so its layout matters enormously. Before 3.6, a dict was
*one* sparse hash table of 24-byte entry slots kept at most two-thirds full, so it held many empty
24-byte slots, wasting memory and scattering entries across cache lines. Raymond Hettinger's compact
design (3.6) split the table in two: `dk_indices`, a small sparse array of integer indices (1/2/4/8
bytes each), the actual hash table; and `dk_entries`, a dense contiguous array of `(hash, key, value)`
appended in insertion order. A lookup hashes into `dk_indices`, reads the small integer, and indexes
into the dense `dk_entries`. Empty slots now cost 1-8 bytes, not 24, cutting dict memory ~30-40%, and
because entries are dense and in-order, iteration order equals insertion order for free:

```python
# code/ch012/l04_compact_dict.py
```

Verified output (CPython 3.13.5):

```text
--- iteration order equals insertion order ---
  inserted z, a, m, b -> list(d): ['z', 'a', 'm', 'b']
--- deleting and re-inserting moves a key to the end ---
  after del+reinsert 'first' : ['second', 'third', 'first']
```

The del-and-reinsert result shows the ordering is *insertion* order, not sorted order: removing `first`
and adding it back moves it to the end of the dense array. **Insertion order was an implementation
detail in 3.6 and a language guarantee in 3.7**, so code may now rely on it. The senior-engineer
contrast: this is what Java provides only via a separate `LinkedHashMap`; in Python the default `dict`
is ordered, and the ordering costs nothing because it falls out of the compact layout. Sets remain
unordered, so order does not survive a round-trip through one.

---

## 12.5 Measurement: f-strings, and the logging trap

Two claims about f-strings get tested here: that they are "the fastest interpolation," and the logging
anti-pattern from the chapter opening.

**Methodology.** `code/ch012/bench_fstring.py`, through `_harness/bench.py`. `min` over 15 batches;
within one interpreter; CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64. Reproduced across runs.

**Plain substitution, f-strings win:**

| form | ratio |
|---|---|
| f-string | 1.00x |
| `%`-format | 1.10x |
| `.format()` | 1.68x |

**With a numeric format spec, the gap closes:**

| form | ratio |
|---|---|
| f-string | 1.00x |
| `%`-format | 1.04x |

For plain substitution the f-string is genuinely fastest, as advertised. But with a numeric format
spec (`:.2f`), the spec application dominates and the syntaxes converge to within a few percent, so the
blanket claim "f-strings are always the fastest interpolation" is overstated. The compile-time win is
in avoiding the method lookup and call, and that win shrinks when the actual formatting work grows.

**The logging trap, which is the one that matters in production:**

| form (suppressed level, expensive `repr`) | ratio |
|---|---|
| lazy `%`-args | 1.00x |
| eager f-string | **107x** |

Logging an f-string at a *disabled* level runs the interpolation and discards the result. For a trivial
value that is a few percent, but for an expensive `repr` of a large object, as in the chapter opening,
it is the *entire* cost of that `repr`, done for nothing. `log.info("data=%r", big)` passes `big`
unformatted and lets the logging machinery format it *only if* the level check passes; `log.info(f"data
={big!r}")` formats it first, unconditionally, then hands the finished string to a call that throws it
away. The 107x is the full cost of the discarded `repr`. **Use `log.info("...%s", x)`, never
`log.info(f"...")`.** This is the single most common performance bug involving f-strings, and it is
invisible until you profile a service whose logs are off.

---

## 12.6 Edges and failure modes

**f-strings in logging.** §12.5. Eager formatting means a suppressed log line still pays the
interpolation cost, up to 107x for an expensive `repr`. Use `%`-args and let logging defer.

**f-strings with untrusted data into SQL/HTML/shell.** f-strings are interpolation, not escaping.
Never build a query or markup with one; use parameterized queries and proper escaping.

**Forward references, version-dependent.** §12.3. A bare self-referential annotation raises `NameError`
on 3.13 and succeeds on 3.14. Quote it (`"Node"`) for portability across both.

**Annotations are not validation.** §12.2. `x: int = "nope"` runs. Use pydantic, dataclass validators,
or a runtime checker (**Deep I**) for enforcement.

**Function-local annotations cost nothing; class/module ones cost a little.** §12.2. `SETUP_ANNOTATIONS`
runs at import for module- and class-level annotations; do not annotate a hot module constant expecting
zero cost.

**Relying on set order.** §12.4. Dict order is guaranteed since 3.7; set order is not. Order does not
survive a trip through a set.

---

## 12.7 Connections

**Backward.** The PEG parser that PEP 701 reimplemented f-strings in is Chapter 14 (PEP 617). The
`__annotations__` metadata this chapter introduces is the erased-typing model of the whole typing
story. The dict whose compact layout this chapter measures is the object model's most-used container
(Chapter 19).

**Forward.** PEP 649's lazy annotations, the mechanism that reverses §12.3 on 3.14, are Chapter 18,
which shares its lazy-evaluation scope with PEP 695. Dataclasses, which build on the annotations of
§12.2, are Chapter 13, the next chapter. The type system in depth, `TypedDict`, protocols, variance,
and runtime validators, is **Deep I**. The full dict internals are **Deep A**; the codecs and `string`
module are **Deep P**.

**Across books.** The compact, ordered dict is quietly load-bearing at the **Book III** seam: a
retrieval pipeline's document records are dicts, and their guaranteed insertion order means a serialized
record round-trips field-for-field without a separate ordered container, which matters when the same
record crosses into a C++ index builder (**Book I**) that reads fields positionally. The Unicode
sandwich of Chapter 7 and the f-string's eager formatting together define how text is assembled before
it crosses either boundary. **Deep M** and **Deep U** own those seams.

---

## 12.8 Exercises

**1. Measure your own logging trap.** Reproduce §12.5's logging benchmark with three interpolations of
increasing cost: a small int, a `repr` of a 1000-element list, and a call to a function that sleeps a
millisecond. Predict the eager-vs-lazy ratio for each before measuring, and explain why the ratio grows
with interpolation cost.

**2. Watch the forward-reference flip.** Run the §12.3 listing on both a 3.13 and a 3.14 interpreter if
you have them (or reason precisely about each). Then find the one-character change that makes the code
behave identically on both, and explain what it stores on each version.

**3. Prove the annotation is stripped.** Disassemble a function with several local annotations and
confirm none of them appears in the bytecode. Then move the same annotations to module scope and show
`SETUP_ANNOTATIONS` appear. Explain why the compiler makes this scope distinction.

**4. Break the ordering assumption.** Write code that relies on dict insertion order and works, then
route the same data through a `set` and show the order is lost. Explain, using §12.4, why the dict
guarantees order and the set does not, in terms of their layouts.

**5. The design question.** PEP 649 (3.14) reversed the forward-reference behavior that Python
programmers had worked around for years with quotes and `from __future__ import annotations`. Argue
whether making annotations lazy by default was worth breaking the eager-evaluation behavior some code
depended on (for example, code that read `__annotations__` at import and expected real objects, not
lazy ones). Your answer must address who benefits, who is broken, and how the change interacts with the
`get_type_hints` resolution that frameworks already do.

---

## 12.9 Summary and cross-references

- **f-strings** (PEP 498) interpolate at **compile time** (`CONVERT_VALUE`/`FORMAT_SIMPLE`/
  `FORMAT_WITH_SPEC`/`BUILD_STRING` on 3.13); **PEP 701 (3.12)** removed the nesting, multiline,
  backslash, and comment restrictions. They format **eagerly**.
- **Variable annotations** (PEP 526) are **metadata, not checks**: stored in `__annotations__` at
  module/class scope, **stripped** at function scope.
- **Forward references flip between versions:** a bare self-reference raises `NameError` on 3.13 and
  succeeds on 3.14 under **PEP 649** lazy annotations. Quote it for portability.
- The **compact dict** (3.6) splits a sparse index array from a dense entry array, cutting memory
  ~30-40% and making **insertion order** intrinsic, a guarantee since 3.7.
- **Measured:** f-strings are fastest for plain substitution (`%`-format 1.10x, `.format` 1.68x) but
  roughly tied with a numeric spec; logging an f-string at a suppressed level with an expensive `repr`
  costs **107x** the `%`-args form. Never log with an f-string.

**Cross-references.** The PEG parser behind PEP 701 → Chapter 14. Lazy annotations (PEP 649) → Chapter
18. Dataclasses → Chapter 13. The type system → Deep I. Dict internals → Deep A; codecs and `string` →
Deep P. The data-record seam to Books I and III → Deep M and Deep U.
