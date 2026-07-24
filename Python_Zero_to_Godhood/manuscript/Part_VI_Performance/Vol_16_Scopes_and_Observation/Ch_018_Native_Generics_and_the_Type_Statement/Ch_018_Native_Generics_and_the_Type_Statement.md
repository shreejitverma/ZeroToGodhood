# Chapter 18: Native Generics and the `type` Statement (Python 3.12)

PEP 695 looks like syntax sugar. `def first[T](xs: list[T]) -> T` instead of a `TypeVar` on the
line above, `class Box[T]` instead of `class Box(Generic[T])`, `type Alias = ...` instead of an
assignment. Three cosmetic wins, and most coverage of 3.12 stops there.

It is not sugar. To make that syntax work the compiler grew a new kind of scope, one whose body
does not run when the surrounding code runs, and which follows different name-resolution rules than
any other scope in the language. That machinery is the actual content of PEP 695, it is why the
feature could not have been a library, and in Python 3.14 it turned out to be the foundation
someone else needed: PEP 649's deferred annotations are built on the same mechanism, generalised.

This chapter is about the scope, not the syntax.

## Section index

- **18.1** The problem: a type that mentions itself
- **18.2** The model: an alias is an object with a deferred body
- **18.3** Mechanism I: what the compiler emits for `type X = ...`
- **18.4** Mechanism II: the type-parameter scope
- **18.5** Mechanism III: the class-scope exception, and why it exists
- **18.6** What the lazy scope forbids, and why
- **18.7** Variance stops being something you declare
- **18.8** The 3.14 convergence: PEP 695 meets PEP 649
- **18.9** Measurement: what the syntax costs
- **18.10** Edges and failure modes
- **18.11** Connections
- **18.12** Exercises
- **18.13** Summary and cross-references

All listings in this chapter live under `code/ch18/` and are re-executed by `make verify` on both
verification interpreters. Output blocks are transcribed from `code/ch18/expected/`.

---

## 18.1 The problem: a type that mentions itself

Write the type of a JSON document. It is a string, a number, a boolean, null, a list of JSON
documents, or a dictionary of strings to JSON documents. The definition is recursive, which is
fine, because JSON is recursive.

Now write it in Python before 3.12:

```python
JSONValue = Union[None, bool, int, float, str, list["JSONValue"], dict[str, "JSONValue"]]
```

The quotes are the problem, and they are not a stylistic wart. At the moment that line executes,
the name `JSONValue` is not yet bound, so the interpreter cannot evaluate it. The only way to
mention it is to hand the type checker a *string* and let the checker resolve it later. The runtime
gets a `str` and no way to know it was meant to be a type.

The same defect shows up without recursion, wherever a type is mentioned before it exists: two
modules that reference each other's types, a factory annotated with a class defined below it, a
protocol whose method returns the protocol. Every one forces the same workaround, and the
workarounds compound: `if TYPE_CHECKING:` blocks that import for the checker but not the runtime,
`from __future__ import annotations` to stringify everything, and `typing.get_type_hints()` calls
that re-`eval()` those strings against whatever globals the caller can supply, failing when the
name lived in a different module's namespace.

Here is the pre-695 idiom, run:

```python
# code/ch18/l02_laziness.py (excerpt)
from typing import TypeAlias, Union

OldTree: TypeAlias = "list[Union[OldTree, int]]"
print("type(OldTree)       =", type(OldTree).__name__)
print("OldTree             =", OldTree)
```

Verified output (CPython 3.13.5):

```text
type(OldTree)       = str
OldTree             = list[Union[OldTree, int]]
it is a str; resolving it is the type checker's problem, or eval()'s
```

A `str`. Not a type, not a wrapper around a type, not anything the runtime can introspect. Three
separate mechanisms had grown up to paper over this: string annotations, `__future__` stringifying,
and `TYPE_CHECKING` guards. PEP 695's premise is that all three exist because the language had no
way to say *"evaluate this expression later, in the namespace where it was written."*

So it added one.

---

## 18.2 The model: an alias is an object with a deferred body

