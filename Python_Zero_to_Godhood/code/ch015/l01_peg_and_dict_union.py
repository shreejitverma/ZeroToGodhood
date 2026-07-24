"""Listing 15.1 - the PEG parser's payoff, and the dict union operators.

PEP 617 (3.9) replaced the 30-year-old LL(1) parser with a PEG parser: ordered
choice (first match wins), unlimited lookahead, and packrat memoization (linear
time). Freed from one-token lookahead, the grammar could express constructs the
old parser could not, most visibly the parenthesized multi-line context managers
of 3.10, and it made the match grammar feasible. PEP 584 (3.9) added dict | and
|=.
"""

# The parenthesized context manager below only parses because of PEG lookahead;
# the old parser could not tell it from a parenthesized tuple. (Shown, not run,
# to avoid opening files.)
_ = """
with (
    open("a.txt") as a,
    open("b.txt") as b,
):
    ...
"""
print("--- parenthesized multi-line context managers: a PEG-only construct ---")
print("  (see the source; it parses only because of unlimited lookahead)")

print()
print("--- dict union: | merges into a new dict, |= updates in place ---")
d1, d2 = {"a": 1, "b": 2}, {"b": 99, "c": 3}
print("  d1 | d2 (right key wins):", d1 | d2)

merged = d1.copy()
merged |= d2
print("  merged |= d2            :", merged)

print()
print("--- | requires a mapping on the right; a non-mapping raises ---")
try:
    d1 | [1, 2]
except TypeError as exc:
    print("  d1 | [1, 2] ->", str(exc).split(":")[0])

print()
print("| always returns a plain dict even for dict subclasses; |= accepts any")
print("mapping (or an iterable of pairs, like update). Prefer |/|= for")
print("readability; {**a, **b} stays valid and is comparable in speed.")
