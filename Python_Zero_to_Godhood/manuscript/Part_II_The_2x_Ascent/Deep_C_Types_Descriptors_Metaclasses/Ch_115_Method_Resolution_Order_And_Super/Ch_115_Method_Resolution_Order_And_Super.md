# Chapter 34: Method Resolution Order and `super()`

Every attribute lookup so far has quietly assumed an answer to a question this chapter finally asks: when a class has *several* ancestors, which one provides an inherited attribute?
The lookup order of Chapter 21 said "search along the MRO" without saying what the MRO *is*.
Here it is: the **method resolution order** is a single linear list of a class and all its ancestors, computed by the **C3 linearization** algorithm, and every attribute lookup walks it left to right and takes the first match.
For single inheritance the MRO is obvious (child, parent, grandparent, `object`).
For multiple inheritance, especially the diamond, it is not obvious at all, and getting it right is what lets Python have multiple inheritance without the ambiguities that sink it in other languages.

The MRO also settles the single most misunderstood construct in Python: **`super()` does not mean "call the parent class".**
It means "call the next class in the MRO after this one", and in a diamond the "next class" can be a *sibling* you do not inherit from directly, chosen by the runtime type of `self`.
That redefinition is what makes **cooperative multiple inheritance** work: every class calls `super().method()`, and the calls chain through the entire diamond exactly once each, in MRO order.
Understanding this turns `super()` from a source of baffling bugs into a precise tool.

**This is the canonical home for the MRO and `super()`.**
It completes the attribute-lookup story of Chapter 21 (the order the search walks), builds on Chapter 4 (2.2 unified the type hierarchy that C3 linearizes) and Chapter 32 (descriptor lookup walks this same MRO), and underpins the abstract base classes and mixins of the rest of Deep C.

## Section index

- **34.1** The MRO and C3 linearization
- **34.2** `super()` follows the MRO, not the parent
- **34.3** Measurement: MRO depth does not slow method calls
- **34.4** Edges and failure modes
- **34.5** Connections
- **34.6** Exercises
- **34.7** Summary and cross-references

Listings live under `code/ch115/` and are re-executed by `make verify` on both verification interpreters.

---

## 34.1 The MRO and C3 linearization

```python
# code/ch115/l01_mro_diamond.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the diamond's MRO (C3 linearization) ---
  D.__mro__ : ['D', 'B', 'C', 'A', 'object']
--- lookup walks the MRO and takes the first match ---
  D().who() : B   (B: first in the MRO to define who, not A)
--- C3 preserves local precedence: B before C because D(B, C) ---
  D lists bases (B, C), so B precedes C in the MRO
--- an INCONSISTENT hierarchy cannot be linearized: TypeError ---
  class Bad(X, Y) -> TypeError (inconsistent MRO): True
--- the rule ---
  the MRO is one linear order of a class and its ancestors (C3);
  lookup takes the first match; inconsistent hierarchies are rejected
```

The classic **diamond**: `D` inherits from `B` and `C`, both of which inherit from `A`.
Its MRO is `[D, B, C, A, object]`, and attribute lookup walks that list and stops at the first class defining the name, so `D().who()` returns `"B"`, not `"A"`, `B` comes before `A` in the MRO.
C3 computes this order to satisfy three constraints simultaneously:

1. **Children before parents**: `D` before `B`/`C`, `B`/`C` before `A`, `A` before `object`.
2. **Local precedence**: the order bases are listed in is preserved, `D(B, C)` puts `B` before `C`.
3. **Monotonicity**: the MRO is consistent with the MROs of all bases, so a subclass never reorders what its parents established.

Crucially, `A` appears **once**, after *both* `B` and `C`.
This is C3's key property: a shared ancestor is visited a single time, after everything that inherits from it, which is what makes the diamond well-behaved (a naive depth-first order would visit `A` before `C`, breaking the "children before parents" rule for `C`).

When no ordering can satisfy all three constraints, the class **cannot be created**.
`class Bad(X, Y)` where `Y(X)` is such a case: listing `X` before `Y` demands `X` precede `Y`, but `Y(X)` demands `Y` precede `X`, a contradiction, and Python raises `TypeError` at class-creation time rather than silently picking one.
This fail-fast behaviour is a feature: an inconsistent hierarchy is a design error, and C3 catches it when the class is defined, not when a method is called.

---

## 34.2 `super()` follows the MRO, not the parent

```python
# code/ch115/l02_cooperative_super.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the MRO of the diamond ---
  LR.__mro__ : ['LR', 'L', 'R', 'Base', 'object']
--- super() walks that MRO: LR -> L -> R -> Base ---
  LR().m() : LR->L->R->Base
--- the key point: L.super() reaches R, which is L's SIBLING ---
  inside L.m, super() is R (the next in LR's MRO), NOT L's parent Base
  proof: calling m on an L alone skips R entirely ->
  L().m() : L->Base   (here super() after L is Base; no R in this MRO)
--- so super() is runtime-type-dependent, not static-parent ---
  same L.m source, different super() target depending on the MRO it runs in
--- the rule ---
  super() = the next class in type(self).__mro__ after the current one;
  have every class in a diamond call super().m() for a single clean chain
```