The mental model is one sentence: **a PEP 695 type alias is an object that holds an unevaluated
function, and asking for its value calls that function once and caches the answer.**

Everything else follows. Because the body is a function, it can be written before the names it
mentions exist. Because it is called on demand, it resolves against the namespace as it stands at
that moment, not at definition time. Because the result is cached, the deferral costs nothing after
the first access.

Start with what the three forms actually leave behind:

```python
# code/ch18/l01_three_forms.py
type Alias = list[int]

def fn[T](x: T) -> T:
    return x

class Box[T]:
    def __init__(self, v: T) -> None:
        self.v = v
```

Verified output (CPython 3.13.5):

```text
--- the type alias is an object, not a name for another object ---
type(Alias)           = <class 'typing.TypeAliasType'>
Alias.__name__        = Alias
Alias.__value__       = list[int]
Alias.__type_params__ = ()
--- functions and classes grow a __type_params__ slot ---
fn.__type_params__    = (T,)
Box.__type_params__   = (T,)
--- Generic is added to the bases for you ---
Box.__bases__         = (<class 'typing.Generic'>,)
Box.__mro__           = (<class '__main__.Box'>, <class 'typing.Generic'>, <class 'object'>)
--- the implicitly created TypeVar ---
type(T)               = <class 'typing.TypeVar'>
T.__name__            = T
T.__bound__           = None
T.__constraints__     = ()
T.__covariant__       = False
T.__contravariant__   = False
T.__infer_variance__  = True
```

Three things to notice. `Alias` is a `TypeAliasType`, a real object with a `__name__` and a
`__value__`, not a second name for `list[int]`. `Box` was given `typing.Generic` as a base without
being asked. And the `T` in `fn[T]` produced an ordinary `typing.TypeVar`, so PEP 695 did not
invent a new type-parameter object; it invented a new way to *create* the existing one.

The `__infer_variance__` flag reading `True` is the one genuinely new behaviour on that object, and
§18.7 covers it.

Now the deferral, which is the whole point:

```python
# code/ch18/l02_laziness.py
type Tree = list[Tree | int]          # self-referential, unquoted, Tree not yet bound
type UsesLater = list[DefinedLater]   # class does not exist yet
type Broken = list[NeverDefined]      # will never exist

class DefinedLater:
    pass
```

Verified output (CPython 3.13.5):

```text
--- all three aliases were defined without error ---
no exception raised at definition time
--- forcing evaluation resolves against the CURRENT module namespace ---
Tree.__value__      = list[Tree | int]
UsesLater.__value__ = list[__main__.DefinedLater]
--- an unresolvable alias fails at access time, not definition time ---
NameError: name 'NeverDefined' is not defined
--- the computed value is cached: the lazy scope runs at most once ---
Tree.__value__ is Tree.__value__ -> True
```

`Tree` refers to itself without quotes. `UsesLater` refers forward to a class defined three lines
below it. Neither raised. `Broken` raised too, but at the moment someone asked, which is the
correct time for that error: a type alias nobody evaluates is a type alias whose broken reference
nobody needs.

The identity check on the last line matters more than it looks. `Tree.__value__ is Tree.__value__`
returning `True` means the lazy scope is not a property that recomputes. It runs at most once, and
§18.6 demonstrates that directly with a counter.

---

## 18.3 Mechanism I: what the compiler emits for `type X = ...`

**What the interpreter actually does.** A `type` statement is not an assignment. It compiles to a
nested code object plus a single intrinsic call.

```python
# code/ch18/l03_bytecode.py
import dis
code = compile("type Alias = list[int]\n", "<demo>", "exec")
dis.dis(code, depth=0)
```

Verified output (CPython 3.13.5):

```text
--- module-level bytecode ---
  0           RESUME                   0
  1           LOAD_CONST               0 ('Alias')
              LOAD_CONST               1 (None)
              LOAD_CONST               2 (<code object Alias at 0xADDR, file "<path>", line 1>)
              MAKE_FUNCTION
              BUILD_TUPLE              3
              CALL_INTRINSIC_1        11 (INTRINSIC_TYPEALIAS)
              STORE_NAME               0 (Alias)
              RETURN_CONST             1 (None)
```

