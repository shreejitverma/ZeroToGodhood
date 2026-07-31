# Chapter 265: Postponed Annotations

## The constraint

Python's type annotations (introduced in 3.5, the subject of Deep Volume I) are, by default, *ordinary expressions evaluated when the `def` or `class` statement runs*.
Writing `def f(x: SomeType)` executes `SomeType` at definition time and stores the resulting object in the function's `__annotations__`.
That default caused two persistent pains.

First, **forward references**.
If an annotation named a type that was not yet defined - a method annotating its own enclosing class, or two classes that reference each other - evaluating it at definition time raised `NameError`.
The workaround was to *quote* the annotation as a string: `nxt: "Node"`.
This worked but was ugly and easy to forget, and it made annotations a special case where sometimes you wrote the type and sometimes you wrote its name in quotes.

Second, **runtime cost**.
Annotations are, overwhelmingly, read by *type checkers* - static tools that never run your code - and almost never inspected at runtime.
Yet eager evaluation charged every annotation its cost at import time: `x: list[int]` ran `list[int]` when the module loaded, for information most programs never look at.
For annotation-heavy code, this was real import-time overhead spent producing objects nobody would read.

The constraint Python 3.7 (2018, PEP 563) answered: **stop evaluating annotations at definition time - store them as strings, resolved lazily only if something asks - so forward references just work and annotations cost nearly nothing at import.**
It shipped opt-in, via `from __future__ import annotations`.

This is a two-track chapter.
The type system itself - what annotations mean, how checkers use them, generics and the typing vocabulary - is Deep Volume I's subject.
What this chapter owns is the release: the day annotations were decoupled from runtime evaluation.

## What shipped

With `from __future__ import annotations` at the top of a module, *all* annotations in that module are stored as strings (their source text) rather than evaluated objects, and `typing.get_type_hints` resolves them to real objects on demand.
Listing 265.1 shows this on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- annotations are stored as STRINGS, not evaluated objects ---
  process.__annotations__ : {'items': 'list[int]', 'factor': 'float', 'return': 'dict[str, int]'}
  the 'items' annotation is a str : True
  with `from __future__ import annotations`, def did NOT evaluate
  list[int] etc. - it stored the SOURCE TEXT. no runtime cost, and no
  requirement that the annotated types even be resolvable yet
--- forward / self references work WITHOUT quotes ---
  built a linked pair : a.value=1 -> nxt.value=2
  Node.__init__ annotates its own type `Node` : 'Node'
  `nxt: Node` inside Node's own body would be a NameError under
  eager evaluation (Node is not defined yet at that point). as a
  string it is fine - the classic reason you used to write 'Node'
--- get_type_hints resolves the strings to real types on demand ---
  get_type_hints(process)['items'] : list[int]
  it is the actual type object now : True
  the strings are not useless: tools (and you) resolve them to real
  objects with typing.get_type_hints when needed. lazy by default,
  evaluated only when something actually inspects the types
--- the payoff: annotations cost nothing at import unless read ---
  under eager evaluation, every `x: SomeType` runs SomeType at
  def-time - import cost for information usually only a type checker
  reads. as strings, that work is deferred to whoever (if anyone)
  actually calls get_type_hints - near-zero runtime overhead
--- the trade-off to know ---
  code that inspects annotations at RUNTIME (some dataclass-like or
  validation libraries) must call get_type_hints to resolve strings,
  and needs the names in scope when it does. that is why the string
  behaviour stayed OPT-IN rather than becoming the unconditional default
--- the constraint answered ---
  eager annotations forced quoted forward references and charged
  import-time cost for type info most code never reads. PEP 563
  (`from __future__ import annotations`, 3.7) stores annotations as
  strings: forward refs just work, import cost drops, and
  get_type_hints resolves them on demand. types decoupled from runtime
```

## Why each part answers the constraint

**Annotations become strings.**
The first block shows `process.__annotations__` holding `'list[int]'`, `'float'`, `'dict[str, int]'` - the *source text*, not the evaluated objects.
The `def` did not run `list[int]`; it stored the string.
This means no runtime cost at definition and no requirement that the annotated types even be resolvable at that point.

**Forward references work without quotes.**
The second block shows `Node.__init__` annotating its own type `Node` - `nxt: Node` inside `Node`'s own body.
Under eager evaluation this would be a `NameError`, because `Node` is not yet defined at the point its `__init__` is compiled; that is exactly why programmers used to write `nxt: "Node"`.
With postponed evaluation the annotation is already a string, so the forward reference just works, unquoted.
The linked pair builds correctly, and the stored annotation is `'Node'`.

**`get_type_hints` resolves on demand.**
The third block shows the strings are not a dead end: `typing.get_type_hints(process)` evaluates them to real type objects, so `hints['items']` *is* `list[int]`.
The design is lazy by default - the source text is kept until something actually needs the resolved types, at which point a tool (or your own code) resolves them explicitly.

**The import-cost payoff.**
The fourth block states the performance benefit.
Eager evaluation charges every `x: SomeType` its cost at definition time, producing objects that usually only a static type checker would read.
Storing strings defers that work to whoever calls `get_type_hints`, if anyone ever does - so annotations add near-zero runtime overhead, which matters for large, annotation-dense codebases.

**The trade-off that kept it opt-in.**
The fifth block is honest about the cost.
Libraries that inspect annotations *at runtime* - some dataclass-like frameworks, some validation libraries - must call `get_type_hints` to resolve the strings, and the names must be in scope when they do.
This runtime-introspection friction is why the string behavior stayed opt-in via `from __future__ import annotations` rather than becoming the unconditional default, a decision that was debated and deferred across several releases.

## The two-track note

What annotations *mean* - the type system, generics like `list[int]`, how checkers consume `__annotations__`, the relationship between runtime objects and static types - is Deep Volume I's to develop.
PEP 563 is orthogonal to that meaning: it changes *when* annotations are evaluated (never, unless asked), not *what* they express.
What the timeline records is the release act: in 3.7, `from __future__ import annotations` made annotations lazy strings, solving forward references and import cost in one move, with `typing.get_type_hints` as the resolution path.
The modern consequence, verified above, is that annotation-heavy code opts into the future import to get free forward references and cheaper imports, while runtime-introspection libraries account for the string form - a tension that shaped the long, careful discussion about whether and when this behavior should become the default.

## Where this lands, and the close of Expression

Postponed annotation evaluation is a subtle release with a clear practical payoff: forward references without quotes, and annotations that no longer cost import time.
Add `from __future__ import annotations` to modules with heavy annotations or mutual/self type references - it makes the types read naturally and the imports stay cheap.
Remember that any code inspecting annotations at runtime must resolve the strings with `typing.get_type_hints` (with the relevant names in scope), which is the one adjustment the change requires.
Deep Volume I explains what the annotations mean; this chapter is the record of the release that decoupled writing them from evaluating them.

This closes Volume 12, Expression.
The volume's thesis - *declaring intent, not steps* - runs through its chapters: f-strings and dataclasses (Chapters 12-13) let you state what you want rather than how to assemble it, and around them 3.6-3.7 delivered a cluster of ergonomic wins - the `secrets` module, `__init_subclass__`, `breakpoint()`, module `__getattr__`, and postponed annotations here.
Part V continues with Deep Volume I, the type system that annotations serve, before Volume 13 pays down the debt that typing and the old parser had accumulated.
