"""Listing 231.1 - Python 2.5 (2006): conditional expressions, x if cond else y.

For its first fifteen years Python had no ternary operator, and the community
kept inventing unsafe fakes for it. The most common, `cond and a or b`, has a
silent bug: it returns b whenever a is falsy, even when cond is true. Python
resisted adding a ternary for years (there was no obvious good syntax), then
PEP 308 chose a deliberately un-C-like order that reads like English:
`a if cond else b` - value first, condition second. The order is the point: it
puts the usual result up front. Deep B owns expression evaluation; this is the
release that gave Python a correct one-expression conditional and retired the
`and/or` trap. Verified on current interpreters.
"""


def main() -> None:
    print("--- the conditional expression: value first, condition second ---")
    n = 7
    parity = "odd" if n % 2 else "even"
    print(f"  'odd' if n % 2 else 'even'  (n=7) : {parity}")
    print(f"  abs via expression : {n if n >= 0 else -n}")
    print("  reads left to right as English: the USUAL value, the condition")
    print("  that qualifies it, then the fallback. one expression, so it works")
    print("  where a statement can't - in a return, an arg, a comprehension")

    print("--- why it was needed: the `and/or` fake has a silent bug ---")
    cond = True
    a, b = 0, 99                                 # a is falsy (0)
    fake = cond and a or b                        # the pre-2.5 idiom
    correct = a if cond else b                    # the 2.5 expression
    print(f"  cond=True, a=0, b=99")
    print(f"  cond and a or b : {fake}   <- WRONG (wanted a=0, got b=99)")
    print(f"  a if cond else b: {correct}   <- correct")
    print("  `cond and a or b` collapses to `b` whenever a is FALSY, even with")
    print("  cond true - because `True and 0` is 0, then `0 or 99` is 99. the")
    print("  ternary has no such hole: it selects on the CONDITION, not on")
    print("  whether the chosen value happens to be truthy")

    print("--- it is an expression, so it nests where statements cannot ---")
    def classify(x):
        return "neg" if x < 0 else "zero" if x == 0 else "pos"
    print(f"  classify(-3), classify(0), classify(5) : "
          f"{classify(-3)}, {classify(0)}, {classify(5)}")
    labels = ["even" if k % 2 == 0 else "odd" for k in range(5)]
    print(f"  inside a comprehension : {labels}")
    print("  because it is an expression it goes inside return, inside a")
    print("  comprehension, inside a function argument - places an if-STATEMENT")
    print("  cannot reach. that is the whole reason a ternary earns its keep")

    print("--- only the chosen branch is evaluated (short-circuit) ---")
    log = []
    def side(tag, value):
        log.append(tag)
        return value
    result = side("A", 1) if True else side("B", 2)
    print(f"  result : {result}, evaluated branches : {log}")
    print("  the else branch never ran - the expression evaluates ONLY the")
    print("  selected side, like if/else, so putting an expensive or unsafe")
    print("  call in the untaken branch is fine (Deep B's evaluation rules)")

    print("--- the constraint answered ---")
    print("  Python lacked a ternary and the `and/or` workaround was quietly")
    print("  wrong for falsy values. PEP 308 added `a if cond else b` - value")
    print("  first so the common case reads first - giving a correct, nestable,")
    print("  short-circuiting one-expression conditional and ending the trap")


if __name__ == "__main__":
    main()
