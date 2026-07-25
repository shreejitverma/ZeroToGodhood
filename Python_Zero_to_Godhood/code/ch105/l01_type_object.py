"""Listing 105.1 - the type object: what ob_type points at.

Chapter 19 established that every object begins with ob_refcnt and ob_type.
This listing looks at what ob_type POINTS AT: the type object. The type is
itself a full object (it has the header), its own type is 'type', and it carries
the SLOT TABLE, the C-level function pointers (tp_as_number->nb_add and friends)
that implement the object's behaviour. A special method like __add__ is an entry
in that table, exposed to Python as an attribute OF THE TYPE.
"""


def main() -> None:
    x = 5

    print("--- ob_type is the object's type ---")
    print(f"  type(5)            : {type(x).__name__}")

    print("--- the type carries the slot: __add__ lives on the TYPE ---")
    print(f"  type(5).__add__    : {type(x).__add__!r}")
    print(f"  it is a slot wrapper (a C slot), kind : {type(type(x).__add__).__name__}")

    print("--- a Python-defined method is a plain function on the type ---")
    class P:
        def __add__(self, o):
            return 1
    print(f"  P.__add__ kind     : {type(P.__add__).__name__}")

    print("--- a type is itself an object; its type is 'type' ---")
    print(f"  isinstance(int, object) : {isinstance(int, object)}")
    print(f"  type(int)               : {type(int).__name__}")
    print(f"  type(type)              : {type(type).__name__}   (type is its own type)")

    print("--- the rule ---")
    print(f"  ob_type points at the type object, which holds the slot table;")
    print(f"  a special method is an entry in that table, an attribute of the type")


if __name__ == "__main__":
    main()
