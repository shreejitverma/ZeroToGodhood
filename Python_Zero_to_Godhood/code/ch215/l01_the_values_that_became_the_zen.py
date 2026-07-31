"""Listing 215.1 - the values present from 1989, codified as the Zen in 2004.

The design values that defined Python - readability, explicitness, one obvious
way, practicality - were present in the 1989 fix-list (Chapter 1) long before
Tim Peters distilled them into the Zen of Python (PEP 20, 2004). The Zen POST-
dates the values; it did not create them. This listing shows the Zen itself
(it ships in the interpreter, `import this`), then demonstrates two values as
running CONSEQUENCES rather than slogans: 'explicit is better than implicit'
in how names resolve, and 'errors should never pass silently' in how the
language forces a choice. Verified on current interpreters - the values are
observable behaviour, not marketing.
"""

import io
import contextlib


def main() -> None:
    print("--- the Zen ships in the interpreter (PEP 20, 2004) ---")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        import this                      # prints the Zen as a side effect
    zen = buf.getvalue()
    lines = [ln for ln in zen.splitlines() if ln.strip()]
    print(f"  'import this' prints {len(lines)} aphorisms")
    print(f"  first : {lines[1]!r}")
    print(f"  last  : {lines[-1]!r}")
    print("  the Zen is a 2004 distillation (Tim Peters) of values present in")
    print("  the 1989 design - it codified them, it did not invent them")

    print("--- 'explicit is better than implicit': names resolve by rule ---")
    x = "module-level"

    def outer():
        x = "enclosing"

        def inner():
            return x                     # reads the enclosing x, by the LEGB rule
        return inner()
    print(f"  a name resolves to the nearest ENCLOSING binding : {outer()!r}")
    print(f"  no implicit global fallback surprise here        : {x!r}")
    print("  Python resolves names by an explicit rule (local, enclosing,")
    print("  global, builtin) - not by an implicit 'whatever is in scope'.")
    print("  explicitness is a VALUE with a mechanism (Chapter 75, Deep H)")

    print("--- 'errors should never pass silently': the language insists ---")
    try:
        result = 1 / 0
    except ZeroDivisionError as exc:
        result = f"raised {type(exc).__name__}"
    print(f"  1/0 does not return 0 or NaN silently : {result}")
    print(f"  {{}}['missing'] raises, not returns None :", end=" ")
    try:
        {}['missing']
    except KeyError:
        print("KeyError")
    print("  a language that returned a default on error would be 'convenient'")
    print("  and wrong; Python raises, because a silent error is a bug you")
    print("  find in production instead of at the call site (Deep O's whole")
    print("  discipline rests on this value)")

    print("--- the value, and the volume ---")
    print("  every release in the timeline that follows answers a constraint")
    print("  WITHOUT abandoning these values: readability, explicitness, one")
    print("  obvious way. when a feature would violate them (implicit magic,")
    print("  a second obvious way) it is argued for years or rejected - which")
    print("  is why Python's history is slow, deliberate, and coherent")


if __name__ == "__main__":
    main()
