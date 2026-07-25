"""Listing 113.1 - the descriptor protocol: __get__, __set__, __delete__, __set_name__.

A descriptor is an object that customizes attribute access for the class that holds
it, by defining any of:
  __get__(self, obj, objtype)  - called when the attribute is READ
  __set__(self, obj, value)    - called when it is ASSIGNED
  __delete__(self, obj)        - called when it is deleted
  __set_name__(self, owner, name) - called ONCE at class creation, told its name
This is the mechanism behind property, methods, classmethod, staticmethod, and
__slots__ (Chapter 22). When obj is None (access on the CLASS, not an instance),
__get__ conventionally returns the descriptor itself. This listing implements one.
"""


class Logged:
    """A descriptor that stores in the instance dict and logs access."""

    def __set_name__(self, owner, name):
        self.name = name                 # learn the attribute name at class creation
        print(f"  __set_name__: this descriptor is '{name}' on {owner.__name__}")

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self                  # accessed on the class -> the descriptor
        return obj.__dict__.get(self.name, "<unset>")

    def __set__(self, obj, value):
        print(f"  __set__: {self.name} = {value!r}")
        obj.__dict__[self.name] = value

    def __delete__(self, obj):
        print(f"  __delete__: {self.name}")
        del obj.__dict__[self.name]


class Account:
    balance = Logged()                   # __set_name__ fires HERE, at class creation


def main() -> None:
    print("--- (the __set_name__ line above ran during class creation) ---")
    a = Account()

    print("--- read: __get__ ---")
    print(f"  a.balance : {a.balance}")

    print("--- assign: __set__ ---")
    a.balance = 100
    print(f"  a.balance : {a.balance}")

    print("--- delete: __delete__ ---")
    del a.balance
    print(f"  a.balance after delete : {a.balance}")

    print("--- access on the CLASS (obj is None) returns the descriptor ---")
    print(f"  type(Account.balance) : {type(Account.balance).__name__}")

    print("--- the rule ---")
    print(f"  a descriptor on a class intercepts get/set/delete of that attribute;")
    print(f"  __set_name__ tells it its own name at class-creation time")


if __name__ == "__main__":
    main()
