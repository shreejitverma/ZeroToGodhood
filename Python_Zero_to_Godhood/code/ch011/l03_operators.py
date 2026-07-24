"""Listing 11.3 - the @ matrix operator and PEP 448 unpacking, both meaning-free
dispatch.

PEP 465 added @ (and @=) for matrix multiplication, mapping to __matmul__ and
the C slot nb_matrix_multiply. Like every operator it carries no built-in
meaning; it dispatches to the operands' type. PEP 448 generalized * and **
unpacking to multiple uses in literals and calls.
"""

import operator


class Vec:
    def __init__(self, data):
        self.data = data

    def __matmul__(self, other):
        return sum(a * b for a, b in zip(self.data, other.data))


print("--- @ dispatches to __matmul__; here, a dot product ---")
print("  Vec([1,2,3]) @ Vec([4,5,6]):", Vec([1, 2, 3]) @ Vec([4, 5, 6]))
print("  operator.matmul exists:", hasattr(operator, "matmul"))
print("  (NumPy implements nb_matrix_multiply to call BLAS, which releases the")
print("   GIL during the heavy C computation; @ on large arrays is readable AND")
print("   parallelizable. See Deep T.)")

print()
print("--- PEP 448: multiple * and ** unpackings in literals and calls ---")
a, b = [1, 2], [3, 4]
print("  [*a, *b, 5]        :", [*a, *b, 5])
d1, d2 = {"x": 1}, {"y": 2}
print("  {**d1, **d2, 'z':3}:", {**d1, **d2, "z": 3})


def f(*args):
    return args


print("  f(*a, *b)          :", f(*a, *b))

print()
print("--- collision rules differ by context ---")
overlap1, overlap2 = {"k": 1}, {"k": 2}
print("  dict literal, rightmost wins: {**o1, **o2}['k'] =", {**overlap1, **overlap2}["k"])
try:
    f2 = lambda **kw: kw  # noqa: E731
    f2(**overlap1, **overlap2)
except TypeError as exc:
    print("  call kwargs collision raises ->", type(exc).__name__ + ":", str(exc)[:52])
