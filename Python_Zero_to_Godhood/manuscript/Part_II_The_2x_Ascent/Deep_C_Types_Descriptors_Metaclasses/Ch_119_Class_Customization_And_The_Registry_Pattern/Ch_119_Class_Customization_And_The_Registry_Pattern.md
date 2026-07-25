# Chapter 38: Class Customization and the Registry Pattern

Chapter 31 opened Deep C with the most powerful tool for customizing class creation, the metaclass, and immediately warned that it is the most overused.
This chapter, which closes Deep C, is the payoff of that warning: the two *lighter* tools that do most of what people historically reached for metaclasses to do, and do it more simply.
`__init_subclass__` (PEP 487, Python 3.6) lets a base class run code whenever a subclass is defined, without a metaclass.
A **class decorator** lets a function transform a class right after its body runs, `@dataclass` (Chapter 36) is exactly this.
Between them they cover the common cases, auto-registration, validation, attribute injection, so cleanly that a metaclass is now a rare and deliberate choice.

The unifying idea, and the reason this chapter belongs in Deep C, is the **registry pattern**: a base class that automatically collects its subclasses into a lookup table as they are defined, so a factory can create them by name.
This is the backbone of every plugin system, serializer dispatch table, and command router in the Python ecosystem, and `__init_subclass__` makes it a five-line hook instead of a metaclass.
The measurement establishes the fact that makes all of this safe to use freely: class customization runs **once at definition time**, so it adds **zero per-instance cost**, a registered class's objects are exactly as fast as a plain class's.

**This is the canonical home for lightweight class customization and the registry pattern, and the close of Deep C.**
It is the intended default that Chapter 31 (metaclasses) deferred to, uses `__set_name__` from Chapter 32 (descriptors), and completes the volume's arc from "how classes are built" to "how to customize that cleanly".

## Section index

- **38.1** `__init_subclass__`: a hook for every subclass
- **38.2** Class decorators, and the three tools by reach
- **38.3** Measurement: customization is free per instance
- **38.4** Edges and failure modes
- **38.5** Connections
- **38.6** Exercises
- **38.7** Summary and cross-references

Listings live under `code/ch119/` and are re-executed by `make verify` on both verification interpreters.

---

## 38.1 `__init_subclass__`: a hook for every subclass

```python
# code/ch119/l01_init_subclass.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
  registered CsvLoader under key 'csv'
  registered JsonLoader under key 'json'
--- (the registrations above ran as each subclass was defined) ---
--- the base now has a registry of its subclasses ---
  registry keys : ['csv', 'json']
--- a factory can look up and instantiate by key ---
  Loader.registry['csv']().load() : csv data
--- __init_subclass__ runs for EVERY subclass, including grandchildren ---
  subclasses seen : ['A', 'B']
--- the rule ---
  __init_subclass__ runs on the base each time a subclass is defined;
  use it for auto-registration without a metaclass
```

`__init_subclass__` is a hook defined on a *base* class that the interpreter calls **each time a subclass is created**, passing the new subclass as `cls`.
It is implicitly a `classmethod` (you do not write `@classmethod`), and it accepts **keyword arguments passed in the class header**: `class CsvLoader(Loader, key="csv")` sends `key="csv"` to `Loader.__init_subclass__`.
The output shows the registrations firing during the `class CsvLoader...` and `class JsonLoader...` statements, before any instance exists.

This is the **registry pattern** in its cleanest form.
`Loader` keeps a `registry` dict; its `__init_subclass__` adds each new subclass under a key; and a factory then looks up and instantiates by key (`Loader.registry["csv"]()`).
A new loader is registered simply *by being defined as a subclass with a key*, no manual `register(CsvLoader)` call, no decorator, no metaclass, and no way to forget the registration.
This is how plugin systems, serialization dispatch, and command routers are built: define a subclass, and it is automatically available to the factory.

Two mechanics matter.
The hook runs for **every** subclass, including grandchildren (`B(A)` fires it too, the output shows both `A` and `B` collected), because subclass creation is recursive down the hierarchy.
And it must **call `super().__init_subclass__(**kwargs)`**, cooperatively (Chapter 34), so that multiple bases with their own hooks all run and unconsumed keywords propagate, forgetting this breaks the chain exactly as with any cooperative method.

---

## 38.2 Class decorators, and the three tools by reach

```python
# code/ch119/l02_class_decorators.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a class decorator modifies the class at definition ---
  Point(1, 2)   : Point(x=1, y=2)
  Person('ann') : Person(name='ann')
--- it is NOT inherited: a subclass is not re-decorated ---
  Point3D(1, 2, 3) uses inherited repr : Point3D(x=1, y=2, z=3)
--- the three tools, by reach ---
  class decorator   : one class, explicit, not inherited (e.g. @dataclass)
  __init_subclass__ : every subclass of a base, inherited (registries)
  metaclass         : class creation itself, most powerful (Chapter 31)
--- the rule ---
  prefer the lightest tool that works: class decorator for one class,
  __init_subclass__ for a family, metaclass only when neither suffices
```

