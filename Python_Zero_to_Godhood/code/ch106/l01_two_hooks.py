"""Listing 106.1 - the two attribute hooks: __getattribute__ and __getattr__.

Ordinary attribute access (x.foo, distinct from the special-method dispatch of
Chapter 20) is governed by two hooks with very different timing:
  - __getattribute__(self, name) runs on EVERY attribute access. It is the whole
    algorithm; object.__getattribute__ is the default implementation.
  - __getattr__(self, name) runs ONLY when normal lookup FAILS (would raise
    AttributeError). It is the fallback, the place to synthesize missing names.
This listing shows both: a class that resolves class and instance attributes
normally, and falls back to __getattr__ only for names that do not exist.
"""


class T:
    x = "class-x"                      # a class attribute

    def __init__(self):
        self.y = "instance-y"          # an instance attribute

    def __getattr__(self, name):
        # only reached when x.<name> would otherwise raise AttributeError
        return f"__getattr__ fallback for {name!r}"


def main() -> None:
    t = T()

    print("--- normal lookup resolves existing names; __getattr__ not consulted ---")
    print(f"  t.x  (class attribute)    : {t.x}")
    print(f"  t.y  (instance attribute) : {t.y}")

    print("--- a MISSING name falls through to __getattr__ ---")
    print(f"  t.z  (no such attribute)  : {t.z}")

    print("--- __getattr__ fires only on failure, so it is free for hits ---")
    class Count:
        def __init__(self):
            self.a = 1

        def __getattr__(self, name):
            print(f"    __getattr__ called for {name!r}")
            raise AttributeError(name)

    c = Count()
    print(f"  c.a (exists) : {c.a}   (no __getattr__ line printed)")
    try:
        c.missing
    except AttributeError:
        print(f"  c.missing    : raised AttributeError (after the __getattr__ line)")

    print("--- the rule ---")
    print(f"  __getattribute__ runs on every access; __getattr__ only on a miss")


if __name__ == "__main__":
    main()
