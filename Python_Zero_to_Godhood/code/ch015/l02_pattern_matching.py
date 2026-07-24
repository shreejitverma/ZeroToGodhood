"""Listing 15.2 - structural pattern matching is destructuring plus matching,
not a switch.

match/case is not a C/Java switch (which only compares a scalar against
constants). Each case is a PATTERN that simultaneously tests the shape of the
subject and binds names from its components, closer to Rust's match. It shines
when branching on the structure of data: ASTs, JSON-ish messages, command
tokens, geometric types.
"""

import dis


def classify(x):
    match x:
        case 0:                              # literal (value) pattern
            return "zero"
        case [a]:                            # sequence pattern, length 1
            return f"one-list:{a}"
        case [a, b, *rest]:                  # sequence with star-capture
            return f"seq:{a},{b},rest={rest}"
        case {"type": t, "value": v}:        # mapping pattern (subset of keys)
            return f"map:{t}={v}"
        case str() as s if len(s) > 3:       # class pattern + as-binding + guard
            return f"long-str:{s}"
        case int() | float():                # OR pattern of class patterns
            return f"number:{x}"
        case _:                              # wildcard
            return "unknown"


print("--- the pattern taxonomy over mixed subjects ---")
for v in [0, [7], [1, 2, 3, 4], {"type": "pt", "value": 9}, "hello", 3.5, (1, 2)]:
    print(f"  {v!r:>26} -> {classify(v)}")

print()
print("Note (1, 2) matched the SEQUENCE pattern: sequence patterns match any")
print("collections.abc.Sequence EXCEPT str/bytes/bytearray, deliberately")
print("excluded so a string is not destructured character by character. Mapping")
print("patterns match a SUBSET of keys.")

print()
print("--- class patterns destructure via __match_args__ ---")


class Point:
    __match_args__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y


def locate(p):
    match p:
        case Point(0, 0):
            return "origin"
        case Point(x, 0):
            return f"x-axis@{x}"
        case Point(0, y):
            return f"y-axis@{y}"
        case Point(x, y):
            return f"point@{x},{y}"


for p in (Point(0, 0), Point(5, 0), Point(2, 3)):
    print(f"  Point({p.x},{p.y}) -> {locate(p)}")

print()
print("--- the compiler builds a decision tree, not an if/elif chain ---")


def seqmatch(data):
    match data:
        case [1, y]:
            return y
        case _:
            return None


ops = [i.opname for i in dis.get_instructions(seqmatch)]
present = [o for o in ("MATCH_SEQUENCE", "GET_LEN", "UNPACK_SEQUENCE", "MATCH_MAPPING", "MATCH_CLASS")
           if o in ops]
print("  shape-testing opcodes in seqmatch:", present)
print("  these test shape once and fail fast BEFORE binding, so a half-matched")
print("  pattern never leaks a partial binding.")
