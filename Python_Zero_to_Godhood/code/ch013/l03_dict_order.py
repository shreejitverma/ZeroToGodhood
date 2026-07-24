"""Listing 13.3 - dict insertion order is a language guarantee since 3.7.

The compact dict of Chapter 12 made insertion order an implementation detail in
3.6; Python 3.7 codified it as a language guarantee. The order is now part of the
spec for iteration, the keys/values/items views, **kwargs (call-site order), and
class-namespace ordering.
"""


def show(**kwargs):
    return list(kwargs)


print("--- **kwargs preserves call-site order (guaranteed since 3.7) ---")
print("  show(z=1, a=2, m=3):", show(z=1, a=2, m=3))

print()
print("--- iteration, views, and class __dict__ all follow insertion order ---")
d = {}
for k in ("gamma", "alpha", "beta"):
    d[k] = 1
print("  dict iteration :", list(d))
print("  .items() view  :", [k for k, _ in d.items()])


class Ordered:
    third = 3
    first = 1
    second = 2


print("  class __dict__ :", [k for k in vars(Ordered) if not k.startswith("__")])

print()
print("Ecosystem consequence: json.dumps is deterministic by default, ORMs and")
print("serializers can rely on field order, and OrderedDict is now reserved for")
print("its order-sensitive == and move_to_end, not for ordering itself.")
