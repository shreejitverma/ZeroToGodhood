"""Listing 285.1 - Python 3.13 (2024): warnings.deprecated, one way to mark deprecations.

Deprecating an API means telling users 'this still works, but stop using it' - at
BOTH runtime (a DeprecationWarning when they call it) and check time (a static
warning in their editor/CI). People did these separately: a manual
warnings.warn() call inside the function for runtime, and a docstring note or
type-checker-specific hack for static. Python 3.13's PEP 702 added a single
decorator, warnings.deprecated(msg): put it on a function or class and it BOTH
emits the runtime DeprecationWarning AND is understood by type checkers as a
deprecation marker. One annotation, both audiences. Deep I owns the type system
that reads it statically; this is the release that unified how you deprecate.
Verified on current interpreters.
"""

import warnings


@warnings.deprecated("use new_api() instead")
def old_api(x):
    return x * 2


def new_api(x):
    return x * 2


@warnings.deprecated("use Modern instead")
class Legacy:
    def __init__(self, value):
        self.value = value


def main() -> None:
    print("--- calling a @deprecated function still works, but warns ---")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = old_api(21)
    print(f"  old_api(21) returned : {result}   (it still WORKS)")
    print(f"  it emitted a warning : {len(caught) == 1}")
    print(f"  warning category : {caught[0].category.__name__}")
    print(f"  warning message  : {str(caught[0].message)!r}")
    print("  the function runs normally - deprecation does not break callers -")
    print("  but every call raises a DeprecationWarning carrying your message.")
    print("  no manual warnings.warn() inside the body; the decorator does it")

    print("--- the message is yours: say what to use instead ---")
    print("  the decorator argument becomes the warning text, so you point users")
    print("  at the replacement ('use new_api() instead'). a good deprecation")
    print("  always names the migration path, and this puts it in the warning")

    print("--- classes can be deprecated too: instantiation warns ---")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        obj = Legacy(5)
    print(f"  Legacy(5).value : {obj.value}   (still constructs)")
    print(f"  constructing it warned : {len(caught) == 1}")
    print(f"  message : {str(caught[0].message)!r}")
    print("  putting @deprecated on a CLASS warns when it is instantiated, so a")
    print("  whole type can be phased out with the same one-line marker")

    print("--- the decorator also sets a marker attribute for tools ---")
    print(f"  old_api.__deprecated__ : {old_api.__deprecated__!r}")
    print("  besides the runtime warning, the decorator records the message on")
    print("  __deprecated__, which a static type checker reads to flag USES of")
    print("  the deprecated API in the editor and CI (Deep I) - before the code")
    print("  ever runs. one annotation serves both the runtime and the checker")

    print("--- the payoff: one marker for both audiences ---")
    print("  before PEP 702 you wrote a warnings.warn() in the body (runtime")
    print("  only) AND separately signalled the checker somehow. @deprecated is")
    print("  a single decorator that BOTH warns at runtime AND is understood")
    print("  statically - no drift between what the code does and what tools see")

    print("--- the constraint answered ---")
    print("  deprecating an API meant two disconnected signals: a hand-written")
    print("  runtime warning and a separate static hint. warnings.deprecated")
    print("  (3.13, PEP 702) is one decorator on a function or class that emits")
    print("  the DeprecationWarning AND marks it for type checkers. deprecation")
    print("  became a single, standard annotation for both runtime and tooling")


if __name__ == "__main__":
    main()
