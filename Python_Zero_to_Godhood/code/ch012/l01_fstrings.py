"""Listing 12.1 - f-strings interpolate at compile time, with a rich feature
surface.

The pre-3.6 options both pay runtime cost: %-formatting builds a temporary tuple
and runs C printf routines; "".format() does an attribute lookup, a call, and
re-parses the format string every call. An f-string moves interpolation to
compile time: the parser splits the literal into constant chunks and expression
sub-trees, and the compiler emits inline formatting opcodes, no method lookup, no
call frame, no runtime format parsing.
"""

x = 3.14159

print("--- format specs, conversions, and the = debug form (3.8) ---")
print("  f'{x:.2f}'  :", f"{x:.2f}")
print("  f'{chr(65)!r}' :", f"{chr(65)!r}")
print("  f'{x=}'     :", f"{x=}")

print()
print("--- PEP 701 (3.12) relaxations: reuse quotes, multiline, nesting ---")
val = {"k": "v"}
print("  same-quote nesting f'{val[\"k\"]}':", f"{val["k"]}")
print("  multiline expression            :", f"{
    1 + 2
}")
print()
print("Before 3.12 you could not reuse the f-string's own quote inside the")
print("expression, embed backslashes, write multiline expressions, or put")
print("comments in the braces. PEP 701 reimplemented f-strings in the PEG")
print("grammar and lifted all of it. f-strings format EAGERLY, so do not use")
print("them where formatting should be deferred (logging; see the benchmark).")
