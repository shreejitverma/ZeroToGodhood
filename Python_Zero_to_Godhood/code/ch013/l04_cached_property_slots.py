"""Listing 13.4 - cached_property and __slots__ as applications of descriptor
precedence.

Both are direct consequences of Chapter 4's rule: a data descriptor outranks the
instance dict, a non-data descriptor does not.

cached_property (a NON-data descriptor, only __get__) computes once, writes the
result into instance.__dict__ under its own name, and is thereafter shadowed by
that instance-dict entry, so __get__ never runs again. This is exactly why a
plain @property (a DATA descriptor) cannot be cached this way: it would intercept
every access regardless of the instance dict.

__slots__ uses member descriptors (data descriptors with a fixed offset) and
removes the per-instance __dict__ entirely.
"""

import sys
from functools import cached_property

calls = []


class Data:
    @cached_property
    def heavy(self):
        calls.append(1)
        return sum(range(1000))


d = Data()
print("--- cached_property computes once, then is shadowed by its own cache ---")
print("  first :", d.heavy, "| second:", d.heavy, "| computed times:", len(calls))
print("  'heavy' now in d.__dict__:", "heavy" in d.__dict__)


class DictClass:
    def __init__(self):
        self.x = 1
        self.y = 2


class SlotsClass:
    __slots__ = ("x", "y")

    def __init__(self):
        self.x = 1
        self.y = 2


dd, ss = DictClass(), SlotsClass()
print()
print("--- __slots__ removes the per-instance __dict__ ---")
print("  dict-based total (obj + __dict__):", sys.getsizeof(dd) + sys.getsizeof(dd.__dict__))
print("  slots-based                      :", sys.getsizeof(ss))
try:
    ss.z = 3
except AttributeError as exc:
    print("  ss.z = 3 (not in __slots__)      ->", type(exc).__name__)
print()
print("The memory win compounds to gigabytes across millions of objects, and")
print("@dataclass(slots=True) (3.10) gives it for free. The trade: no dynamic")
print("attributes, and a subclass that omits __slots__ reintroduces __dict__.")
