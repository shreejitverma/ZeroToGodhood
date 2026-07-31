"""Listing 262.1 - Python 3.6 (2016): __init_subclass__, subclass hooks without a metaclass.

Wanting to run code every time a class is SUBCLASSED - to register plugins, to
validate that required attributes are set, to wire up a framework - used to
require a metaclass. Metaclasses are powerful but heavy: they change the type of
your class, compose badly (two metaclasses in one hierarchy conflict), and are
famously hard to reason about. The vast majority of metaclass uses were just
'do something when a subclass is created', which is a sledgehammer for a nail.
Python 3.6's PEP 487 added __init_subclass__: an ordinary classmethod on the
base that the interpreter calls for each new subclass, with no metaclass at all.
Deep C owns metaclasses and the type-creation machinery; this is the release
that made the common subclass hook a plain method. Verified on current
interpreters.
"""


# A plugin registry built with __init_subclass__ - no metaclass in sight.
class Plugin:
    registry = {}

    def __init_subclass__(cls, /, name=None, **kwargs):
        super().__init_subclass__(**kwargs)      # cooperative: always call super
        key = name or cls.__name__.lower()
        Plugin.registry[key] = cls               # runs once, when the subclass is defined


class JsonExporter(Plugin, name="json"):
    pass


class CsvExporter(Plugin):                        # no name= -> defaults to 'csvexporter'
    pass


# A validating base: subclasses MUST define a `columns` attribute.
class Table:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "columns"):
            raise TypeError(f"{cls.__name__} must define `columns`")


class Users(Table):
    columns = ["id", "name"]


def main() -> None:
    print("--- __init_subclass__ runs once per subclass, at definition time ---")
    print(f"  defining JsonExporter and CsvExporter populated the registry:")
    for key, cls in Plugin.registry.items():
        print(f"    {key!r} -> {cls.__name__}")
    print("  the base's __init_subclass__ fired as each subclass was CREATED -")
    print("  no metaclass. registration happens automatically at import time,")
    print("  the moment the subclass statement runs")

    print("--- class keyword arguments are passed to the hook ---")
    print(f"  class JsonExporter(Plugin, name='json') registered under : "
          f"{'json' in Plugin.registry}")
    print(f"  CsvExporter with no name= defaulted to : "
          f"{'csvexporter' in Plugin.registry}")
    print("  the `name='json'` in the class header became a keyword argument to")
    print("  __init_subclass__ - so a subclass can CONFIGURE its own")
    print("  registration declaratively in the class statement")

    print("--- validation: reject a subclass that breaks the contract ---")
    print(f"  Users defined columns, so it was accepted : {Users.columns}")
    try:
        class Broken(Table):                     # no `columns` - should fail
            pass
    except TypeError as exc:
        print(f"  class Broken(Table) with no columns -> TypeError: {exc}")
    print("  __init_subclass__ can ENFORCE that subclasses meet requirements,")
    print("  failing at class-definition time (import) rather than later when a")
    print("  missing attribute would surface as a confusing runtime error")

    print("--- the base class itself does NOT trigger the hook ---")
    print("  __init_subclass__ fires for SUBCLASSES, not for the class that")
    print("  defines it - so Plugin and Table were not registered/validated")
    print(f"  'plugin' in registry (the base) : {'plugin' in Plugin.registry}")
    print("  the hook is about descendants, which is exactly what a registry or")
    print("  a contract wants: apply the rule to those who inherit, not the root")

    print("--- why this beats a metaclass for the common case ---")
    print("  a metaclass changes type(cls) and conflicts when hierarchies mix")
    print("  two of them. __init_subclass__ is a plain classmethod - it composes")
    print("  by cooperative super() calls, needs no metaclass, and reads like")
    print("  ordinary code. reach for a metaclass only when you must alter class")
    print("  CREATION itself, not merely react to it")

    print("--- the constraint answered ---")
    print("  'run code when a class is subclassed' meant a metaclass - heavy,")
    print("  conflict-prone, hard to read - for what was usually a simple hook.")
    print("  __init_subclass__ (3.6) made it a plain classmethod the interpreter")
    print("  calls per subclass, with class-keyword configuration and cooperative")
    print("  super(). registries and contracts stopped needing metaclasses")


if __name__ == "__main__":
    main()
