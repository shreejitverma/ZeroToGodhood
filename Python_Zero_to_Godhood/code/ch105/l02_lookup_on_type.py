"""Listing 105.2 - special methods are looked up on the TYPE, not the instance.

The single most consequential rule of the data model: when the interpreter needs
a special method (len(x) needs __len__, x + y needs __add__), it looks it up on
type(x), NOT on x itself. Putting __len__ in the instance's own __dict__ does
NOTHING; the value must live on the class. This is why you cannot make one
instance iterable by assigning it an __iter__ attribute, and why monkeypatching a
dunder means patching the class.
"""


def main() -> None:
    class C:
        pass

    c = C()

    print("--- put __len__ on the INSTANCE dict: ignored ---")
    c.__len__ = lambda: 42            # goes into c.__dict__, not the type
    print(f"  c.__len__ is in c.__dict__ : {'__len__' in c.__dict__}")
    try:
        len(c)
    except TypeError as e:
        print(f"  len(c) -> TypeError        : {e}")

    print("--- put __len__ on the TYPE: now len() finds it ---")
    C.__len__ = lambda self: 7        # goes on the class
    print(f"  after C.__len__ = ..., len(c) : {len(c)}")

    print("--- explicit attribute access DOES see the instance one ---")
    print(f"  c.__len__() (explicit, instance) : {c.__len__()}   (the lambda: 42)")
    print(f"  len(c)      (implicit, type)     : {len(c)}   (the class method: 7)")

    print("--- the rule ---")
    print(f"  implicit special-method dispatch reads type(x).__dunder__,")
    print(f"  never x.__dict__; to change a dunder, change the class")


if __name__ == "__main__":
    main()
