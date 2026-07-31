"""Listing 229.1 - Python 2.3 (2003): the bool type, and why it subclasses int.

Before 2.3, truth was just 1 and 0. Comparisons returned 1/0, there was no
`True`/`False`, and `if x == 1` and `if x` blurred together. PEP 285 added a
real `bool` type with two singletons, True and False - but made a deliberate,
much-debated choice: bool SUBCLASSES int, so True IS 1 and False IS 0. That
kept every old program working (code that did arithmetic on comparison results
still ran) while giving truth a name and a type. The subclassing is the whole
story: it is why True + True == 2, why isinstance(True, int), and why you must
never write `if x == True`. Deep A owns the type/subtype model; this is the
release that gave truth a type without breaking the decade of code that treated
it as a number. Verified on current interpreters.
"""


def main() -> None:
    print("--- True and False are singletons of a real type ---")
    print(f"  type(True)  : {type(True).__name__}")
    print(f"  True, False : {True}, {False}")
    print("  before 2.3 there was no True/False - comparisons returned 1 and 0")
    print("  and you wrote your own True, False = 1, 0. PEP 285 made them a type")

    print("--- the deliberate choice: bool is a SUBCLASS of int ---")
    print(f"  issubclass(bool, int) : {issubclass(bool, int)}")
    print(f"  isinstance(True, int) : {isinstance(True, int)}")
    print(f"  True == 1  : {True == 1}   (True IS 1)")
    print(f"  False == 0 : {False == 0}   (False IS 0)")
    print("  PEP 285 made bool subclass int so that a DECADE of code treating")
    print("  truth as 1/0 kept working unchanged. backward compatibility was")
    print("  the reason, and it is why the two values equal 1 and 0 exactly")

    print("--- the consequence: True and False do arithmetic ---")
    print(f"  True + True       : {True + True}   (1 + 1)")
    print(f"  sum([True, False, True, True]) : {sum([True, False, True, True])}")
    votes = [True, False, True, True, False]
    print(f"  counting Trues by sum() : {sum(votes)} of {len(votes)}")
    print("  because True IS 1, sum() over booleans COUNTS them - a genuinely")
    print("  useful idiom (how many predicates held?), and a direct consequence")
    print("  of the subclassing, not a coincidence")

    print("--- the trap the subclassing creates: never compare == True ---")
    x = 3
    print(f"  x = 3")
    print(f"  bool(x)     : {bool(x)}   (3 is truthy)")
    print(f"  x == True   : {x == True}   (3 == 1 is False!)")
    print(f"  x is True   : {x is True}   (3 is not the True singleton)")
    print("  `if x == True` asks '== 1', so a truthy 3 FAILS it. write `if x`")
    print("  (truthiness) - never `== True`. the subclassing is exactly why the")
    print("  comparison misleads: True is 1, and 3 != 1")

    print("--- truthiness: any object answers bool(), not just True/False ---")
    print(f"  bool(0), bool(''), bool([]), bool(None) : "
          f"{bool(0)}, {bool('')}, {bool([])}, {bool(None)}")
    print(f"  bool(42), bool('x'), bool([0]) : "
          f"{bool(42)}, {bool('x')}, {bool([0])}")
    print("  `if x` calls x.__bool__() (Deep A): empty/zero/None are falsy,")
    print("  everything else truthy. bool the TYPE named the two answers; the")
    print("  PROTOCOL lets every object give one. that is why `if seq:` is the")
    print("  Pythonic emptiness test, not `if len(seq) == 0`")

    print("--- the constraint answered ---")
    print("  before 2.3, truth had no name - just 1 and 0. PEP 285 gave it a")
    print("  type with two singletons, but subclassed int so every program")
    print("  that did arithmetic on comparisons kept working. that one design")
    print("  choice explains all of bool's behaviour: names for truth, full")
    print("  compatibility, sum-counts-Trues, and the `== True` trap")


if __name__ == "__main__":
    main()
