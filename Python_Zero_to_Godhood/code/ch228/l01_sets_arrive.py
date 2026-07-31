"""Listing 228.1 - Python 2.3 (2003): the set type, membership and algebra as builtins.

Before 2.3, 'a collection of unique things' was faked with a dict mapping keys
to a dummy value (d[x] = 1), and 'is x in this collection' was dict membership.
Python 2.3 added `set` as a proper builtin type (2.4 gave it literal syntax):
O(1) membership, uniqueness by construction, and the algebra of sets - union,
intersection, difference - as operators. This is the container Chapter 88's
cost model points at for 'is this in there?', and using a list instead is the
most common real performance bug in Python. Deep Q owns the internals (hashing,
load factor); this is the release that made the right container a builtin.
Verified on current interpreters.
"""


def main() -> None:
    print("--- a set: unique elements, O(1) membership ---")
    s = {3, 1, 2, 2, 3, 1}                        # duplicates collapse
    print(f"  {{3,1,2,2,3,1}} -> {sorted(s)}  (duplicates gone)")
    print(f"  3 in s : {3 in s}  (O(1) - a hash lookup, not a scan)")
    print(f"  9 in s : {9 in s}")
    print("  uniqueness is by CONSTRUCTION (adding a duplicate is a no-op) and")
    print("  membership is O(1) (a hash probe) - the two properties a 'set of")
    print("  things you test membership on' needs (Chapter 88's cost model)")

    print("--- set algebra as operators ---")
    a = {1, 2, 3, 4}
    b = {3, 4, 5, 6}
    print(f"  a | b (union)        : {sorted(a | b)}")
    print(f"  a & b (intersection) : {sorted(a & b)}")
    print(f"  a - b (difference)   : {sorted(a - b)}")
    print(f"  a ^ b (symmetric diff): {sorted(a ^ b)}")
    is_subset = {1, 2} <= a
    print(f"  {{1,2}} <= a (subset)  : {is_subset}")
    print("  the algebra of sets - union, intersection, difference, subset -")
    print("  as operators. 'which symbols are in both portfolios' is a & b,")
    print("  not a nested loop (Chapter 88's 5000x membership win)")

    print("--- the pre-2.3 workaround, and why the type is better ---")
    fake_set = {}                                # a dict pretending to be a set
    for x in [1, 2, 2, 3]:
        fake_set[x] = 1                          # the old idiom
    print(f"  dict-as-set keys : {sorted(fake_set)}  (the pre-2.3 fake)")
    real_set = set([1, 2, 2, 3])
    print(f"  real set         : {sorted(real_set)}  (the 2.3 type)")
    print("  the dict-as-set worked but wasted a value per key, gave no set")
    print("  algebra, and read as a dict. a real type is smaller, has |&-^,")
    print("  and SAYS what it is - which is why the builtin mattered")

    print("--- the membership performance point (Chapter 88, in miniature) ---")
    big_list = list(range(10000))
    big_set = set(big_list)
    print(f"  9999 in list  : {9999 in big_list}  (scans up to 10000 items)")
    print(f"  9999 in set   : {9999 in big_set}  (one hash probe)")
    print("  SAME result, wildly different cost: 'x in list' inside a loop is")
    print("  the accidental quadratic (Chapter 87), and 'convert to a set")
    print("  first' is the single highest-leverage line-level fix in Python")

    print("--- frozenset: the immutable, hashable set ---")
    fs = frozenset({1, 2, 3})
    can_key = {fs: "usable as a dict key"}       # sets are unhashable; frozensets aren't
    print(f"  frozenset can be a dict key/set member : {fs in can_key}")
    print("  a set is mutable and thus unhashable; frozenset is the immutable")
    print("  version you can put IN a set or use as a key (Deep A's hashability")
    print("  rule: mutable means unhashable)")

    print("--- the constraint answered ---")
    print("  before 2.3, 'unique collection + fast membership' was a dict")
    print("  hack with no algebra. the set type made the right container a")
    print("  builtin, so Chapter 88's advice ('use a set for membership') is")
    print("  a one-liner, not a workaround. the container IS the cost model")


if __name__ == "__main__":
    main()
