"""Listing 119.1 - __init_subclass__: the lightweight class-creation hook.

__init_subclass__ (PEP 487, Python 3.6) lets a base class run code every time a
SUBCLASS is defined, without a metaclass. It is implicitly a classmethod, receives
the new subclass as cls, and accepts keyword arguments passed in the class header
(class Sub(Base, key='x')). Its canonical use is the REGISTRY / PLUGIN pattern:
a base class automatically collects its subclasses into a lookup table as they are
defined, so a factory can find them by name. This listing builds such a registry.
"""


class Loader:
    registry = {}

    def __init_subclass__(cls, /, key=None, **kwargs):
        super().__init_subclass__(**kwargs)          # cooperative: always call super
        name = key or cls.__name__
        cls.registry[name] = cls                     # auto-register the subclass
        print(f"  registered {cls.__name__} under key {name!r}")


class CsvLoader(Loader, key="csv"):                  # keyword goes to __init_subclass__
    def load(self):
        return "csv data"


class JsonLoader(Loader, key="json"):
    def load(self):
        return "json data"


def main() -> None:
    print("--- (the registrations above ran as each subclass was defined) ---")

    print("--- the base now has a registry of its subclasses ---")
    print(f"  registry keys : {sorted(Loader.registry)}")

    print("--- a factory can look up and instantiate by key ---")
    loader = Loader.registry["csv"]()
    print(f"  Loader.registry['csv']().load() : {loader.load()}")

    print("--- __init_subclass__ runs for EVERY subclass, including grandchildren ---")
    class Base:
        seen = []

        def __init_subclass__(cls, **kw):
            super().__init_subclass__(**kw)
            Base.seen.append(cls.__name__)

    class A(Base):
        pass

    class B(A):                          # grandchild: hook still runs
        pass

    print(f"  subclasses seen : {Base.seen}")

    print("--- the rule ---")
    print(f"  __init_subclass__ runs on the base each time a subclass is defined;")
    print(f"  use it for auto-registration without a metaclass")


if __name__ == "__main__":
    main()
