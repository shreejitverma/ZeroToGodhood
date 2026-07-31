"""Listing 216.1 - December 1989: the founding commitment, everything is an object.

The prototype Guido began over the Christmas break of 1989 (first released as
0.9.0 in February 1991, Chapter 1) already carried the architectural decision
that everything else in Python rests on: EVERYTHING IS AN OBJECT. Not just the
data - the functions, the types, the modules, the code itself. There is no
privileged category of 'primitives' outside the object system (contrast Java's
int-vs-Integer). This listing demonstrates the commitment as it survives in
today's interpreter, the direct descendant of the 1991 design: functions are
objects, types are objects, and even a class is an instance of a type.
Verified on current interpreters - the founding decision, still observable.
"""


def a_function(x):
    return x + 1


class AClass:
    pass


def main() -> None:
    print("--- data is objects (obviously) - but so is everything else ---")
    print(f"  42 is an object      : {isinstance(42, object)}")
    print(f"  'hi' is an object    : {isinstance('hi', object)}")
    print(f"  [1,2] is an object   : {isinstance([1, 2], object)}")

    print("--- functions are objects: they have attributes and identity ---")
    a_function.tag = "annotated at runtime"
    print(f"  a function has a type   : {type(a_function).__name__}")
    print(f"  and attributes you set  : {a_function.tag!r}")
    print(f"  and can be passed around: {list(map(a_function, [1, 2, 3]))}")
    print("  a function is a first-class object - assignable, passable,")
    print("  attribute-bearing - which is why decorators, closures, and")
    print("  higher-order functions all just WORK (no special mechanism)")

    print("--- types are objects, and a class is an instance of a type ---")
    print(f"  type of AClass          : {type(AClass).__name__}")
    print(f"  type of int             : {type(int).__name__}")
    print(f"  type of type            : {type(type).__name__}")
    print("  a class is an instance of 'type'; 'type' is an instance of")
    print("  itself. the object system has no floor and no ceiling - it is")
    print("  turtles all the way down, by design (Deep A, Deep C own this)")

    print("--- there is no privileged 'primitive' category ---")
    print(f"  int has methods          : {(42).bit_length()} = (42).bit_length()")
    print(f"  int is subclassable      :", end=" ")

    class Ticks(int):
        pass
    print(f"{Ticks(5) + 1} (a Ticks, still an int)")
    print("  contrast Java's int (a primitive, not an object, needs Integer")
    print("  to box it): in Python there is ONE category, objects, and the")
    print("  smallest int and the largest class are the same kind of thing")

    print("--- the founding commitment, and the whole book ---")
    print("  'everything is an object' is the 1989 decision that makes Python")
    print("  uniform (one model for all values), extensible (Chapter 1: a C")
    print("  type IS an object), and introspectable (Deep S). its cost - a")
    print("  header on every value (Deep A, Chapter 89) - is the price of the")
    print("  uniformity, paid on every object, forever. that trade, chosen at")
    print("  the start, is what the timeline spends thirty-five years refining")


if __name__ == "__main__":
    main()
