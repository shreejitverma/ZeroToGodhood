"""Listing 18.6 - what the compiler forbids inside a PEP 695 scope.

A lazy scope may be evaluated at an arbitrary later moment, possibly more than
once by tooling, possibly never. Constructs whose whole purpose is a side
effect or a suspension point would have undefined timing, so the compiler
rejects them outright rather than leaving it to chance.
"""

CASES = [
    ("walrus in an alias",      "type A = [x := 1]"),
    ("yield in a TypeVar bound", "def f[T: (yield)](): ..."),
    ("await in an alias",        "async def g():\n    type A = await x\n"),
    ("yield in an alias",        "def h():\n    type A = (yield)\n"),
]

for label, source in CASES:
    try:
        compile(source, "<t>", "exec")
    except SyntaxError as exc:
        print(f"{label:24} -> SyntaxError: {exc.msg}")
    else:
        print(f"{label:24} -> accepted")

print()
print("--- but ordinary expressions are fine, including calls ---")
CALLS = 0


def side_effect():
    global CALLS
    CALLS += 1
    return int


type Counted = list[side_effect()]

print("calls after definition    =", CALLS)
print("value                     =", Counted.__value__)
print("calls after first access  =", CALLS)
print("value again               =", Counted.__value__)
print("calls after second access =", CALLS, "(cached: the scope ran once)")