Read the stack: the alias's name, its type parameters (`None`, since this alias has none), and a
**function built from a nested code object**. Those three go into a tuple, and
`CALL_INTRINSIC_1 INTRINSIC_TYPEALIAS` turns the tuple into a `TypeAliasType`.

The value expression `list[int]` does not appear at module level at all. It is inside that nested
code object, and the nested code object is never called here. That is the deferral, and it is
structural: the compiler physically moved the expression somewhere that does not execute.

Disassembling the nested object shows the expression sitting there unevaluated:

```text
--- the nested code object the compiler built for the value ---
co_name    = Alias
co_argcount= 0
co_flags   = 0x3
--- disassembly of the lazy value scope ---
  1           RESUME                   0
              LOAD_GLOBAL              0 (list)
              LOAD_GLOBAL              2 (int)
              BINARY_SUBSCR
              RETURN_VALUE
```

A zero-argument function that loads two globals, subscripts, and returns. `LOAD_GLOBAL` is the
detail that makes forward references work: the names are resolved when the function is *called*,
against the module's globals as they stand then. Nothing was captured at definition time.

> **Version caveat.** Run this same listing on 3.14 and the lazy scope has a parameter, a
> `NotImplementedError` guard, and different opcodes for the same operations. That is not drift in
> the example; it is PEP 649 arriving. §18.8 explains it, and `make verify` checks both.

---

## 18.4 Mechanism II: the type-parameter scope

A type parameter has to be visible in places that belong to different scopes: the base-class list,
the method signatures, the class body, and any nested aliases. Before PEP 695 this was solved by
making `T` an ordinary module-level name, with the well-known consequence that two unrelated classes
sharing a `TypeVar` object was legal and occasionally load-bearing by accident.

PEP 695 gives the parameters their own scope, wrapped around everything that needs them.

```python
# code/ch18/l04_typeparam_scope.py
code = compile("class Box[T]:\n    def get(self) -> T: ...\n", "<demo>", "exec")
```

Verified output (CPython 3.13.5):

```text
--- module-level bytecode: the class statement calls a function ---
  0           RESUME                   0
  1           LOAD_CONST               0 (<code object <generic parameters of Box> at 0xADDR, file "<path>", line 1>)
              MAKE_FUNCTION
              PUSH_NULL
              CALL                     0
              STORE_NAME               0 (Box)
              RETURN_CONST             1 (None)
--- the code-object tree, with cell and free variables ---
- '<generic parameters of Box>'  argcount=0  cellvars=('.type_params', 'T')  freevars=()
    - 'Box'  argcount=0  cellvars=()  freevars=('.type_params', 'T')
        - 'get'  argcount=1  cellvars=()  freevars=()
```

`class Box[T]` compiles to *calling a function*. That function is
`<generic parameters of Box>`, and the class body is nested inside it. `T` is a **cell variable** in
the outer scope and a **free variable** in the class body, which is to say `T` reaches the class
through an ordinary closure. The generic machinery is built out of a mechanism the language already
had, which is why it composes correctly with everything else.

The `.type_params` cell alongside it is compiler-generated bookkeeping. The leading dot is the
interesting part:

```text
note: '.type_params' is a compiler-generated cell. The leading dot
makes it unspellable in Python source, so it cannot collide with a
name you wrote.
```

A leading-dot name is not a valid identifier, so no user program can shadow or reference it. CPython
uses this trick wherever it needs a private slot in a user-visible namespace; the implicit `.0`
argument in a comprehension's code object is the same idea (Chapter 3).

The practical consequence: **each `class Box[T]` creates a fresh `T`.** Two classes that both write
`[T]` share nothing. That is the fix for the accidental-sharing problem, and it falls out of the
scope rather than being enforced separately.

---

## 18.5 Mechanism III: the class-scope exception, and why it exists

Here is where PEP 695's scope stops resembling anything else in Python.

