"""Listing 266.1 - Python 3.8 (2019): the f-string = specifier, self-documenting debug output.

The most common debugging line in any language is 'print this variable with its
name': print("count =", count). You type the name twice - once as text, once as
the value - and they drift apart when you rename or copy-paste, producing labels
that lie ('count =', but it prints total). Python 3.8 added the = specifier to
f-strings: f"{count=}" expands to the text 'count=' followed by the value's repr,
from the SINGLE expression you wrote. The label is generated from the expression,
so it can never disagree with the value. It even works on whole expressions, not
just names. Deep D owns string formatting; this is the small release that made
the ubiquitous debug print correct by construction. Verified on current
interpreters.
"""


def main() -> None:
    print("--- f\"{expr=}\" prints the expression text AND its value ---")
    count = 42
    name = "Ada"
    print(f"  f'{{count=}}' -> {count=}")
    print(f"  f'{{name=}}'  -> {name=}")
    print("  one expression produced both the label 'count=' and the value 42.")
    print("  you wrote `count` once; the = specifier echoed the source text and")
    print("  appended its repr. no more typing the name twice")

    print("--- the bug it prevents: a label that lies ---")
    total = 100
    subtotal = 30
    # The classic copy-paste error: label says one thing, value is another.
    print(f"  hand-written, miscopied : {'total ='} {subtotal}   <- label LIES")
    print(f"  with = specifier        : {subtotal=}   <- label cannot lie")
    print("  the manual 'total =', subtotal prints the WRONG name (a real bug")
    print("  from renaming or pasting). the = form derives the label from the")
    print("  expression, so it always matches the value shown")

    print("--- it works on whole EXPRESSIONS, not just variable names ---")
    xs = [3, 1, 2]
    print(f"  {sorted(xs)=}")
    print(f"  {len(xs) * 2=}")
    print(f"  {xs[0] + xs[1]=}")
    print("  the text captured is the whole expression source, and the value is")
    print("  its result. great for 'what does this actually evaluate to?' checks")
    print("  without inventing a label")

    print("--- format specs still apply after the = ---")
    import math
    pi = math.pi
    print(f"  {pi=:.3f}   (round to 3 places, still labelled)")
    ratio = 0.25
    print(f"  {ratio=:.0%}   (as a percent)")
    print("  put a normal format spec after the =, and it formats the VALUE while")
    print("  keeping the generated label. the debug helper composes with the")
    print("  whole format mini-language (Chapter 246)")

    print("--- whitespace around = is preserved in the label ---")
    x = 5
    print(f"  f'{{x = }}' -> {x = }")
    print("  spaces you put around the = are echoed, so you control the look")
    print("  ('x=5' vs 'x = 5'). a tiny touch, but it means the output reads")
    print("  exactly how you wrote the expression")

    print("--- the constraint answered ---")
    print("  the everyday debug print made you type a variable's name twice -")
    print("  once as a label, once as the value - and the two drifted apart into")
    print("  lying labels. the f-string = specifier (3.8) generates the label")
    print("  from the expression itself, so name and value can never disagree.")
    print("  the most common debug line became correct by construction")


if __name__ == "__main__":
    main()
