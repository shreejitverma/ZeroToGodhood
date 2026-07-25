"""Listing 122.1 - finalization: __del__'s pitfalls and weakref.finalize's reliability.

Cleaning up at end of life (closing a handle, releasing a resource) has three tools:
  - __del__: runs when the refcount hits zero (Chapter 31), but it is FRAGILE. An
    exception inside __del__ is SWALLOWED (printed to stderr, not raised), its timing
    is unspecified for objects in cycles, and it can resurrect the object.
  - weakref.finalize(obj, func, *args): a RELIABLE finalizer. It runs func exactly
    once, when obj is collected OR at interpreter exit, is idempotent, and reports
    whether it has run (.alive). It does NOT keep obj alive.
  - context managers (with): deterministic cleanup by construction (the best default).
This listing shows __del__'s swallowed exception and weakref.finalize's guarantees.
"""

import io
import weakref
from contextlib import redirect_stderr


class Fragile:
    def __del__(self):
        raise ValueError("error in __del__")     # will be swallowed


def cleanup(name):
    print(f"  finalize ran: cleaning up {name}")


def main() -> None:
    print("--- __del__ pitfall: an exception in __del__ is SWALLOWED ---")
    captured = io.StringIO()
    with redirect_stderr(captured):
        f = Fragile()
        del f                                     # __del__ raises, but to stderr only
    swallowed = "ValueError" in captured.getvalue()
    print(f"  the ValueError went to stderr, not raised : {swallowed}")
    print(f"  program continued normally             : True")

    print("--- weakref.finalize: a reliable, once-only finalizer ---")
    class Resource:
        def __init__(self, name):
            self.name = name

    r = Resource("db")
    fin = weakref.finalize(r, cleanup, "db")
    print(f"  finalize registered, alive : {fin.alive}")
    print("  del r (drops the last reference):")
    del r                                         # finalize runs NOW
    print(f"  finalize alive after del   : {fin.alive}   (it ran)")

    print("--- weakref.finalize is idempotent: calling again does nothing ---")
    r2 = Resource("cache")
    fin2 = weakref.finalize(r2, cleanup, "cache")
    fin2()                                        # call explicitly
    result = fin2()                               # second call: no-op, returns None
    print(f"  second explicit call returned : {result}   (already finalized)")

    print("--- the rule ---")
    print(f"  prefer 'with' for deterministic cleanup; use weakref.finalize for")
    print(f"  reliable at-collection cleanup; avoid __del__ (fragile, swallows errors)")


if __name__ == "__main__":
    main()