Ordinary nested scopes **skip the enclosing class body**. A method, a lambda, or a comprehension
inside `class C` cannot see `C`'s class-level names. This is deliberate and long-standing: class
bodies are not closures, and a name defined in a class body is an attribute of the class, not a
variable of an enclosing scope.

```python
# code/ch18/l05_class_scope.py
class Ordinary:
    X = int
    get = lambda self: X
Ordinary().get()
```

Verified output (CPython 3.13.5):

```text
--- ordinary nested scopes: class-level names are invisible ---
lambda in class body     -> NameError: name 'X' is not defined
comprehension in class    -> NameError: name 'X' is not defined
--- a PEP 695 lazy scope in the same position: visible ---
type alias in class body  ->  list[int]
```

The lambda cannot see `X`. The comprehension cannot see `X`. The type alias, in the same position,
**can**.

**Why this exists.** Annotations and aliases inside a class routinely mention names defined in that
class: a nested type, a constant, a related alias. If PEP 695 scopes followed the normal rule, every
such reference would fail, and the feature would be unusable in exactly the place people write the
most types. So the compiler makes an exception, and pays for it with a dedicated opcode:

```text
--- the mechanism: a __classdict__ cell plus LOAD_FROM_DICT_OR_GLOBALS ---
class-body cellvars       = ('__classdict__',)
alias lazy-scope freevars = ('__classdict__',)
name lookup opcodes       = [('LOAD_DEREF', '__classdict__'), ('LOAD_FROM_DICT_OR_GLOBALS', 'list'), ('LOAD_DEREF', '__classdict__'), ('LOAD_FROM_DICT_OR_GLOBALS', 'X')]
```

The class body exports its namespace as a cell named `__classdict__`; the lazy scope closes over
it; and `LOAD_FROM_DICT_OR_GLOBALS` looks a name up in that dictionary first, falling back to
globals. The opcode exists for this purpose and for PEP 649's annotation scopes, which need the same
exception for the same reason.

This is worth holding onto as a general lesson about CPython: when the language needs a scoping rule
that the existing machinery cannot express, the answer is usually a new opcode rather than a new
kind of object. The cost is one entry in the instruction set; the benefit is that everything else,
closures, cells, the frame layout, keeps working unchanged.

---

## 18.6 What the lazy scope forbids, and why

A lazy scope may be evaluated at an arbitrary later moment, or never, or (as §18.8 shows) by tooling
asking for a different representation entirely. Constructs whose entire purpose is a side effect or
a suspension point would have undefined timing under those conditions. The compiler rejects them
outright rather than leaving it to chance.

```python
# code/ch18/l06_scope_limits.py
```

Verified output (CPython 3.13.5):

```text
walrus in an alias       -> SyntaxError: named expression cannot be used within a type alias
yield in a TypeVar bound -> SyntaxError: yield expression cannot be used within a TypeVar bound
await in an alias        -> SyntaxError: await expression cannot be used within a type alias
yield in an alias        -> SyntaxError: yield expression cannot be used within a type alias
```

Note that these are `SyntaxError`s, raised at compile time, with messages naming the specific
construct and the specific scope. The language is not merely declining to define the behaviour; it
is refusing to compile the program.

Ordinary expressions, including calls, remain legal, which lets us watch the caching directly:

```text
--- but ordinary expressions are fine, including calls ---
calls after definition    = 0
value                     = list[int]
calls after first access  = 1
value again               = list[int]
calls after second access = 1 (cached: the scope ran once)
```

Zero calls at definition. One call at first access. Still one at second access. The deferral is
free after the first read, and the function-call cost is paid once per alias per process.

That also means **a side effect in an alias body happens at an unpredictable time, exactly once, or
never**. Do not put one there. The compiler cannot stop you from calling a function, only from
suspending inside one.

---

## 18.7 Variance stops being something you declare

Under the legacy spelling you told the checker whether a type parameter was covariant, and you were
on your own if you got it wrong:

```python
T_co = TypeVar("T_co", covariant=True)
```

