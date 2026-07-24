# Chapter 24: PEP 649, Deferred Annotations (Python 3.14)

Three separate chapters of this book have flagged the same version boundary. Chapter 12 showed that
`class Node: parent: Node` raises `NameError` on 3.13 and succeeds on 3.14. Chapter 16 showed that an
annotated `def` costs 5.6x a bare one on 3.13 but only 3.5x on 3.14. Chapter 18 showed that a `type`
statement's lazy scope gained a `.format` parameter in 3.14. All three are the same change, and this
chapter is its home: **PEP 649**, which made annotations *lazy*.

For most of Python's history, an annotation was evaluated eagerly, the moment the `def` or class body
ran. That single decision produced a decade of workarounds: quoting forward references, `if
TYPE_CHECKING:` guards, `from __future__ import annotations` (PEP 563) to stringify everything, and
`get_type_hints` to re-evaluate the strings later. PEP 649 replaces eager evaluation with a
compiler-generated `__annotate__` function that runs on demand, and in doing so it retires most of those
workarounds and reduces the definition-time cost of annotating. This is the deep treatment of the
mechanism the earlier chapters only pointed at; it is also the same lazy-scope machinery PEP 695 (Chapter
18) introduced for type aliases, now generalized to all annotations.

> **Version note.** PEP 649 and the `annotationlib` module are Python 3.14. This chapter's listings are
> gated `# requires: 3.14+` and verified on the 3.14 interpreter; on 3.13 the harness reports them
> skipped, and the eager-evaluation behavior they replace is recorded in Chapter 12.

## Section index

- **24.1** The problem: annotations that run too early
- **24.2** Lazy annotations and `__annotate__`
- **24.3** `annotationlib` and the three formats
- **24.4** What PEP 649 retires, and what it costs
- **24.5** Edges and failure modes
- **24.6** Connections
- **24.7** Exercises
- **24.8** Summary and cross-references

Listings live under `code/ch024/` and are re-executed by `make verify` on the 3.14 interpreter.

---

## 24.1 The problem: annotations that run too early

An annotation is an expression. `x: list[int]` contains the expression `list[int]`, and `parent: Node`
contains the expression `Node`. Through Python 3.13, that expression was evaluated *eagerly*, at the
moment the surrounding `def` or class statement executed. Eager evaluation has two consequences, and
both are costs.

The first is *forward references*. If the expression names something that does not exist yet, evaluating
it raises `NameError`. A class that annotates a field with its own type (`parent: Node` inside `Node`) is
the canonical case: `Node` is not bound while its own body runs, so the annotation fails. The workaround
was to quote it, `parent: "Node"`, turning the annotation into a string the interpreter would not
evaluate and a checker would resolve later, an entire convention built around avoiding evaluation.

The second is *cost*. Eager evaluation means every annotated `def` builds its annotation objects at
definition time, which Chapter 16 measured at 5.6x a bare `def` on 3.13. For a module that defines
thousands of annotated functions, that is real import-time work for metadata the running program may
never read.

PEP 649 addresses both by not evaluating the annotation until someone asks for it.

---

## 24.2 Lazy annotations and `__annotate__`

Under PEP 649, the compiler does not evaluate the annotations when the `def` or class runs. Instead it
compiles them into a `__annotate__` function attached to the object, which produces the annotations dict
on demand. The `def` succeeds whether or not the annotation's names exist:

```python
# code/ch024/l01_deferred_annotations.py   # requires: 3.14+
def f(x: Undefined) -> AlsoMissing:      # names that do not exist anywhere
    ...

class Node:
    next: Node                            # self-reference; raised NameError on <= 3.13
```

Verified output (CPython 3.14.6):

```text
--- a def with undefined annotations now survives definition ---
  defined without error: f
  has a lazy __annotate__ function: True
--- a self-referential class annotation also just works ---
  Node.__annotations__: {'next': 'Node'}
```

