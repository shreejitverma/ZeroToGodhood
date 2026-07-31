"""Listing 275.1 - Python 3.11 (2022): PEP 657, fine-grained error locations in tracebacks.

Before 3.11 a traceback pointed at a LINE. When that line had several places the
same error could come from - a[i][j][k], or x + y + z where one term is None -
the line number alone left you guessing WHICH sub-expression failed. Python 3.11
records, per bytecode instruction, the exact COLUMN span of the source that
produced it (via code.co_positions()), and the traceback underlines the precise
sub-expression with ^ carets. 'None is not subscriptable' now shows you which
subscript. Deep J owns the interpreter and bytecode this rests on; this is the
release that made tracebacks point at the exact expression, not just the line.
This listing extracts only the caret lines (not the file-path frames), so its
output is machine-independent. Verified on current interpreters.
"""

import traceback


def show_error_location(fn):
    """Run fn, capture the traceback, and print ONLY the caret lines + message."""
    try:
        fn()
    except Exception:
        tb = traceback.format_exc()
    lines = tb.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        # A caret line is made only of the underline characters ~ and ^.
        if stripped and set(stripped) <= set("~^"):
            # print the source line above it and the caret line, de-pathed
            print(f"    {lines[i - 1].strip()}")
            print(f"    {line.strip()}")
    print(f"    -> {lines[-1]}")


def main() -> None:
    print("--- carets point at the EXACT failing subscript, not just the line ---")
    def subscript_fail():
        data = {"a": {"b": None}}
        return data["a"]["b"]["c"]               # None["c"] fails; which subscript?
    show_error_location(subscript_fail)
    print("  the ^ carets underline `[\"c\"]` specifically - the subscript that")
    print("  was applied to None. before 3.11 you only got the line and had to")
    print("  reason out which of the three subscripts blew up")

    print("--- which term of an arithmetic expression was the problem ---")
    def arithmetic_fail():
        a, b, c = 1, None, 3
        return a + b + c                         # a + b fails: b is None
    show_error_location(arithmetic_fail)
    print("  in `a + b + c` the carets mark `a + b`, the failing operation. the")
    print("  line has three operands; the location tells you it was b, not c")

    print("--- attribute access in a chain: which attribute is missing ---")
    def attribute_fail():
        class Box: pass
        obj = Box()
        return obj.contents.name                 # obj.contents is fine? no - missing
    show_error_location(attribute_fail)
    print("  `obj.contents` does not exist, and the carets sit under `.contents`")
    print("  - not the whole chain. in a long a.b.c.d access, you see exactly")
    print("  which hop failed")

    print("--- the mechanism: code.co_positions() carries column spans ---")
    def sample(x):
        return x + 1
    positions = list(sample.__code__.co_positions())
    has_columns = any(
        start_col is not None and end_col is not None
        for (_, _, start_col, end_col) in positions
    )
    print(f"  sample.__code__.co_positions() yields column spans : {has_columns}")
    print("  each bytecode instruction now records (start_line, end_line,")
    print("  start_col, end_col). the traceback machinery reads those to draw the")
    print("  carets. it is exact source-position tracking in the code object (Deep J)")

    print("--- the constraint answered ---")
    print("  a traceback pointed only at a LINE, so when a line had several")
    print("  places the error could originate you had to guess. PEP 657 (3.11)")
    print("  records per-instruction column spans and underlines the exact")
    print("  sub-expression with ^ carets. the traceback now points at the")
    print("  precise operation that failed, not just the line it was on")


if __name__ == "__main__":
    main()
