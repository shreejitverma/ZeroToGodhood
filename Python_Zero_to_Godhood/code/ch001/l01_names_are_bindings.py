"""Listing 2.1 - assignment binds a name; it never copies an object.

The single most consequential fact in the language, and the one that most
reliably surprises an engineer arriving from C++ or Java: `b = a` does not copy
`a`. It binds a second name to the same object.
"""

a = [1, 2, 3]
b = a               # b is NOT a copy; a and b name the same list
b.append(4)

print("after b.append(4):")
print("  a       =", a)          # the mutation is visible through a
print("  b       =", b)
print("  a is b  =", a is b)     # identity: the same object
print("  a == b  =", a == b)     # value: also equal, but that is a weaker claim

print()
print("contrast: rebinding a name does not touch the object or the other name")
c = a
c = c + [5]         # builds a NEW list, rebinds c to it; a is untouched
print("  a       =", a)
print("  c       =", c)
print("  a is c  =", a is c)