Getting that wrong is easy and the consequences are quiet: an unsound covariant parameter on a
mutable container lets the checker accept code that fails at runtime, which is the classic
`list[Dog]` as `list[Animal]` hole (Chapter 16, §16.4). The declaration is also redundant, because
variance is *derivable* from how the parameter is used. A parameter that only appears in return
position is covariant; only in argument position, contravariant; both, invariant. The checker can
see all of that.

PEP 695 parameters are created with `infer_variance=True`, which hands the decision to the tool that
has the information:

Verified output (CPython 3.13.5):

```text
spelling                                           co  contra  infer
--------------------------------------------------------------------
TypeVar('LegacyCo', covariant=True)              True   False  False
TypeVar('LegacyContra', contravariant=True)     False    True  False
TypeVar('LegacyPlain')                          False   False  False
PEP 695  def modern[T]                          False   False   True
```

**The runtime does not enforce variance either way.** That flag is a message to the type checker,
and the listing shows the message being set, not obeyed. This is the gradual-typing boundary again
(Chapter 16, §16.5): the checker guarantees consistency of typed code at build time, and the runtime
guarantees nothing about types at all.

Bounds and constraints are lazy on the same machinery as alias values:

```text
--- bounds and constraints are lazy too ---
the bound referenced an undefined name; definition still succeeded
accessing __bound__ -> NameError: name 'Undefined' is not defined
--- constrained type parameters use a tuple, and are also lazy ---
constraints = (<class 'int'>, <class 'str'>)
bound       = None
```

`def bounded[T: Undefined]` compiles and defines successfully; the `NameError` waits until something
reads `__bound__`. So a bound may refer forward to a class defined later in the module, which is
precisely the recursive-protocol case that needed quoting before.

Note the last two lines: a constrained parameter `[T: (int, str)]` populates `__constraints__` and
leaves `__bound__` as `None`. Bounds and constraints are different features that share a syntactic
slot, and confusing them is a common error. A bound says *"any subtype of this"*; constraints say
*"exactly one of these, and the same one throughout"*.

---

## 18.8 The 3.14 convergence: PEP 695 meets PEP 649

Re-run `l03_bytecode.py` on Python 3.14 and the lazy scope has changed shape:

Verified output (CPython 3.14.6):

```text
--- the nested code object the compiler built for the value ---
co_name    = Alias
co_argcount= 1
co_flags   = 0x3
--- disassembly of the lazy value scope ---
  1           RESUME                   0
              LOAD_FAST_BORROW         0 (.format)
              LOAD_SMALL_INT           2
              COMPARE_OP             132 (>)
              POP_JUMP_IF_FALSE        3 (to L1)
              NOT_TAKEN
              LOAD_COMMON_CONSTANT     1 (NotImplementedError)
              RAISE_VARARGS            1
      L1:     LOAD_GLOBAL              0 (list)
              LOAD_GLOBAL              2 (int)
              BINARY_OP               26 ([])
              RETURN_VALUE
```

The scope now takes an argument, `.format` (another unspellable compiler name), and raises
`NotImplementedError` if that argument exceeds 2. The type alias did not ask for this. **PEP 649
did.**

PEP 649 needed to defer *annotations* for the same reasons PEP 695 deferred alias values, and it
needed more: a tool that cannot resolve a name should still be able to obtain a forward reference,
or the original source text, rather than an exception. So 3.14 generalised the lazy scope into a
protocol with four formats:

```python
# code/ch18/l08_pep649_bridge.py   # requires: 3.14+
type Alias = list[Undefined] | Missing
```

Verified output (CPython 3.14.6):

```text
--- the format protocol ---
Format members = {'VALUE': 1, 'VALUE_WITH_FAKE_GLOBALS': 2, 'FORWARDREF': 3, 'STRING': 4}
--- 3.14 exposes the lazy scope itself ---
Alias.evaluate_value = function
--- the compiler-generated scope only implements VALUE natively ---
  evaluate_value(VALUE      ) -> NameError: name 'Undefined' is not defined
  evaluate_value(FORWARDREF ) -> NotImplementedError  <- 'ask the fallback path'
  evaluate_value(STRING     ) -> NotImplementedError  <- 'ask the fallback path'
```