A **class decorator** is a function that receives a class (after its body has executed) and returns a class, usually the same one, modified.
`auto_repr` injects a `__repr__` and returns the class; `@dataclass` is the canonical real example, it reads the fields and adds methods.
The decorator runs **once**, at the point of definition, and applies to **that one class explicitly**.

The output highlights the defining difference from `__init_subclass__`: a class decorator is **not inherited**.
`Point3D(Point)` uses the `__repr__` that the decorator put on `Point` (inherited normally through the MRO), but the decorator itself did **not** run for `Point3D`, if `Point3D` needed its own decoration, you would decorate it explicitly.
This is exactly the right tool when you want to customize *specific* classes you name, and the wrong tool when you want every member of a family customized automatically.

So Deep C's class-customization tools form a spectrum by **reach**:

- **Class decorator**: customizes **one class**, explicitly, at its definition. Not inherited. Simplest. (`@dataclass`, `@functools.total_ordering`.)
- **`__init_subclass__`**: customizes **every subclass** of a base, automatically, inherited. The registry/plugin tool. Middle weight.
- **Metaclass** (Chapter 31): controls **class creation itself**, can change the namespace, the bases, the type. Most powerful, heaviest, and the one to avoid unless the other two genuinely cannot express what you need.

The rule that closes the volume: **prefer the lightest tool that works.**
Reach for a class decorator to shape a named class, `__init_subclass__` to shape a family, and a metaclass only when you must intervene in class creation itself (a framework that must control the namespace, or combine with an existing metaclass like `ABCMeta`).
Chapter 31 gave you the metaclass; this chapter tells you to want it last.

---

## 38.3 Measurement: customization is free per instance

The worry with any "magic at class definition" is that it slows the objects down. It does not, and knowing why frees you to use these patterns liberally.

**Methodology.** `code/ch119/bench_registration.py`.
Instance construction for a class with an auto-registering `__init_subclass__` versus a plain class, `min` of 5 runs, 5,000,000 constructions.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| instance construction | ns/instance | vs plain |
|---|---|---|
| plain class | ~50 | 1.0x |
| auto-registered class | ~50 | **~1.0x** |

Instance construction of the registered class is **the same speed** as the plain class, the measured ratio clusters around 1.0x across runs (0.88x to 1.09x, i.e. pure run-to-run noise, the two are structurally identical objects).
The reason is the timing of the hook.
`__init_subclass__` ran **once**, when the class was *defined*, to register it, and never runs again.
The instances it governs carry no trace of it: they are ordinary objects of an ordinary class, constructed by an ordinary `__init__`.
The one-time class-creation cost is negligible (microseconds, paid once per class definition, at import), and the per-instance cost is **zero**.

This generalises to all three tools.
A class decorator, `__init_subclass__`, and a metaclass all do their work at **class-definition time** and then step out of the way, the resulting class and its instances run at full speed.
So a plugin registry, a validation hook, an attribute-injection decorator, or a framework metaclass adds nothing to the runtime cost of the objects it governs; the cost is a one-time definition-time expense, incurred at import, not in the hot path.
This is the final instance of Deep C's recurring theme: the object model's customization machinery is paid for *once, at the boundary of class creation*, exactly like `@dataclass`'s code generation (Chapter 36) and the type method cache (Chapter 34), so you can build expressive, self-organizing class hierarchies without a per-object tax.
Customize freely; the objects stay fast.

---

## 38.4 Edges and failure modes

**Always call `super().__init_subclass__(**kwargs)`.** §38.1.
It is a cooperative method (Chapter 34). Skipping it breaks multi-base hooks and leaves keyword arguments unconsumed. Accept and forward `**kwargs`.

**Class decorators are not inherited; `__init_subclass__` is.** §38.2.
Decorate each class that needs it; use `__init_subclass__` when you want every subclass covered automatically. Choosing the wrong one gives "only the base is customized" or "I have to decorate every subclass" surprises.

**A registry holds strong references.**
An `__init_subclass__` registry keeps every subclass alive forever (a strong reference in the dict). This is usually fine (classes live for the program), but a system that dynamically creates and discards classes will leak them. Use a `WeakValueDictionary` if classes are transient.

**`__init_subclass__` runs before the subclass body's decorators.**
The hook sees the class as the `class` statement produced it, *before* any class decorator on the subclass runs. If registration depends on decorator-added attributes, order matters, prefer the decorator, or re-check in it.

**Keyword arguments in the class header go only to `__init_subclass__` (and the metaclass).**
`class Sub(Base, key="x")` passes `key` to `__init_subclass__`; it is not a base class or an attribute. A typo'd keyword that no hook consumes raises `TypeError`.

