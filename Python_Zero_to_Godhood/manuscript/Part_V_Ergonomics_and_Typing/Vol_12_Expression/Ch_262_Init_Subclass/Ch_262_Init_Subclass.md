# Chapter 262: Init Subclass

## The constraint

A recurring need in framework and library code is to *run code whenever a class is subclassed*.
A plugin system wants to register each subclass in a lookup table.
A framework wants to validate that every subclass sets the required attributes.
An ORM wants to wire up a subclass's fields when the model is defined.
In each case, the trigger is the *creation of a subclass*, and something should happen at that moment.

For Python's first quarter-century, the only tool for this was a *metaclass*.
A metaclass is a class whose instances are classes - it lets you intercept class creation itself, so its `__new__` or `__init__` runs when a class is defined.
It works, and it is one of the most powerful features in the language.
It is also heavy and treacherous.
A metaclass changes the *type* of your class, which ripples in surprising ways.
Metaclasses compose badly: if a class inherits from two bases with different metaclasses, Python raises a metaclass conflict, and resolving it means writing a third metaclass that combines them.
And they are famously hard to reason about - "if you have to ask whether you need a metaclass, you don't," as the saying went.

The trouble was that the overwhelming majority of metaclass uses were just "do something when a subclass is created" - a sledgehammer wielded for a nail.
The constraint Python 3.6 (2016, PEP 487) answered: **provide a plain, composable hook for the common case - run code per subclass - so that registries, validators, and simple frameworks no longer need a metaclass at all.**

This is a two-track chapter.
Metaclasses and the full type-creation machinery are Deep Volume C's subject.
What this chapter owns is the release: the day the common subclass hook became an ordinary method.

## What shipped

`__init_subclass__` is a classmethod (implicitly) defined on a base class that the interpreter calls automatically for each new subclass, passing along any class-level keyword arguments.
No metaclass is involved.
Listing 262.1 builds a plugin registry and a validating base with it, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- __init_subclass__ runs once per subclass, at definition time ---
  defining JsonExporter and CsvExporter populated the registry:
    'json' -> JsonExporter
    'csvexporter' -> CsvExporter
  the base's __init_subclass__ fired as each subclass was CREATED -
  no metaclass. registration happens automatically at import time,
  the moment the subclass statement runs
--- class keyword arguments are passed to the hook ---
  class JsonExporter(Plugin, name='json') registered under : True
  CsvExporter with no name= defaulted to : True
  the `name='json'` in the class header became a keyword argument to
  __init_subclass__ - so a subclass can CONFIGURE its own
  registration declaratively in the class statement
--- validation: reject a subclass that breaks the contract ---
  Users defined columns, so it was accepted : ['id', 'name']
  class Broken(Table) with no columns -> TypeError: Broken must define `columns`
  __init_subclass__ can ENFORCE that subclasses meet requirements,
  failing at class-definition time (import) rather than later when a
  missing attribute would surface as a confusing runtime error
--- the base class itself does NOT trigger the hook ---
  __init_subclass__ fires for SUBCLASSES, not for the class that
  defines it - so Plugin and Table were not registered/validated
  'plugin' in registry (the base) : False
  the hook is about descendants, which is exactly what a registry or
  a contract wants: apply the rule to those who inherit, not the root
--- why this beats a metaclass for the common case ---
  a metaclass changes type(cls) and conflicts when hierarchies mix
  two of them. __init_subclass__ is a plain classmethod - it composes
  by cooperative super() calls, needs no metaclass, and reads like
  ordinary code. reach for a metaclass only when you must alter class
  CREATION itself, not merely react to it
--- the constraint answered ---
  'run code when a class is subclassed' meant a metaclass - heavy,
  conflict-prone, hard to read - for what was usually a simple hook.
  __init_subclass__ (3.6) made it a plain classmethod the interpreter
  calls per subclass, with class-keyword configuration and cooperative
  super(). registries and contracts stopped needing metaclasses
```

## Why each part answers the constraint

**It runs per subclass, automatically.**
The first block shows the registry populating itself: defining `JsonExporter` and `CsvExporter` caused `Plugin.__init_subclass__` to fire for each, registering them.
No metaclass, no manual registration call - the hook runs at the moment the `class` statement executes, so registration happens automatically at import time.
This is the plugin-registry pattern that previously justified a metaclass, now written as a plain method.

**Class keyword arguments configure the hook.**
The second block shows a capability PEP 487 added alongside the hook: keyword arguments in the class header.
`class JsonExporter(Plugin, name="json")` passes `name="json"` to `__init_subclass__`, so the subclass configures its own registration declaratively in the class statement, while `CsvExporter` with no `name=` falls back to a default.
This makes the class header a place to declare per-subclass configuration, cleanly.

**It can validate and reject.**
The third block shows enforcement: `Table.__init_subclass__` checks that each subclass defines `columns`, so `Users` (which does) is accepted and `Broken` (which does not) raises `TypeError` *at class-definition time*.
This is the validation pattern, and the timing matters: the error fires when the module is imported, not later when a missing `columns` attribute would surface as a confusing runtime failure far from its cause.

**The base itself is exempt.**
The fourth block shows an important detail: `__init_subclass__` fires for *subclasses*, not for the class that defines it, so `Plugin` and `Table` are not themselves registered or validated.
This is exactly right for registries and contracts - the rule applies to those who inherit, not to the root that defines the rule.

**It composes where metaclasses conflict.**
The fifth block states why this beats a metaclass for the common case.
A metaclass changes `type(cls)` and conflicts when a hierarchy mixes two of them; `__init_subclass__` is a plain classmethod that composes through cooperative `super().__init_subclass__(**kwargs)` calls, needs no metaclass, and reads like ordinary code.
The guidance is clear: use `__init_subclass__` to *react* to class creation, and reserve a metaclass for the rare case where you must *alter* class creation itself.

## The two-track note

Metaclasses, `type.__new__`, the descriptor `__set_name__` hook that PEP 487 added as a companion, and the full mechanics of class creation are Deep Volume C's to develop.
`__init_subclass__` sits on top of that machinery as the friendly, composable entry point for the most common use.
What the timeline records is the release act: in 3.6, PEP 487 added `__init_subclass__` (and `__set_name__`), moving the common subclass hook out of metaclass territory.
The modern consequence, verified above, is that plugin registries, subclass validators, and declarative frameworks are written with a plain classmethod - and metaclasses have retreated to the genuinely advanced cases they are actually needed for.

## Where this lands

`__init_subclass__` is a study in giving a hard tool an easy alternative for its common use.
Reach for it whenever you need to react to subclass creation - registering plugins, validating that subclasses meet a contract, wiring up framework machinery - and remember to call `super().__init_subclass__(**kwargs)` so hooks compose cooperatively along the inheritance chain.
Use class keyword arguments to let subclasses configure themselves declaratively.
Fall back to a metaclass only when you must change how the class object itself is built, not merely respond to its creation.
Deep Volume C explains the metaclass machinery underneath; this chapter is the record of the release that made the common subclass hook a plain method.
