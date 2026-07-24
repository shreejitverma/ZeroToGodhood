"""Listing 18.1 - the three PEP 695 forms and the objects they actually create.

PEP 695 adds one piece of syntax in three positions: a type-parameter list on
a function, on a class, and the `type` statement. This listing shows what each
leaves behind at runtime.
"""

type Alias = list[int]


def fn[T](x: T) -> T:
    return x


class Box[T]:
    def __init__(self, v: T) -> None:
        self.v = v


print("--- the type alias is an object, not a name for another object ---")
print("type(Alias)           =", type(Alias))
print("Alias.__name__        =", Alias.__name__)
print("Alias.__value__       =", Alias.__value__)
print("Alias.__type_params__ =", Alias.__type_params__)

print()
print("--- functions and classes grow a __type_params__ slot ---")
print("fn.__type_params__    =", fn.__type_params__)
print("Box.__type_params__   =", Box.__type_params__)

print()
print("--- Generic is added to the bases for you ---")
print("Box.__bases__         =", Box.__bases__)
print("Box.__mro__           =", Box.__mro__)

print()
print("--- the implicitly created TypeVar ---")
(T,) = fn.__type_params__
print("type(T)               =", type(T))
print("T.__name__            =", T.__name__)
print("T.__bound__           =", T.__bound__)
print("T.__constraints__     =", T.__constraints__)
print("T.__covariant__       =", T.__covariant__)
print("T.__contravariant__   =", T.__contravariant__)
print("T.__infer_variance__  =", T.__infer_variance__)
