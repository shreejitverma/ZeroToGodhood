"""Listing 110.1 - object construction: __new__ creates, __init__ initializes.

Calling C(args) is two steps, orchestrated by type.__call__:
  1. __new__(cls, *args) CREATES and returns the new instance (it allocates).
     It is implicitly a staticmethod receiving the class, and normally returns
     super().__new__(cls).
  2. __init__(self, *args) INITIALIZES the already-created instance in place. It
     must return None.
Two consequences shown here: __init__ returning non-None is an error, and if
__new__ returns something that is NOT an instance of cls, __init__ is SKIPPED.
"""


class Trace:
    def __new__(cls, v):
        print(f"  1. __new__  creates the instance (cls = {cls.__name__})")
        return super().__new__(cls)      # allocate; do NOT call __init__ here

    def __init__(self, v):
        print(f"  2. __init__ initializes it (v = {v})")
        self.v = v


class ReturnsForeign:
    def __new__(cls):
        print(f"  ReturnsForeign.__new__ returns a str, not a ReturnsForeign")
        return "not an instance of cls"

    def __init__(self):
        print(f"  ReturnsForeign.__init__ (this must NOT run)")


def main() -> None:
    print("--- C(v) runs __new__ then __init__ ---")
    t = Trace(5)
    print(f"  result: t.v = {t.v}")

    print("--- __new__ is implicitly a staticmethod ---")
    print(f"  type(Trace.__dict__['__new__']) : {type(Trace.__dict__['__new__']).__name__}")

    print("--- if __new__ returns a non-instance of cls, __init__ is SKIPPED ---")
    r = ReturnsForeign()
    print(f"  result: {r!r}   (a str; __init__ never ran)")

    print("--- __init__ must return None ---")
    class BadInit:
        def __init__(self):
            return 42                    # illegal

    try:
        BadInit()
    except TypeError as e:
        print(f"  __init__ returning 42 raises {type(e).__name__} : {'should return None' in str(e)}")

    print("--- the rule ---")
    print(f"  __new__ makes the object (returns it); __init__ sets it up (returns")
    print(f"  None); type.__call__ runs __new__ then, if it got a cls instance, __init__")


if __name__ == "__main__":
    main()
