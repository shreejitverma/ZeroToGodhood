"""Listing 270.1 - Python 3.10 (2021): match/case, structural pattern matching (the basics).

Long if/elif chains that test the SHAPE of data - is it this literal? that kind
of object? a sequence of this length? - are verbose and error-prone. Many
languages answer with a `switch`, but a C-style switch only compares a value to
constants. Python 3.10's PEP 634 match statement is more: it matches the
STRUCTURE of a value and can BIND parts of it in the same step. This chapter
covers the fundamentals - literal patterns, the capture pattern that binds a
name, the wildcard _, and the crucial fact that match is structural, not a
fall-through switch. The PEG parser (Chapter 15) is what made this syntax
possible. Deep B owns evaluation; this is the release that added matching on
shape. Verified on current interpreters.
"""


def http_status(code):
    match code:
        case 200:                                # literal pattern
            return "OK"
        case 404:
            return "Not Found"
        case 500:
            return "Server Error"
        case _:                                  # wildcard: matches anything
            return "Unknown"


def describe(value):
    match value:
        case 0:
            return "zero"
        case int():                              # matches any int (a class pattern)
            return f"the integer {value}"
        case str() as s:                         # matches any str, binds it
            return f"the string {s!r}"
        case _:
            return f"something else: {value!r}"


def main() -> None:
    print("--- literal patterns: match a value against constants ---")
    for code in [200, 404, 500, 418]:
        print(f"  http_status({code}) : {http_status(code)}")
    print("  each `case 200:` compares code to a literal, like a switch. the")
    print("  final `case _:` is the wildcard - it matches anything, serving as")
    print("  the default branch")

    print("--- the capture pattern BINDS a name to the matched value ---")
    def unpack_point(p):
        match p:
            case (0, 0):
                return "origin"
            case (0, y):                         # y is CAPTURED from the value
                return f"on the y-axis at {y}"
            case (x, 0):
                return f"on the x-axis at {x}"
            case (x, y):
                return f"at ({x}, {y})"
    for p in [(0, 0), (0, 5), (3, 0), (2, 4)]:
        print(f"  unpack_point({p}) : {unpack_point(p)}")
    print("  `case (0, y)` matches any pair whose first element is 0 AND binds")
    print("  the second to y in one step. matching and destructuring together -")
    print("  the thing a switch cannot do")

    print("--- matching on TYPE, not just value ---")
    for v in [0, 42, "hi", [1, 2]]:
        print(f"  describe({v!r}) : {describe(v)}")
    print("  `case int():` matches any integer, `case str() as s:` any string")
    print("  (binding it to s). match tests the KIND of value, so one statement")
    print("  handles 'zero', 'any int', 'any str', and 'anything else' by shape")

    print("--- match does NOT fall through - exactly one case runs ---")
    hits = []
    def check(n):
        match n:
            case 1:
                hits.append("one")
            case _:
                hits.append("other")
    check(1)
    print(f"  after check(1), branches taken : {hits}")
    print("  unlike C's switch, there is no fall-through and no `break` needed:")
    print("  the FIRST matching case runs, then the whole statement is done.")
    print("  cases are tried top to bottom, so order more specific before general")

    print("--- a name alone is a CAPTURE, not a comparison (the classic gotcha) ---")
    RED = "red"
    def classify(color):
        match color:
            case "red":                          # a literal - compares
                return "matched the literal red"
            case other:                          # a bare NAME - captures, always matches
                return f"captured as {other!r}"
    print(f"  classify('red')  : {classify('red')}")
    print(f"  classify('blue') : {classify('blue')}")
    print("  a bare name like `other` is a CAPTURE pattern: it always matches and")
    print("  binds. it does NOT compare against a variable named other. to match")
    print("  against a constant you need a literal or a dotted name (Enum.RED)")

    print("--- the constraint answered ---")
    print("  testing the shape of data was long if/elif chains, and a C switch")
    print("  only compares to constants. match/case (3.10) matches STRUCTURE and")
    print("  BINDS parts in one step: literals, type patterns, captures, and _")
    print("  for default. it is structural dispatch, not a fall-through switch")


if __name__ == "__main__":
    main()