`f` was defined despite annotating with two names that exist nowhere, and it carries a `__annotate__`
function. `Node`'s self-reference, which raised `NameError` at definition time on 3.13 (Chapter 12,
§12.3), now succeeds, and reading `Node.__annotations__` resolves `next` to `Node`, because by the time
anything reads it, `Node` is bound. The `__annotate__` function is exactly the generalization of PEP
695's lazy value scope from Chapter 18: a compiler-built function that evaluates a deferred expression
in the namespace where it was written, invoked on demand rather than eagerly.

---

## 24.3 `annotationlib` and the three formats

Deferring evaluation raises a question eager evaluation never had to answer: what should a tool get when
it asks for an annotation whose names *cannot* be resolved? PEP 649 answers with a protocol of *formats*,
exposed through the new `annotationlib` module:

```python
# code/ch024/l02_annotationlib.py   # requires: 3.14+
from annotationlib import Format, get_annotations
def f(x: Undefined) -> AlsoMissing:      # deliberately unresolvable
    ...
```

Verified output (CPython 3.14.6):

```text
--- the three formats, on annotations that cannot be resolved ---
  VALUE     : NameError: name 'Undefined' is not defined
  FORWARDREF: {'x': ForwardRef('Undefined', owner=<function f at 0xADDR>), 'return': ForwardRef('AlsoMissing', owner=<function f at 0xADDR>)}
  STRING    : {'x': 'Undefined', 'return': 'AlsoMissing'}
--- for resolvable annotations, VALUE returns the real objects ---
  get_annotations(g, VALUE): {'n': <class 'int'>, 'return': <class 'str'>}
```

The three formats are the whole design. **`VALUE`** evaluates the annotation to real objects and raises
`NameError` if a name is missing, exactly as reading `__annotations__` would; for the resolvable `g` it
returns `{int, str}`. **`FORWARDREF`** never raises: for each unresolvable name it returns a `ForwardRef`
object, so a checker or documentation tool can work with partial information rather than failing on the
first missing name. **`STRING`** returns the source text of each annotation. `typing.get_type_hints`
builds on this, which is why 3.14 tooling handles forward references that 3.13 tooling could only manage
through the stringize-everything hack of `from __future__ import annotations`.

---

## 24.4 What PEP 649 retires, and what it costs

PEP 649 makes several long-standing workarounds unnecessary. Quoting forward references
(`parent: "Node"`) is no longer needed for the definition to succeed. `from __future__ import
annotations` (PEP 563), which stringified *all* annotations and had its own problems (it made
annotations unavailable as real objects at runtime, breaking libraries that read them), is on a path to
retirement now that laziness gives the forward-reference benefit without the everything-is-a-string cost.
And the `if TYPE_CHECKING:` dance for import cycles is often avoidable, because an annotation that
mentions a type imported only for checking no longer needs that import to exist at runtime.

The cost side is where the earlier measurement lands. Chapter 16 found an annotated `def` at 5.6x a bare
one on 3.13 and **3.5x on 3.14**. PEP 649 *reduced* the definition-time cost, because the annotation
expressions are no longer evaluated at `def` time, but it did *not* eliminate it: the `__annotate__`
function still has to be built and attached. So "annotations are now free" is as wrong as "annotations
have zero overhead" was; the honest statement is that PEP 649 moved the *evaluation* cost from definition
time to first-read time (where it is often never paid), while leaving a smaller *construction* cost at
definition time. For a program that never introspects its annotations, that is close to a pure win; for
one that reads them, the evaluation cost simply moved.

---

## 24.5 Edges and failure modes

**Assuming annotations are now free.** §24.4. An annotated `def` is still ~3.5x a bare one on 3.14; the
evaluation moved to first read, the construction did not vanish.

**Reading `__annotations__` and expecting eager errors.** Code that relied on a bad annotation raising
at import time will no longer see the error until something reads the annotations. If you *want* eager
validation, read `__annotations__` (or call `get_annotations(..., VALUE)`) explicitly at import.

**Mixing `from __future__ import annotations` with `annotationlib`.** The `__future__` import forces the
STRING format for that module, which changes what `get_annotations(VALUE)` can return. On 3.14, prefer
plain lazy annotations over the `__future__` import; do not combine them.

