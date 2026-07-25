"""Listing 111.2 - the singletons, and why 'is None' beats '== None'.

Python has a handful of singleton objects: exactly one None, one True, one False,
one Ellipsis (...), one NotImplemented. Because there is only one of each, you test
for them with IDENTITY (is), not equality (==). For None this matters two ways:
  - Correctness: == calls __eq__, which a class can override (or get wrong for
    None), while 'is None' is an unforgeable identity check nothing can intercept.
  - Speed: 'is' is a pointer comparison; '== None' dispatches __eq__ (benchmark).
This listing shows the singletons and a class whose broken __eq__ makes '== None'
lie while 'is None' stays correct.
"""


class BrokenEq:
    """__eq__ that wrongly claims equality to anything, including None."""

    def __eq__(self, other):
        return True                      # pathological, but legal


def main() -> None:
    print("--- the singletons: exactly one object each ---")
    print(f"  None is None       : {None is None}")
    print(f"  Ellipsis is ...    : {Ellipsis is ...}")
    print(f"  NotImplemented is NotImplemented : {NotImplemented is NotImplemented}")
    print(f"  type(None) : {type(None).__name__}   type(...) : {type(...).__name__}")

    print("--- 'is None' is correct even when __eq__ lies ---")
    b = BrokenEq()
    print(f"  b == None : {b == None}   (wrong: __eq__ returns True for anything)")
    print(f"  b is None : {b is None}   (correct: b is not the None object)")

    print("--- so a None check must use identity ---")
    value = BrokenEq()
    got_none_wrongly = (value == None)   # would take the wrong branch
    got_none_correctly = (value is None)
    print(f"  '== None' would say None : {got_none_wrongly}")
    print(f"  'is None' says None      : {got_none_correctly}")

    print("--- the rule ---")
    print(f"  test singletons (None, True, False, ..., NotImplemented) with 'is',")
    print(f"  never '=='; 'is None' cannot be fooled by __eq__ and is faster")


if __name__ == "__main__":
    main()