That `NotImplementedError` is not a failure; it is the protocol working. The compiler emits a scope
that knows how to compute a *value* and nothing else, and signals "I cannot do that format" for the
rest. The library layer supplies the missing formats by re-running the same code object with a fake
globals mapping that turns every name lookup into a recorded reference:

```text
--- the high-level API supplies the fallback, via fake globals ---
  call_evaluate_function(FORWARDREF ) -> ForwardRef("list[ForwardRef('Undefined')] | Missing")
  call_evaluate_function(STRING     ) -> 'list[Undefined] | Missing'
--- which is why repr() of an unresolvable alias still works ---
  repr(Alias) = Alias
--- the identical machinery now backs function annotations ---
  get_annotations(VALUE      ) -> NameError: name 'StillUndefined' is not defined
  get_annotations(FORWARDREF ) -> {'x': ForwardRef('StillUndefined', owner=<function f at 0xADDR>), 'return': ForwardRef('AlsoMissing', owner=<function f at 0xADDR>)}
  get_annotations(STRING     ) -> {'x': 'StillUndefined', 'return': 'AlsoMissing'}
```

The last three lines are the point of this section. `get_annotations` on an ordinary function, with
ordinary annotations, is running the same machinery that `type Alias = ...` introduced two releases
earlier. PEP 695 built a lazy scope for type aliases; PEP 649 recognised it as the general solution
to "evaluate this later, in the namespace where it was written," and made annotations use it.

This is also the answer to a question Chapter 16 leaves open. `from __future__ import annotations`
existed because annotations were evaluated eagerly and that was often wrong. In 3.14 they are lazy
by default, and the `__future__` import is on a path to retirement. The full treatment of PEP 649,
including what it does to `dataclasses` and `get_type_hints`, is **Vol 18** (Python 3.14).

---

## 18.9 Measurement: what the syntax costs

**Methodology.** `code/ch18/bench_pep695.py`, run through `_harness/bench.py`. Fifteen batches of
20,000 operations each, 2,000-operation warm-up, `time.perf_counter`. The reported statistic is
**min**, because microbenchmark noise is one-sided: a scheduler preemption can only make a batch
slower, so the fastest batch is the best estimate of the work itself. Median and relative standard
deviation are reported as diagnostics of how quiet the machine was, not as speed.

Interpreter: CPython 3.13.5, `OPT='-DNDEBUG -O2 -Wall'`, computed gotos on, PGO and LTO on.
Hardware: Apple M3 Pro, 12 cores, 36 GB, macOS 27.0, arm64.

Definition cost of a generic class, `exec` of a pre-compiled code object so that parsing is excluded:

| case | ratio vs plain class |
|---|---|
| `class Box:` (no generics) | 1.0x |
| `class Box(Generic[T]):` (legacy) | about 2.1x |
| `class Box[T]:` (PEP 695) | about 2.7x to 3.0x |

**The PEP 695 form is the slowest of the three to define.** That is the honest result and it is the
direct consequence of §18.4: `class Box[T]` runs an extra function scope, `<generic parameters of
Box>`, before the class body executes. The legacy form does not.

Three caveats on those numbers, all of which matter more than the numbers.

First, **the precision is one decimal place, not two.** Across repeated runs the legacy ratio
reproduced tightly (2.09, 2.11, 2.15) but the PEP 695 ratio moved by about 10% (2.70, 2.80, 2.98).
Citing "2.70x" would be false precision; "about 2.7x" is what the measurement supports.

Second, **this cost is paid once per class, at import time, and never again.** It is not per
instantiation and not per method call. A module defining 100 generic classes pays on the order of
half a millisecond more than it would have under the legacy spelling. For essentially every program
this is not a consideration; for a CLI whose startup time is a feature, it is worth knowing it
exists.

