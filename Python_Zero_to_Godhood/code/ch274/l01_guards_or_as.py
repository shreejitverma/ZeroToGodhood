"""Listing 274.1 - Python 3.10 (2021): guards, OR-patterns, and as-patterns.

The final pieces that make match expressive. A GUARD (`case p if cond:`) adds a
boolean condition a pattern alone cannot express - relationships between bound
values, range checks, arbitrary predicates. An OR-pattern (`case a | b:`) matches
any of several alternatives in one case. An AS-pattern (`case p as name:`) binds
the whole thing a sub-pattern matched, so you keep both the parts AND the intact
value. Together with the structural patterns of the earlier chapters, these make
match a complete dispatch tool, not just a fancy switch. Deep B owns evaluation;
this chapter closes the pattern-matching facets of the 3.10 release. Verified on
current interpreters.
"""

from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int


def main() -> None:
    print("--- a GUARD adds a condition the pattern alone cannot check ---")
    def quadrant(p):
        match p:
            case Point(x, y) if x == y:          # relationship between bound names, checked first
                return "on the line y = x"
            case Point(x, y) if x > 0 and y > 0:
                return "quadrant I"
            case Point(x, y) if x < 0 and y > 0:
                return "quadrant II"
            case Point():
                return "somewhere else"
    for p in [Point(1, 2), Point(-1, 3), Point(5, 5), Point(2, -1)]:
        print(f"  quadrant({p}) : {quadrant(p)}")
    print("  `case Point(x, y) if x == y:` matches the shape AND tests a")
    print("  condition on the bound values. the guard runs only if the pattern")
    print("  matched; if the guard is false, matching CONTINUES to the next case")

    print("--- the guard sees the BOUND names - relationships, ranges, predicates ---")
    def classify(n):
        match n:
            case int() as v if v < 0:
                return "negative"
            case int() as v if v % 2 == 0:
                return "even"
            case int():
                return "odd"
    for n in [-4, 10, 7]:
        print(f"  classify({n}) : {classify(n)}")
    print("  a guard is arbitrary Python, evaluated with the captured names in")
    print("  scope. it expresses what patterns cannot: <, %, membership, any")
    print("  predicate over the values the pattern pulled out")

    print("--- OR-patterns: one case, several alternatives with | ---")
    def day_type(day):
        match day:
            case "sat" | "sun":                  # matches either
                return "weekend"
            case "mon" | "tue" | "wed" | "thu" | "fri":
                return "weekday"
            case _:
                return "unknown"
    for d in ["sat", "wed", "xyz"]:
        print(f"  day_type({d!r}) : {day_type(d)}")
    print("  `case 'sat' | 'sun':` matches if the value matches ANY alternative,")
    print("  collapsing what would be several near-identical cases into one.")
    print("  each alternative is a full pattern, not just a literal")

    print("--- OR-patterns can bind, if every alternative binds the same name ---")
    def unwrap(value):
        match value:
            case [x] | (x,):                     # a 1-list OR a 1-tuple, bind x
                return f"single value {x}"
            case _:
                return "not a singleton"
    print(f"  unwrap([9])  : {unwrap([9])}")
    print(f"  unwrap((7,)) : {unwrap((7,))}")
    print("  every branch of an OR-pattern must bind the SAME names, so whichever")
    print("  alternative matched, x is defined afterwards. here 'a one-element")
    print("  list or tuple' is one case that works for both")

    print("--- AS-patterns: keep the whole matched value AND its parts ---")
    def normalize(shape):
        match shape:
            case Point(0, 0) as origin:          # match the shape, keep the object
                return f"origin object: {origin}"
            case Point(x, y) as p:
                return f"point {p} with x={x}, y={y}"
    print(f"  {normalize(Point(0, 0))}")
    print(f"  {normalize(Point(3, 4))}")
    print("  `case Point(x, y) as p` binds x and y from inside AND binds the")
    print("  whole Point to p. you get the destructured parts and the intact")
    print("  value together - useful when you need to pass the original along")

    print("--- the constraint answered ---")
    print("  patterns match shape; guards add conditions on the bound values;")
    print("  OR-patterns fold alternatives into one case; as-patterns keep the")
    print("  whole value alongside its parts. with the structural patterns of")
    print("  Chapters 270-273, these complete match/case as a full structural")
    print("  dispatch tool - shape, condition, alternation, and capture together")


if __name__ == "__main__":
    main()
