"""Listing 64.1 - circular imports: a module is registered before its body finishes.

`import X` adds X to sys.modules BEFORE running X's body (Chapter 63), so if X's
body imports Y and Y's body imports X, Y receives a HALF-INITIALIZED X, one whose
later names do not exist yet. Using such a name at import time raises
'partially initialized module ... has no attribute ...'. The fix is to not need
the other module's names AT IMPORT TIME: defer the cross-import into the function
that uses it, by which point both modules are fully loaded. This listing shows the
broken pair failing and the fixed pair working.

circ_bad/: mod_a and mod_b import each other's names at top level (fails).
circ_good/: each defers the cross-import into a function (works).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # code/ on path


def main() -> None:
    print("--- circular import that uses names at import time: FAILS ---")
    try:
        from ch064.circ_bad import mod_a  # noqa: F401
        outcome = "unexpectedly succeeded"
    except AttributeError as e:
        msg = str(e)
        outcome = "AttributeError"
        print(f"  raised              : {outcome}")
        print(f"  is a circular-import error : {'partially initialized' in msg}")
        print(f"  names the missing attr     : {'a_value' in msg}")

    print("--- the fix: defer the cross-import into the function that needs it ---")
    from ch064.circ_good import mod_a as good_a
    print(f"  good_a.combined()   : {good_a.combined()!r}")
    print(f"  both modules load; the import happens at call time, fully initialized")


if __name__ == "__main__":
    main()