**Expecting `FORWARDREF` everywhere.** Only `annotationlib.get_annotations` and `get_type_hints` speak
the format protocol. Reading the raw `__annotations__` attribute triggers `VALUE`-style evaluation and
can still raise on an unresolvable name.

**Cross-version code.** A forward reference that works unquoted on 3.14 still raises on 3.13. For code
that must run on both, quote forward references or use `from __future__ import annotations`; do not rely
on 3.14 laziness until 3.14 is your floor.

---

## 24.6 Connections

**Backward.** The eager-annotation behavior this chapter replaces is Chapter 12 (the forward-reference
flip) and Chapter 16 (the cost measurement); this chapter is the mechanism both pointed at. The lazy
value scope that PEP 649 generalizes is PEP 695's `type` statement, Chapter 18, which shares the
`__annotate__`-style deferred-evaluation function.

**Forward.** The type system that consumes these annotations, `get_type_hints`, checker behavior,
runtime validators, is **Deep I**. The compiler machinery that builds the `__annotate__` function is
**Deep J**.

**Across books.** Lazy annotations make Book II's typed interfaces cleaner at both seams. A module that
types a function against a **Book I** binding or a **Book III** message type no longer needs a runtime
import of that type just to annotate against it, so the annotation can name a type that only the checker
resolves, cutting import cycles at the boundary. **Deep I** owns the type-system consumption; this
chapter is why the annotations it reads can now name things the runtime has not imported.

---

## 24.7 Exercises

**1. Confirm the retirement.** Take a self-referential class that needs a quoted forward reference on
3.13, remove the quotes, and show it works on 3.14. Then explain, using §24.2, exactly when the
annotation is evaluated and why `Node` is bound by then.

**2. Use all three formats.** Write a function annotated with one resolvable and one unresolvable name,
and call `get_annotations` with `VALUE`, `FORWARDREF`, and `STRING`. Explain what each returns for each
annotation and which a documentation tool would prefer.

**3. Measure the moved cost.** Reproduce Chapter 16's annotated-vs-bare def benchmark on 3.14, confirm
the ~3.5x, then measure the cost of *reading* the annotations (`get_annotations(VALUE)`) separately.
Explain how the two together compare to 3.13's eager 5.6x.

**4. Break a runtime reader.** Write code that reads `__annotations__` at import time and depends on
getting real objects, then give it an annotation with an unresolvable name and show it now fails at read
time rather than def time. Fix it, and explain the diagnostic difference PEP 649 introduced.

**5. The design question.** PEP 649 competed with PEP 563 (`from __future__ import annotations`, which
stringified everything) as the solution to forward references. PEP 563 was even made the planned default
and then reverted. Argue why laziness (PEP 649) won over stringification (PEP 563). Your answer must
address what stringification broke (runtime access to annotations as objects), what laziness preserves,
and the cost each imposes.

---

## 24.8 Summary and cross-references

- **PEP 649 (3.14)** makes annotations **lazy**: the compiler builds an **`__annotate__`** function
  instead of evaluating annotations at `def`/class time, so a forward reference or an undefined name no
  longer raises at definition time.
- This is the same lazy-scope machinery as **PEP 695**'s `type` statement (Chapter 18), generalized to
  all annotations, and it is the cause of the version differences flagged in Chapters 12 and 16.
- **`annotationlib`** exposes three formats: **`VALUE`** (real objects, raises on missing names),
  **`FORWARDREF`** (a `ForwardRef` for anything unresolvable, never raises), and **`STRING`** (source
  text). `get_type_hints` builds on this.
- PEP 649 **retires** quoted forward references, `from __future__ import annotations`, and many
  `TYPE_CHECKING` guards, and **reduces** the definition-time cost (from 5.6x to 3.5x a bare def) but
  does not zero it: the `__annotate__` function is still built.

**Cross-references.** The forward-reference flip and the cost measurement → Chapters 12 and 16. The lazy
value scope PEP 649 generalizes → Chapter 18. The type system that consumes annotations → Deep I. The
compiler machinery → Deep J. The typed-boundary seams to Books I and III → Deep I.
