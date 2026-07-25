"""Listing 106.3 - the full lookup order that object.__getattribute__ implements.

Reading obj.name is not "check the instance, then the class". object.__getattribute__
follows a precise precedence:
  1. a DATA descriptor on the type (one with __set__/__delete__) wins over everything
  2. else the instance __dict__
  3. else a NON-DATA descriptor or plain class attribute (searched along the MRO)
  4. else __getattr__ (the Listing 106.1 fallback), or AttributeError
This listing demonstrates the two surprising precedence rules: a data descriptor
beats the instance dict, and a plain class attribute does NOT. (Descriptors
themselves, __get__/__set__ and data vs non-data, are Deep C; here we only observe
where they sit in the order.)
"""


class DataDescriptor:
    """Has __set__, so it is a DATA descriptor: precedence rank 1."""

    def __get__(self, obj, objtype=None):
        return "from-data-descriptor"

    def __set__(self, obj, value):
        pass                            # swallow writes; presence of __set__ is the point


def main() -> None:
    print("--- a DATA descriptor on the type beats the instance dict ---")
    class D:
        attr = DataDescriptor()
    d = D()
    d.__dict__["attr"] = "from-instance-dict"   # force a same-named instance entry
    print(f"  d.__dict__['attr']    : {d.__dict__['attr']}")
    print(f"  d.attr                : {d.attr}   (data descriptor wins, rank 1 > 2)")

    print("--- a plain CLASS attribute does NOT beat the instance dict ---")
    class P:
        attr = "from-class"
    p = P()
    p.__dict__["attr"] = "from-instance-dict"
    print(f"  p.attr                : {p.attr}   (instance dict wins, rank 2 > 3)")

    print("--- so the same 'shadowing' question has OPPOSITE answers ---")
    print(f"  data descriptor vs instance dict : descriptor wins")
    print(f"  plain class attr vs instance dict: instance wins")

    print("--- the rule ---")
    print(f"  order: data descriptor > instance __dict__ > class attr/non-data")
    print(f"  > __getattr__; this is what object.__getattribute__ does")


if __name__ == "__main__":
    main()
