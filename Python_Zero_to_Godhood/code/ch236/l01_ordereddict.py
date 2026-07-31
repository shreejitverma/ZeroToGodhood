"""Listing 236.1 - Python 2.7 (2010): OrderedDict, and the idea that dict order matters.

For twenty years a dict was explicitly unordered: iterating it gave keys in an
arbitrary, implementation-defined sequence, and relying on the order was a bug.
When order mattered - config sections in file order, columns as declared,
undo history - you kept a separate list of keys alongside the dict. Python 2.7
added collections.OrderedDict: a dict that remembers insertion order. It made
'order matters here' expressible as a type. The idea won so thoroughly that in
3.7 the PLAIN dict became insertion-ordered by language guarantee, so today
OrderedDict earns its place by the EXTRA order operations a plain dict still
lacks. Deep Q owns the hash-table internals; this is the release that made
ordering a first-class dict property. Verified on current interpreters.
"""

from collections import OrderedDict


def main() -> None:
    print("--- OrderedDict remembers insertion order (its original purpose) ---")
    od = OrderedDict()
    for k in ["gamma", "alpha", "beta"]:
        od[k] = k.upper()
    print(f"  inserted gamma, alpha, beta -> keys: {list(od.keys())}")
    print("  the keys come back in INSERTION order, not sorted, not arbitrary.")
    print("  before 2.7 you kept a separate [gamma, alpha, beta] list beside")
    print("  the dict to remember this; OrderedDict folded that into the type")

    print("--- the modern consequence: plain dict is ALSO ordered since 3.7 ---")
    plain = {}
    for k in ["gamma", "alpha", "beta"]:
        plain[k] = k.upper()
    print(f"  plain dict keys : {list(plain.keys())}")
    print("  since Python 3.7 the ordinary dict preserves insertion order by")
    print("  LANGUAGE GUARANTEE - the idea OrderedDict introduced became the")
    print("  default. so for plain 'keep insertion order', a dict now suffices")

    print("--- what OrderedDict still gives that a plain dict does not ---")
    od2 = OrderedDict([("a", 1), ("b", 2), ("c", 3)])
    od2.move_to_end("a")                          # reorder: send 'a' to the end
    print(f"  move_to_end('a') -> {list(od2.keys())}")
    od2.move_to_end("c", last=False)             # send 'c' to the front
    print(f"  move_to_end('c', last=False) -> {list(od2.keys())}")
    first_key, first_val = od2.popitem(last=False)  # pop from the FRONT
    print(f"  popitem(last=False) popped the front : {(first_key, first_val)}")
    print("  move_to_end() and popitem(last=...) are order-EDITING operations a")
    print("  plain dict has no equivalent for. an LRU cache is exactly this:")
    print("  move touched keys to the end, evict from the front")

    print("--- order-sensitive equality: the other real difference ---")
    plain_ab = {"a": 1, "b": 2}
    plain_ba = {"b": 2, "a": 1}
    print(f"  plain {{a,b}} == plain {{b,a}} : {plain_ab == plain_ba}  (order ignored)")
    od_ab = OrderedDict([("a", 1), ("b", 2)])
    od_ba = OrderedDict([("b", 2), ("a", 1)])
    print(f"  Ordered {{a,b}} == Ordered {{b,a}} : {od_ab == od_ba}  (order matters)")
    print("  plain dicts compare equal regardless of order; two OrderedDicts")
    print("  compare equal only if their ORDER also matches. when order is part")
    print("  of the meaning (a sequence of steps), that stricter equality is")
    print("  the correct one - the remaining reason to choose OrderedDict")

    print("--- the constraint answered ---")
    print("  a dict was defined as unordered, so 'preserve order' meant a")
    print("  parallel list. 2.7's OrderedDict made order a property of the type;")
    print("  the idea proved so right that 3.7 made every dict ordered. today")
    print("  OrderedDict remains for order-editing (move_to_end) and")
    print("  order-sensitive equality - the parts ordering-as-default did not")
    print("  absorb")


if __name__ == "__main__":
    main()
