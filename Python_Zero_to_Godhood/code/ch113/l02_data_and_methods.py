"""Listing 113.2 - data vs non-data descriptors, and why methods are descriptors.

The descriptor's method set determines its PRECEDENCE in attribute lookup (the
ranking of Chapter 21):
  - A DATA descriptor defines __set__ or __delete__. It OUTRANKS the instance
    __dict__: it cannot be shadowed by an instance attribute. (property, __slots__.)
  - A NON-DATA descriptor defines only __get__. The instance __dict__ OUTRANKS it:
    an instance attribute of the same name shadows it. (functions, so a per-instance
    override is possible.)
And the punchline: a plain FUNCTION is a non-data descriptor. Accessing func on an
instance calls func.__get__, which returns a BOUND METHOD (self already supplied).
That is the entire mechanism of method binding. This listing shows both.
"""


class NonData:
    def __get__(self, obj, objtype=None):
        return "from non-data descriptor"


class HasData:
    def __get__(self, obj, objtype=None):
        return "from data descriptor"

    def __set__(self, obj, value):
        pass                             # having __set__ makes it a DATA descriptor


def main() -> None:
    print("--- a NON-data descriptor is shadowed by the instance dict ---")
    class A:
        attr = NonData()
    a = A()
    a.__dict__["attr"] = "from instance dict"
    print(f"  a.attr : {a.attr}   (instance dict wins over non-data descriptor)")

    print("--- a DATA descriptor outranks the instance dict ---")
    class B:
        attr = HasData()
    b = B()
    b.__dict__["attr"] = "from instance dict"
    print(f"  b.attr : {b.attr}   (data descriptor wins; instance dict ignored)")

    print("--- a plain function IS a non-data descriptor ---")
    class M:
        def greet(self):
            return "hello"
    print(f"  M.greet has __get__     : {hasattr(M.greet, '__get__')}")
    print(f"  M.greet (on class)      : {type(M.greet).__name__}   (plain function)")

    print("--- accessing it on an instance calls __get__ -> a BOUND METHOD ---")
    m = M()
    bound = m.greet
    print(f"  m.greet (on instance)   : {type(bound).__name__}   (bound method)")
    print(f"  m.greet.__self__ is m   : {bound.__self__ is m}   (self is bound in)")
    print(f"  m.greet()               : {bound()}")

    print("--- the rule ---")
    print(f"  __set__/__delete__ => data descriptor (outranks instance dict);")
    print(f"  __get__ only => non-data (shadowable). Functions bind self via __get__")


if __name__ == "__main__":
    main()
