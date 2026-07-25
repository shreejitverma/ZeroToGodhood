"""Listing 106.2 - the instance __dict__, shadowing, and the write hooks.

By default an instance stores its attributes in a per-instance dict, obj.__dict__.
Reading obj.name consults that dict (among other places, Listing 106.3); writing
obj.name = v stores into it via __setattr__, and del obj.name removes it via
__delattr__. An instance attribute SHADOWS a class attribute of the same name,
because the instance dict is consulted before the class for ordinary names. This
listing shows the dict, shadowing, and the __setattr__/__delattr__ hooks.
"""


class Box:
    label = "class-default"            # class attribute, shared by all instances

    def __init__(self):
        self.value = 10                # instance attribute, per object


def main() -> None:
    b = Box()

    print("--- instance attributes live in obj.__dict__ ---")
    print(f"  b.__dict__            : {b.__dict__}")
    print(f"  b.label (from class)  : {b.label}")

    print("--- assigning an instance attribute SHADOWS the class attribute ---")
    b.label = "instance-override"      # writes into b.__dict__ via __setattr__
    print(f"  after b.label = ...   : {b.label}   (instance dict wins)")
    print(f"  Box.label (unchanged) : {Box.label}   (the class attr is untouched)")
    print(f"  b.__dict__            : {b.__dict__}")

    print("--- del removes the instance attribute; the class attr re-emerges ---")
    del b.label                        # __delattr__ removes it from b.__dict__
    print(f"  after del b.label     : {b.label}   (class attr visible again)")

    print("--- __setattr__ intercepts EVERY assignment ---")
    class Audited:
        def __setattr__(self, name, value):
            print(f"    __setattr__ {name!r} = {value!r}")
            object.__setattr__(self, name, value)   # do the real store

    a = Audited()
    a.count = 1
    print(f"  a.count : {a.count}")

    print("--- the rule ---")
    print(f"  instance attrs live in __dict__ and shadow class attrs; writes go")
    print(f"  through __setattr__, deletes through __delattr__")


if __name__ == "__main__":
    main()
