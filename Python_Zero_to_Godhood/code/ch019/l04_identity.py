"""Listing 19.4 - identity, the small-integer cache, and why `is` lies to you.

`is` compares `ob_type`-bearing addresses, not values. Most of the time that is
exactly what you want. The exceptions are the objects CPython pre-allocates and
shares, and they produce the single most reliable source of confusion in the
language.
"""

import sys

print("--- CPython pre-allocates the small integers ---")
lo = hi = None
for i in range(-10, 300):
    immortal = sys.getrefcount(i) > 1000
    if immortal and lo is None:
        lo = i
    if immortal:
        hi = i
print(f"  ints with sentinel refcounts span {lo} .. {hi}")

print()
print("--- inside that range, equal values are the same object ---")
a = int("256")
b = int("256")
print(f"  int('256') is int('256')  ->  {a is b}")

print()
print("--- outside it, they are not ---")
c = int("257")
d = int("257")
print(f"  int('257') is int('257')  ->  {c is d}")
print(f"  int('257') == int('257')  ->  {c == d}")

print()
print("--- the same effect for strings, via interning ---")
s1 = "hello"
s2 = "hello"
s3 = "".join(["hel", "lo"])
print(f"  two literals:      s1 is s2  ->  {s1 is s2}")
print(f"  a computed string: s1 is s3  ->  {s1 is s3}")
print(f"  but equal:         s1 == s3  ->  {s1 == s3}")

print()
print("--- id() is the object's address, and is only unique while it lives ---")
first = id(object())
second = id(object())
print(f"  two short-lived objects reused the address: {first == second}")
print("  the first was freed before the second was allocated, so id() collided.")
print("  never cache an id() and expect it to still mean the same object.")
