# Chapter 264: Module Getattr

## The constraint

Classes had `__getattr__` from the beginning: a hook the interpreter calls when an attribute is *not* found the normal way, letting a class compute attributes lazily, proxy to another object, or shim a renamed attribute with a deprecation warning.
Modules had no equivalent.
Accessing `module.thing` either found a module-level global or raised `AttributeError`, with no way to intercept the lookup.

This gap blocked two genuinely useful patterns.

First, *lazy module attributes*.
A package that exposes a heavy submodule or an expensive-to-build object had to either import/build it eagerly at module load - slowing every import even for programs that never touch it - or expose it awkwardly through a function call.
There was no way to say "compute this module attribute only when someone actually accesses it."

Second, *clean deprecations*.
When a library renamed a module-level name - `MAX_SIZE` to `MAX_LIMIT`, say - it could not make the old name keep working *while warning* the caller to migrate.
The old name either stayed as a duplicate global (no warning, no migration pressure) or was removed (breaking callers immediately).

The constraint Python 3.7 (2018, PEP 562) answered: **extend the missing-attribute hook to modules, so a module can intercept access to names it does not define - enabling lazy attributes and deprecation shims.**

This is a two-track chapter.
The attribute-lookup protocol - how `__getattr__` and `__getattribute__` work, when the hook fires, the descriptor machinery behind attribute access - belongs to Deep Volume C.
What this chapter owns is the release: the day that protocol reached module level.

## What shipped

A module can define a top-level function `__getattr__(name)` (and `__dir__()`), and the interpreter calls it for any attribute not found as a normal module global.
Listing 264.1 uses it for a deprecation shim and a lazy attribute, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- normal attributes never reach __getattr__ ---
  module.VERSION : 2.0   (a real global, found directly)
  __getattr__ fires ONLY for names not found the usual way, exactly
  like the class-level hook. present globals are returned normally,
  so the hook adds no cost to existing attributes
--- a deprecated name is redirected with a warning ---
  module.OldConfig returned : {'mode': 'fast'}   (the current Config)
  and emitted a DeprecationWarning : True
  warning text : 'OldConfig is deprecated; use Config'
  accessing the OLD name still works (redirected to the new one) but
  warns the caller to migrate - a clean deprecation shim that was
  impossible before module __getattr__
--- a lazy attribute is built only on first access ---
  build count before access : 0
  module.expensive_table : {'built': True, 'size': 42}
  build count after access  : 1
  the attribute did not exist as a global; __getattr__ computed it on
  demand. this is how a package lazily imports a heavy submodule only
  when someone actually reaches for it - faster imports by default
--- an unknown name still raises AttributeError, as expected ---
  module.does_not_exist -> AttributeError: module '__main__' has no attribute 'does_not_exist'
  the hook must raise AttributeError for names it does not handle, so
  genuinely missing attributes behave normally - hasattr, getattr
  defaults, and error messages all still work
--- the constraint answered ---
  classes could intercept missing-attribute access; modules could
  not, so lazy module attributes and deprecation shims were
  impossible. PEP 562 (3.7) added module-level __getattr__: a hook
  called for unresolved names, enabling lazy imports and clean
  'renamed, please migrate' warnings without breaking existing access
```

## Why each part answers the constraint

**Normal attributes never reach the hook.**
The first block confirms the hook is the same "missing attribute" mechanism as the class-level one: `module.VERSION`, a real global, is found directly and never touches `__getattr__`.
The hook fires only for names not found the usual way, so it adds no cost to existing attribute access - exactly the behavior that makes it safe to add to a widely-used module.

**Deprecation shims become possible.**
The second block shows the pattern that was previously impossible.
Accessing `module.OldConfig` - a name with no global - triggers `__getattr__`, which emits a `DeprecationWarning` ("OldConfig is deprecated; use Config") and returns the current `Config`.
The old name keeps working, redirected to the new one, *while warning* the caller to migrate.
This is a clean deprecation: no breakage today, clear migration pressure for tomorrow.

**Lazy attributes save import cost.**
The third block shows the lazy pattern.
`expensive_table` does not exist as a global, so accessing it runs `__getattr__`, which builds it on demand - the build counter goes from `0` to `1` only when the attribute is first touched.
This is how a package can expose a heavy submodule or expensive object that is imported or constructed *only when someone actually reaches for it*, keeping imports fast for programs that never use it.

**Missing names still raise.**
The fourth block shows the contract the hook must honor: for names it does not handle, `__getattr__` must raise `AttributeError`.
`module.does_not_exist` raises normally, so `hasattr`, `getattr` with a default, and error messages all continue to work.
The hook extends attribute access without breaking its established semantics.

## The two-track note

The attribute-lookup protocol - the difference between `__getattr__` (called only on failure) and `__getattribute__` (called always), the descriptor machinery, how the module object's `__getattr__` is invoked - is Deep Volume C's to develop.
Module-level `__getattr__` is that protocol applied to the module object, which is itself an ordinary object with a type.
What the timeline records is the release act: in 3.7, PEP 562 gave modules the `__getattr__` and `__dir__` hooks that classes already had.
The modern consequence, verified above, is that lazy imports (the standard library itself uses this to defer heavy submodules) and deprecation warnings on renamed module attributes are standard techniques, and libraries evolve their public module namespaces without abrupt breakage.

## Where this lands

Module-level `__getattr__` closed a small but real asymmetry between classes and modules.
Reach for it to deprecate a module-level name gracefully - redirect the old name to the new one and warn - and to defer expensive imports or object construction until first access, keeping your module's import cheap.
Honor the contract: raise `AttributeError` for names you do not handle, so ordinary attribute semantics keep working.
Pair it with `__dir__` when you want the dynamically-provided names to appear in introspection.
Deep Volume C explains the attribute-lookup protocol underneath; this chapter is the record of the release that extended it to modules.
