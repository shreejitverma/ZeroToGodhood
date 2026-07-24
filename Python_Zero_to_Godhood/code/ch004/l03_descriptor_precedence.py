"""Listing 4.3 - data descriptors beat the instance dict; non-data descriptors
do not.

This single precedence rule is the whole reason attribute lookup behaves the way
it does. A data descriptor (defines __set__ or __delete__) is consulted before
the instance dict, so it cannot be shadowed by an instance attribute. A non-data
descriptor (only __get__) loses to the instance dict, so it can.
"""


class DataDesc:
    def __get__(self, obj, owner):
        return "data-descriptor"

    def __set__(self, obj, value):        # defining __set__ makes it a DATA descriptor
        pass


class NonDataDesc:
    def __get__(self, obj, owner):
        return "non-data-descriptor"


class C:
    d = DataDesc()
    n = NonDataDesc()


c = C()
c.__dict__["d"] = "instance-d"     # try to shadow the data descriptor
c.__dict__["n"] = "instance-n"     # try to shadow the non-data descriptor

print("--- both names have an instance-dict entry; only one wins ---")
print("  c.d ->", c.d, "  (data descriptor wins; instance dict ignored)")
print("  c.n ->", c.n, "  (instance dict wins over the non-data descriptor)")

print()
print("This is why you cannot clobber a property by assigning self.x in")
print("__init__: property is a data descriptor, its __set__ intercepts the")
print("write. And why a method (non-data descriptor) CAN be shadowed by an")
print("instance attribute of the same name, a real and occasional bug.")


class ValidatedPositive:
    """A minimal data descriptor: learns its name (PEP 487) and validates."""

    def __set_name__(self, owner, name):
        self.private = "_" + name

    def __get__(self, obj, owner=None):
        return self if obj is None else getattr(obj, self.private)

    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError("must be positive")
        setattr(obj, self.private, value)


class Account:
    balance = ValidatedPositive()

    def __init__(self, b):
        self.balance = b


print()
print("--- a data descriptor intercepting writes ---")
a = Account(100)
print("  a.balance:", a.balance)
try:
    a.balance = -5
except ValueError as exc:
    print("  a.balance = -5 ->", type(exc).__name__ + ":", exc)
