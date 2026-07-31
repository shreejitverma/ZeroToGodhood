"""Listing 282.1 - Python 3.10-3.12: 'Did you mean' suggestions in error messages.

A typo in a name used to give a bare 'NameError: name 'x' is not defined' - true,
unhelpful, and the fix (you meant 'y') was left entirely to you. Starting in 3.10
and extended through 3.12, CPython computes the CLOSEST valid name to the one you
mistyped and appends 'Did you mean: ...?' to the error - for undefined names,
missing attributes, and failed imports. It turns a dead-end message into a
pointer at the fix. This is the clearest user-facing payoff of the compiler
knowing more about your program. Deep J owns the interpreter that produces these;
this chapter shows the suggestions on current interpreters. To stay path-
independent it prints only the exception type and the suggestion text, never the
file paths some messages include. Verified on current interpreters.
"""

import traceback


def last_line(fn):
    try:
        fn()
    except Exception:
        return traceback.format_exc().splitlines()[-1]


def suggestion_of(fn):
    """Return (exception type, the 'Did you mean...' clause) - no file paths."""
    line = last_line(fn)
    kind = line.split(":", 1)[0]
    marker = "Did you mean:"
    clause = line[line.index(marker):] if marker in line else "(no suggestion)"
    return kind, clause


def main() -> None:
    print("--- a mistyped NAME suggests the closest defined name ---")
    def name_typo():
        collections_length = 5
        return collections_lenght                # transposed letters
    kind, clause = suggestion_of(name_typo)
    print(f"  {kind} -> {clause}")
    print("  the interpreter compared the undefined 'collections_lenght' to the")
    print("  names in scope and found 'collections_length' one edit away. the")
    print("  bare 'not defined' now comes with the likely fix attached")

    print("--- a missing ATTRIBUTE suggests the closest real attribute ---")
    class Config:
        def __init__(self):
            self.timeout = 30
            self.retries = 3
    kind, clause = suggestion_of(lambda: Config().timeut)
    print(f"  {kind} -> {clause}")
    print("  Config has no 'timeut', but it has 'timeout' - so the AttributeError")
    print("  points you there. this catches the everyday obj.atribute typo the")
    print("  moment it runs, with the answer in the message")

    print("--- string/builtin methods get suggestions too ---")
    kind, clause = suggestion_of(lambda: "hi".uppr())
    print(f"  {kind} -> {clause}")
    print("  'hi'.uppr() suggests .upper(). the suggestion pool includes the")
    print("  type's real methods, so a misremembered method name is corrected")
    print("  for builtins as well as your own classes")

    print("--- a bad IMPORT name suggests the right one ---")
    def import_typo():
        from math import sqt                     # meant sqrt
    kind, clause = suggestion_of(import_typo)
    print(f"  {kind} -> {clause}")
    print("  importing 'sqt' from math suggests 'sqrt'. (the full message also")
    print("  names the module's file path, which we omit here so the output is")
    print("  the same on every machine - the SUGGESTION itself is what matters)")

    print("--- no close match means no misleading suggestion ---")
    def no_match():
        return zzzzzz                            # nothing like it in scope
    kind, clause = suggestion_of(no_match)
    print(f"  {kind} -> {clause}")
    print("  when nothing is within a small edit distance, no 'Did you mean' is")
    print("  offered - the interpreter does not guess wildly. suggestions appear")
    print("  only when there is a genuinely close candidate")

    print("--- the constraint answered ---")
    print("  a name/attribute/import typo gave a technically-true but dead-end")
    print("  error and left the fix to you. from 3.10 through 3.12 CPython finds")
    print("  the closest valid name and appends 'Did you mean: ...?', so the")
    print("  error points at the correction. it is the compiler's extra knowledge")
    print("  of your program turned into a better message")


if __name__ == "__main__":
    main()
