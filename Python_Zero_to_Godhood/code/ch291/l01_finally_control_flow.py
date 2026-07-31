# requires: 3.14+
"""Listing 291.1 - Python 3.14 (2025): PEP 765, control flow in finally is now a warning.

Chapter 232 showed that `finally` is the strongest guarantee in the language: it
runs no matter how the block exits. That power has a dark corner - a `return`,
`break`, or `continue` INSIDE a finally block SWALLOWS whatever was happening: a
propagating exception vanishes, and a return value from the try is overridden.
This is almost never what anyone intends; it is a bug that hides real errors.
Python 3.14's PEP 765 makes the compiler emit a SyntaxWarning for return/break/
continue in a finally block, flagging the footgun without breaking the (rare,
deliberate) code that uses it. Deep B owns exception unwinding; this is the
release that turned a silent finally trap into a visible warning. Verified on
3.14 builds.
"""

import warnings


def compile_and_catch(description, source):
    """Compile source, returning the SyntaxWarning it raises (if any)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compile(source, "<demo>", "exec")
    if caught:
        w = caught[0]
        print(f"  {description} -> {w.category.__name__}: {str(w.message)!r}")
    else:
        print(f"  {description} -> no warning")


def main() -> None:
    print("--- `return` in a finally block now warns at compile time ---")
    compile_and_catch(
        "return in finally",
        "def f():\n try:\n  return 1\n finally:\n  return 2\n")
    print("  the compiler flags it as a SyntaxWarning. the code still COMPILES")
    print("  (nothing breaks), but the footgun is now visible instead of silent")

    print("--- break and continue in a finally warn too ---")
    compile_and_catch(
        "break in finally",
        "for i in range(3):\n try:\n  pass\n finally:\n  break\n")
    compile_and_catch(
        "continue in finally",
        "for i in range(3):\n try:\n  pass\n finally:\n  continue\n")
    print("  all three control-flow statements in a finally are flagged, because")
    print("  each hijacks the block's exit and discards whatever was in progress")

    # These buggy functions are built via exec so their (expected) SyntaxWarning
    # is suppressed here rather than firing when this module itself compiles.
    ns = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        exec(
            "def swallows():\n"
            "    try:\n"
            "        raise ValueError('this error should propagate')\n"
            "    finally:\n"
            "        return 'finally ate the exception'\n"
            "def overrides():\n"
            "    try:\n"
            "        return 'from try'\n"
            "    finally:\n"
            "        return 'from finally'\n",
            ns)

    print("--- the actual bug: a finally return SWALLOWS an exception ---")
    result = ns["swallows"]()
    print(f"  a function that raises but returns from finally : {result!r}")
    print("  the ValueError was RAISED, but the finally's return overrode the")
    print("  whole unwinding - so the caller sees a normal return and NEVER sees")
    print("  the exception. a genuine error vanished without a trace")

    print("--- and it overrides the try's return value ---")
    print(f"  try returns 'from try', finally returns 'from finally' : "
          f"{ns['overrides']()!r}")
    print("  the finally's return replaces the try's - another silent surprise.")
    print("  whatever the try was going to return is simply discarded")

    print("--- the fix: never transfer control out of a finally ---")
    print("  put cleanup in finally, but let control flow (return/break/continue/")
    print("  raise) happen in the try or after the block. finally is for cleanup,")
    print("  not for deciding what the function returns or where the loop goes")

    print("--- the constraint answered ---")
    print("  return/break/continue inside finally silently swallow exceptions and")
    print("  override returns - almost always a bug, and invisible before 3.14.")
    print("  PEP 765 makes the compiler warn on it, surfacing the trap while")
    print("  still compiling the code. the strongest guarantee's sharpest edge")
    print("  finally comes with a warning label")


if __name__ == "__main__":
    main()