Third, and most important for how you read the rest of this book: **these figures are not comparable
across interpreters.** The 3.13 and 3.14 builds on this machine differ in optimisation level
(`-O2` versus `-O3`) and in whether computed gotos are enabled (on versus off). Computed gotos are
the interpreter's dispatch mechanism, and a build without them is materially slower at exactly the
thing being measured here. Running this benchmark on both and comparing would measure the *builds*.
`make interpreters` reports this, and `_harness/bench.py` refuses to compute cross-interpreter
ratios. To compare CPython versions honestly, build both from source with identical flags.

The alias forms are close enough to be uninteresting for a trivial value:

| case | ratio |
|---|---|
| `A = list[int]` (eager) | 1.0x |
| `type A = list[int]` (lazy) | about 0.9x |

Which is the expected shape rather than a surprise. The lazy form's saving is proportional to how
expensive the deferred value is, and `list[int]` is not expensive. The `type` statement earns its
keep when the value is costly to build or impossible to resolve at definition time, not when it is
a two-name subscript.

---

## 18.10 Edges and failure modes

**Side effects in an alias body run at an unpredictable time, once or never.** §18.6 shows the
counter. The compiler blocks suspension but not calls. Treat an alias body as a pure expression.

**A `NameError` from an alias surfaces far from its cause.** The traceback points at the line that
*read* `__value__`, which is frequently inside `typing` or a checker, not at the alias definition.
When debugging one of these, look at the alias, not at the frame that raised.

**`type X = ...` is not assignable and not the same as `X = ...`.** The `type` statement creates a
`TypeAliasType`; the assignment creates a binding to whatever the right side evaluates to. Code that
introspects `__value__` will break on the assignment form, and code that expects a plain
`types.GenericAlias` will break on the `type` form.

**The class-scope exception does not extend to methods.** A type alias in a class body sees class
names (§18.5). A type alias inside a *method* is in an ordinary function scope and does not. The
exception is one level deep by design.

**Mixing spellings in one class hierarchy is legal and confusing.** A PEP 695 subclass of a legacy
`Generic[T]` base works, but the base's `T` and the subclass's `T` are different objects with
different variance settings. Pick one spelling per hierarchy.

**Backporting is not possible.** The syntax is a parser change, so a 3.12+ source file using it is a
`SyntaxError` on 3.11, not a runtime failure. There is no `__future__` import for it. Libraries
supporting older interpreters must keep the legacy spelling, which is why the ecosystem's migration
is slower than the feature's age suggests.

**On 3.14, `evaluate_value` raising `NotImplementedError` is normal.** If you call the lazy scope
directly rather than through `annotationlib.call_evaluate_function`, you will see it for any format
above 2, and it means "use the fallback path," not "something broke" (§18.8).

---

## 18.11 Connections

**Backward.** The closure machinery that carries `T` into the class body is the cell-and-free-variable
model from Chapter 3. The `.type_params` unspellable-name trick is the same device as a
comprehension's `.0`. The `TypeVar`, `Protocol`, and variance vocabulary this chapter assumes is
Chapter 16, and the eager-annotation cost model this chapter partly overturns is Chapter 16, §16.5.
`class Box[T]` adding `Generic` to `__bases__` goes through the same `__mro_entries__` machinery as
any other base-class transformation (Chapter 4).

**Forward.** The lazy scope is the substrate for PEP 649, so **Vol 18** (Python 3.14) picks this
thread up directly and is the canonical home for deferred annotations. The type system as a
discipline, variance in depth, `TypeIs` and `TypeGuard`, overloads, stubs, and checker behaviour, is
**Deep I** (The Type System), which owns everything this chapter only gestures at. `sys.monitoring`
and the per-interpreter GIL, the other two headline features of 3.12, are the remaining chapters of
this volume.

**Across books.** Generic containers are where Python's type system meets the boundary that
**Book I** owns. A `Box[T]` holding a NumPy array or a buffer-protocol object is typed the same way
regardless of whether its storage is a Python list or a C++ vector reached through `nanobind`, and
the type parameter carries no runtime information across that boundary in either direction. The
buffer-protocol seam and what type information survives it is **Deep M** (The C-API, ABI, and FFI).

