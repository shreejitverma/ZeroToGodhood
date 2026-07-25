"""Listing 31.1 - a class is an object, type() builds it, and a metaclass hooks
its creation.

Chapter 4 showed that a class IS a PyTypeObject, an instance of type. That means
`class` is not the only way to make one: type() called with three arguments
(name, bases, namespace) builds a class at runtime, and that IS what the class
statement does under the hood. A metaclass customizes that construction by
subclassing type.
"""

# --- type(name, bases, namespace) builds a class, exactly as `class` does ---
Dynamic = type("Dynamic", (object,), {"x": 1, "greet": lambda self: "hi"})
print("--- a class built at runtime with type() ---")
print("  Dynamic.__name__ :", Dynamic.__name__)
print("  Dynamic().x      :", Dynamic().x)
print("  Dynamic().greet():", Dynamic().greet())
print("  type(Dynamic)    :", type(Dynamic).__name__, "(its metaclass is type)")


# --- a metaclass is a subclass of type; it hooks class creation ---
class Meta(type):
    def __new__(mcs, name, bases, namespace):
        namespace["created_by_meta"] = True         # inject an attribute at creation
        return super().__new__(mcs, name, bases, namespace)


class WithMeta(metaclass=Meta):
    pass


print()
print("--- a metaclass customizes the class object as it is built ---")
print("  WithMeta.created_by_meta:", WithMeta.created_by_meta)
print("  type(WithMeta)          :", type(WithMeta).__name__, "(Meta, not type)")

print()
print("--- type is its own metaclass: the tower bottoms out ---")
print("  type(type) is type:", type(type) is type)
print("  type(object) is type:", type(object) is type)
print()
print("`class C(metaclass=M): ...` calls M(name, bases, namespace), which for the")
print("default metaclass `type` is exactly the type() call above. A metaclass's")
print("__new__ runs once per class DEFINITION, not per instance.")