Here is the redefinition that fixes everyone's mental model.
`super()` inside a method of class `X`, called on an object of type `T`, means **"the next class after `X` in `T`'s MRO"**, not "`X`'s base class".
`LR().m()` produces `LR->L->R->Base`: `LR.m` calls `super().m()` which reaches `L`, `L.m` calls `super().m()` which reaches **`R`**, and `R.m` calls `super().m()` which reaches `Base`.

Look at the middle step.
Inside `L.m`, `super()` reaches `R`, but `L` does **not** inherit from `R`, they are siblings, both children of `Base`.
`L`'s "parent" is `Base`, yet `super()` in `L.m` went to `R`, because `R` is what comes after `L` in `LR`'s MRO (`[LR, L, R, Base]`).
The proof is the last line: calling `m` on a plain `L()` gives `L->Base`, `R` is skipped entirely, because in `L`'s own MRO (`[L, Base, object]`) the class after `L` is `Base`.
**The same `L.m` source code calls a different `super()` target depending on the MRO it runs inside.**

This is exactly what makes **cooperative multiple inheritance** work, and why the discipline is "every class in the hierarchy calls `super().method()`".
If each class does its part and then delegates via `super()`, the call threads through *all* of them, each exactly once, in MRO order, with no class needing to know its siblings.
Mixins depend on this: a `LoggingMixin.save` that does its logging and calls `super().save()` composes with any base `save`, because `super()` finds whatever is next in the *concrete* class's MRO.
Break the discipline, one class calls `Base.method(self)` directly instead of `super().method()`, and you skip part of the chain or call a class twice, which is the source of the classic "my mixin's method ran twice / never ran" bugs.

---

## 34.3 Measurement: MRO depth does not slow method calls

Resolving an inherited method is, in principle, an O(depth) walk of the MRO. Intuition says deep inheritance is therefore slow to call. Intuition is wrong.

**Methodology.** `code/ch115/bench_mro.py`.
A method defined on `Root`, called through a subclass 1 hop away versus one 20 hops away (empty subclasses in between, so the method stays on `Root`).
`min` of 5 runs, 10,000,000 calls.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| `obj.m()`, `m` inherited from `Root` | ns/call | vs shallow |
|---|---|---|
| shallow (MRO length 3, `m` 1 hop up) | 21.1 | 1.0x |
| deep (MRO length 22, `m` 20 hops up) | 21.2 | **1.01x** |

A method inherited from **20 classes up** costs the **same** as one from a direct parent (1.01x, and 0.99x on 3.14.6).
The reason is caching.
CPython maintains a **type method cache**: the first lookup of `m` on a type does the O(depth) MRO walk, but the result is cached on the type, so subsequent lookups are O(1), and the specializing interpreter (**Deep H**) turns a hot `obj.m()` into a type-guarded fast path that skips even that.
The depth is paid once, at first call (or cache invalidation), not on every call.

The lesson is a calibration, not a licence.
Deep and wide inheritance hierarchies have real costs, they are hard to understand, fragile under the C3 constraints of §34.1, and prone to the cooperative-`super()` bugs of §34.2, so "prefer composition over deep inheritance" remains sound advice.
But **per-call method-lookup speed is not among those costs**: you do not need to flatten a hierarchy for performance, and a mixin five levels deep does not call more slowly than one at the top.
This matters because it removes a *wrong* reason to avoid clean layered designs (fear of lookup cost) while leaving the *right* reasons (comprehensibility, correctness) fully in force. As throughout, measure before assuming the object model's flexibility costs speed; here, the cache makes it free.

---

## 34.4 Edges and failure modes

**`super()` is the MRO successor, not the parent.** §34.2.
Reasoning about `super()` as "my base class" breaks in diamonds. Always think "next in `type(self).__mro__`".

**Cooperative inheritance requires *every* class to call `super()`.** §34.2.
One class that calls `Base.method(self)` directly, or forgets to call `super()`, breaks the chain (a class is skipped or double-called). All participants must cooperate, including consistent method signatures.

**Inconsistent hierarchies fail at class creation.** §34.1.
A `TypeError: Cannot create a consistent MRO` is a design error surfaced early. Reorder bases or restructure; do not try to force it.

**`super().__init__()` and mismatched signatures.**
Cooperative `__init__` chains require compatible signatures (often `*args, **kwargs` passed through) so each class can consume its arguments and forward the rest. A mixin whose `__init__` takes a positional argument the next class does not expect breaks the chain. `object.__init__` takes no extra args, the chain's terminus.

**`super(Class, obj)` explicit form.**
The zero-argument `super()` works only inside a method (the compiler injects the class and `self`). The explicit `super(Class, obj)` is needed outside that context (a function, a dynamically built method), and getting the first argument wrong (passing the wrong class) reroutes the MRO walk. Prefer the zero-arg form.

