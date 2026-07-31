"""Listing 246.1 - Python 3.1 (2009): str.format auto-numbering and the format mini-language.

Old string formatting was the % operator: "%s is %d" % (name, age) - positional,
C-derived, and error-prone (wrong type, wrong count, tuple-vs-single gotchas).
Python 2.6/3.0 introduced str.format() with numbered fields "{0} is {1}", and
3.1 added AUTO-numbering: "{} is {}" - the fields number themselves. More
importantly, format() carries a rich FORMAT MINI-LANGUAGE after a colon:
alignment, width, thousands separators, precision, number bases. That mini-
language is the durable part: f-strings (3.6) are new SYNTAX over the SAME
spec. Learn "{:,.2f}" once and it works in format(), str.format(), and
f-strings alike. Deep D owns text and encoding; this is the release that
settled how values become formatted text. Verified on current interpreters.
"""


def main() -> None:
    print("--- auto-numbering: {} fills fields left to right (3.1) ---")
    name, age = "Ada", 36
    print(f"  '{{}} is {{}}'.format(name, age) : {'{} is {}'.format(name, age)}")
    print(f"  numbered '{{0}} {{1}} {{0}}' reuses : {'{0} {1} {0}'.format('a', 'b')}")
    print("  3.1 let fields number themselves ({}), so you no longer count")
    print("  indices for the common case. numbered fields {0} remain for reuse")
    print("  or reordering; named fields {who} for clarity")

    print("--- named fields read like a template ---")
    line = "{user} spent {amount} on {item}".format(
        user="Ada", amount=42, item="books")
    print(f"  {line}")
    print("  named placeholders make the call self-documenting and order-")
    print("  independent - the arguments say which field they fill")

    print("--- the format mini-language: everything after the colon ---")
    print(f"  thousands separator  '{{:,}}'   : {'{:,}'.format(1234567)}")
    print(f"  fixed precision      '{{:.2f}}' : {'{:.2f}'.format(3.14159)}")
    print(f"  both                 '{{:,.2f}}': {'{:,.2f}'.format(1234567.891)}")
    print(f"  percentage           '{{:.1%}}' : {'{:.1%}'.format(0.0734)}")
    print("  after the colon comes a SPEC: ,=group thousands, .2f=two decimals,")
    print("  .1%=percent. these describe how the value becomes text, and they")
    print("  are the reason format() replaced ad-hoc rounding and string math")

    print("--- alignment and width: building aligned columns ---")
    rows = [("apple", 3), ("fig", 12), ("cherry", 155)]
    for item, qty in rows:
        print(f"  |{'{:<8}'.format(item)}|{'{:>5}'.format(qty)}|")
    print("  '{:<8}' left-aligns in width 8; '{:>5}' right-aligns in width 5.")
    print("  columns line up without manual padding - the mini-language does")
    print("  the spacing, which is why tabular text stopped needing ljust/rjust")

    print("--- number bases and sign, in the same spec grammar ---")
    print(f"  binary  '{{:b}}'  of 42 : {'{:b}'.format(42)}")
    print(f"  hex     '{{:#x}}' of 255: {'{:#x}'.format(255)}")
    print(f"  signed  '{{:+d}}' of 7  : {'{:+d}'.format(7)}")
    print("  base conversion and explicit sign are part of one consistent")
    print("  grammar, not separate functions (bin(), hex()) plus prefix hacks")

    print("--- the payoff: f-strings (3.6) reuse this exact mini-language ---")
    value = 1234567.891
    via_format = "{:,.2f}".format(value)
    via_fstring = f"{value:,.2f}"
    print(f"  '{{:,.2f}}'.format(value) : {via_format}")
    print(f"  f'{{value:,.2f}}'          : {via_fstring}")
    print(f"  identical output : {via_format == via_fstring}")
    print("  the f-string is newer SYNTAX over the SAME spec after the colon.")
    print("  learn the mini-language once and it serves format(), str.format,")
    print("  and f-strings - which is why 3.1 settled the durable part")

    print("--- the constraint answered ---")
    print("  %-formatting was positional and fragile. str.format with auto-")
    print("  numbering (3.1) removed index-counting for the common case, and")
    print("  its format mini-language gave one consistent grammar for width,")
    print("  alignment, grouping, precision, and bases. f-strings later reused")
    print("  that grammar verbatim - the release settled how values become text")


if __name__ == "__main__":
    main()