---

## 18.12 Exercises

**1. Predict, then verify.** Before running anything, write down what this prints and why:

```python
X = "module"
class C:
    X = "class"
    type A = X
    def m(self):
        type B = X
        return B.__value__
print(C.A.__value__, C().m())
```

The two aliases are three lines apart and resolve differently. Explain the difference in terms of
§18.5, then check yourself. What single opcode accounts for it?

**2. Break the cache.** §18.6 establishes that a lazy scope runs at most once. Construct a case
where the *first* evaluation raises, then the name it needed is defined, then the value is read
again. Does the alias recover, or is the failure cached too? Predict first. Then explain why the
implementation chose that behaviour, in terms of what caching a raised exception would cost.

**3. Measure the import-time cost honestly.** §18.9 reports about 2.7x for a single class
definition. Write a benchmark that generates a module containing *N* generic classes for several
values of *N*, under both spellings, and measure import time. At what *N* does the difference reach
one millisecond? Then argue whether that number should change anyone's code, and state the condition
under which it should.

**4. Find the fourth format.** §18.8 lists four `Format` members and shows three in use.
`VALUE_WITH_FAKE_GLOBALS` is the one the listing never calls directly, and calling it directly is
documented as unsupported. Work out what it does from the behaviour of `call_evaluate_function`, and
explain why the compiler-generated scope raises `NotImplementedError` for formats *above* 2 rather
than for formats *other than* 1.

**5. The design question.** PEP 695 gave type aliases a lazy scope in 3.12. PEP 649 gave annotations
one in 3.14, and generalised the mechanism to do so. Argue the counterfactual: if PEP 649 had landed
first, would PEP 695 have needed to invent anything, or would it have been a pure syntax change over
existing machinery? Cite the specific capability in §18.8's format protocol that PEP 695 does not
use, and say what that tells you about which PEP was solving the harder problem.

---

## 18.13 Summary and cross-references

- A PEP 695 **type alias is an object** (`typing.TypeAliasType`) holding an **unevaluated function**.
  Reading `__value__` calls it once and caches the result, so forward and self references work
  without quotes.
- `type X = ...` compiles to a **nested code object** plus `CALL_INTRINSIC_1 INTRINSIC_TYPEALIAS`.
  The value expression is physically moved into a scope that does not run.
- `class Box[T]` compiles to **calling a function**, `<generic parameters of Box>`, with the class
  body nested inside it. `T` arrives through an ordinary closure. Each such class gets a **fresh**
  type parameter, fixing the accidental-sharing hazard of module-level `TypeVar`s.
- PEP 695 scopes **break the class-scope rule on purpose**: unlike lambdas and comprehensions, they
  can see class-body names, via a `__classdict__` cell and the dedicated
  **`LOAD_FROM_DICT_OR_GLOBALS`** opcode.
- Walrus, `yield`, and `await` are **`SyntaxError`s** inside these scopes, because a scope evaluated
  at an unpredictable time cannot host a suspension point.
- Type parameters are created with **`infer_variance=True`**, moving variance from a declaration you
  can get wrong to an inference the checker makes. The runtime enforces nothing either way.
- In **3.14**, the lazy scope became **PEP 649's annotation evaluator**, gaining a `.format`
  parameter and a four-format protocol. The same machinery now backs ordinary function annotations.
- **Measured:** defining `class Box[T]` costs about **2.7x** a plain class and about **1.3x** the
  legacy `Generic[T]` form, because of the extra scope. Paid once per class at import. Precision is
  one decimal place; the figure is not comparable across differently-configured builds.

**Cross-references.** Closures, cells, and free variables → Chapter 3. `__mro_entries__` and base-class
transformation → Chapter 4. `TypeVar`, `Protocol`, variance, and the gradual-typing boundary →
Chapter 16. Deferred annotations and PEP 649 in full → Vol 18. The type system as a discipline →
Deep I. The C-API boundary and what type information survives it → Deep M.