**Class decorators that return a *new* class break identity and `super()`.**
A decorator that constructs and returns a different class (rather than modifying and returning the original) can break `super()` in methods (which may reference the original class) and any `isinstance`/identity assumptions. Prefer modifying and returning the same class; `@dataclass(slots=True)` is a rare deliberate exception (it must create a new class to add slots, Chapter 36).

**Metaclass conflicts.**
Combining a class using `__init_subclass__` with a class using a metaclass is fine, but combining *two different metaclasses* is a `TypeError` (Chapter 31). `__init_subclass__` avoids this class of problem, another reason to prefer it.

**Do not put per-instance logic in class hooks.** §38.3.
These hooks run per *class*, not per *instance*. Instance-time validation belongs in `__init__`/`__post_init__` or a descriptor's `__set__`, not in `__init_subclass__`.

---

## 38.5 Connections

**Backward.**
`__init_subclass__` is the lightweight alternative to the metaclass of Chapter 31 (which Chapter 31 itself pointed toward), and its cooperative `super()` call is Chapter 34. Class decorators are the mechanism behind `@dataclass` (Chapter 36) and `@total_ordering` (Chapter 24). `__set_name__` (Chapter 32) is the descriptor-side companion hook that fires at the same class-creation moment. This chapter closes Deep C by resolving its opening tension: powerful metaclasses versus simple hooks, in favour of the hooks.

**Forward.**
The import-time cost of class customization (it runs at module import) connects to the import system (**Deep G**) and startup-time concerns. Entry-point-based plugin discovery (setuptools/importlib.metadata), the packaging-level cousin of the in-process registry, is a **Deep** packaging topic. Registries combined with ABCs (Chapter 35) for typed plugins are a common composition.

**Across books.**
The registry pattern is how **Book I** builds extensible systems: a `Strategy`, `Indicator`, `DataSource`, or `MessageType` base with `__init_subclass__` auto-collects every implementation as it is defined, so adding a new strategy is *just defining a subclass*, and a factory dispatches by name off the registry. The order-book system registers its message types and event handlers this way, so decoding dispatches on a type code to the right registered class, and, per §38.3, this self-organizing structure costs nothing at runtime: the registration happened at import, and the millions of messages it routes are plain fast objects. Deep C ends where **Book I** begins, with an object model expressive enough to make the domain's structure declarative and cheap.

---

## 38.6 Exercises

**1. Build a registry.** Reproduce §38.1: a base with `__init_subclass__` that registers subclasses by a header keyword, and a factory that instantiates by key. Add a third subclass and confirm it appears automatically. Explain why no manual registration call is needed.

**2. Decorator versus hook.** Reproduce §38.2's `auto_repr` decorator and show it is not inherited. Then reimplement the same `__repr__` injection with `__init_subclass__` and show it *is* inherited. Explain when each is the right choice.

**3. Cooperative hooks.** Build two base classes, each with an `__init_subclass__`, and a class inheriting both. Show that both hooks run only if each calls `super().__init_subclass__()`. Break one and observe the failure.

**4. Measure the freedom.** Reproduce §38.3. Confirm registered instances construct at plain speed. Then measure the one-time class-creation cost of the hook and explain the "once at import, zero per instance" split.

**5. The design question.** Python offers three tools for class customization (decorator, `__init_subclass__`, metaclass) of increasing power. Argue why having the lighter two matters (what did people misuse metaclasses for that PEP 487 replaced), and give one task that genuinely still needs a metaclass. Defend the "prefer the lightest tool" rule using §38.3.

---

## 38.7 Summary and cross-references

- **`__init_subclass__`** is a base-class hook the interpreter calls for **every subclass** as it is defined (implicitly a classmethod, receives `cls`, accepts class-header keywords). Its canonical use is the **registry / plugin pattern**: subclasses auto-register into a lookup table, so a factory creates them by name. Call `super().__init_subclass__(**kwargs)` cooperatively.
- A **class decorator** transforms **one class** at its definition (like `@dataclass`) and is **not inherited**.
- **Three tools by reach:** class decorator (one class, explicit) < `__init_subclass__` (a family, inherited) < metaclass (class creation itself, Chapter 31). **Prefer the lightest that works**; reach for a metaclass last.
- **Measured:** an auto-registered class's instances construct at **the same speed** as a plain class's (~1.0x, within noise), because customization runs **once at class-definition time** and adds **zero per-instance cost**. The same holds for decorators and metaclasses. Customize freely; the objects stay fast.
- **Edges:** registries hold strong references (use `WeakValueDictionary` for transient classes); hooks run per class, not per instance; class-header keywords go only to `__init_subclass__`/metaclass; decorators returning a new class can break `super()`/identity.

**Cross-references.** Metaclasses (the heavy alternative this defers to) → Chapter 31. Cooperative `super()` → Chapter 34. Class decorators behind `@dataclass`/`@total_ordering` → Chapters 36, 24. `__set_name__` companion hook → Chapter 32. Typed plugin registries with ABCs → Chapter 35. Import-time cost and entry-point plugins → Deep G / packaging.