**Mixin order determines behaviour.**
Because the MRO is left-to-right over bases, `class C(MixinA, MixinB, Base)` and `class C(MixinB, MixinA, Base)` can behave differently (which mixin's cooperative method runs first). Order mixins deliberately, most-derived-override first.

**`__mro__` is fixed at class creation.**
You cannot change a class's MRO after creation (it is computed once). Changing bases dynamically is not supported for the MRO; design the hierarchy up front.

**Method cache invalidation has a (small) cost.** §34.3.
Assigning to a class attribute (`C.m = ...`) invalidates the type method cache and any specialized call sites, so runtime monkeypatching of methods is not free (Chapter 20's edge). Define methods at class-creation time.

---

## 34.5 Connections

**Backward.**
The MRO is the "search along the MRO" that Chapter 21's attribute-lookup order left unspecified, and descriptor lookup (Chapter 32) walks this same list. Chapter 4's 2.2 type/class unification created the single `object`-rooted hierarchy that C3 linearizes (before it, there was no uniform MRO). The type method cache that flattens §34.3 is the same caching that Chapter 20's dunder dispatch relies on.

**Forward.**
Abstract base classes (`abc`, `__subclasshook__`, virtual subclasses) and how `isinstance`/`issubclass` interact with the MRO are later in Deep C. Mixins as a design pattern, and `@dataclass` with inheritance, are Deep C ergonomics. The type method cache internals and `LOAD_METHOD`/`LOAD_ATTR` specialization that make §34.3 O(1) are **Deep H**.

**Across books.**
Cooperative `super()` and predictable MRO are how **Book I** composes cross-cutting behaviour without rewriting classes: a `TimestampedMixin`, a `SerializableMixin`, and a `ValidatedMixin` layer onto a domain base, each doing its part and delegating via `super()`, so a concrete class picks the mixins it needs and the MRO threads them correctly. The order-book system uses shallow, deliberate mixins for cross-cutting concerns (auditing, serialization) on its message and event types, relying on the §34.2 cooperative chain, and it keeps hierarchies shallow for comprehensibility, not speed, because §34.3 shows depth is not the bottleneck.

---

## 34.6 Exercises

**1. Predict the MRO.** For a diamond `D(B, C)` with `B(A)`, `C(A)`, write out the MRO by hand using C3's three constraints, then check against `D.__mro__`. Then add a class `E(C, B)` and explain why its MRO differs from `D`'s.

**2. Trace the cooperative chain.** Reproduce §34.2's diamond with prints in each `m`. Confirm the `LR->L->R->Base` order. Then break it: make `L.m` call `Base.m(self)` directly instead of `super().m()`, and show which class gets skipped. Explain using the MRO.

**3. Build a failing hierarchy.** Construct three classes whose combination C3 cannot linearize, and confirm the `TypeError` at class creation. Explain which two constraints conflict.

**4. Measure depth.** Reproduce §34.3. Then measure the *first* call (cold cache) versus steady-state for the deep chain, and show the depth cost appears once. Explain the type method cache.

**5. The design question.** Python chose C3 linearization and cooperative `super()` over simpler schemes (depth-first, or forbidding multiple inheritance). Argue what C3 buys (the single-visit diamond, fail-fast on inconsistency) and what it costs (the §34.2 "super is not the parent" learning curve, the signature-compatibility burden). Would forbidding multiple inheritance (like Java, with interfaces only) have been the better call? Defend your answer using the mixin use case.

---

## 34.7 Summary and cross-references

- The **MRO** is a single linear order of a class and its ancestors, computed by **C3 linearization**, which guarantees children-before-parents, preserved base order, and monotonicity, with each ancestor visited **once**. Attribute lookup walks it left to right and takes the first match.
- An **inconsistent hierarchy cannot be linearized** and raises `TypeError` at class creation (fail-fast).
- **`super()` is the next class in `type(self).__mro__` after the current one, not "the parent".** In a diamond it can reach a *sibling*, chosen by the runtime type, which is what makes **cooperative multiple inheritance** work when every class calls `super().method()`.
- **Measured:** a method inherited from **20 hops up** costs the same as one from a direct parent (1.01x), because the **type method cache** makes lookup O(1) after the first call. Deep inheritance has real costs; per-call lookup speed is not one.
- **Edges:** all classes must cooperate (call `super()`, compatible signatures); mixin order matters; the MRO is fixed at creation; monkeypatching methods invalidates the cache.

**Cross-references.** The attribute-lookup order this completes → Chapter 21. Descriptor lookup along the MRO → Chapter 32. Type/class unification (the single hierarchy) → Chapter 4. Dunder dispatch and the method cache → Chapter 20. ABCs, `isinstance`/`issubclass`, mixins → Deep C. Method-cache internals and call specialization → Deep H.
