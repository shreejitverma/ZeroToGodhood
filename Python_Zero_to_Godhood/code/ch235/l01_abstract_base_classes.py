"""Listing 235.1 - Python 2.6 (2008): abstract base classes, isinstance for duck typing.

Duck typing asks 'does it behave like X?', but isinstance() historically asked
'does it INHERIT from X?' - a stricter, wrong question for a duck-typed language.
PEP 3119's abstract base classes (the `abc` module, 2.6) reconciled the two:
an ABC can declare 'anything with these methods counts as one of me' via
__subclasshook__, and can REGISTER unrelated classes as virtual subclasses, so
isinstance() finally answers the behavioural question. ABCs also enforce
contracts: @abstractmethod makes a class uninstantiable until every abstract
method is overridden. Deep C owns the metaclass machinery underneath; this is
the release that made 'is this a sequence? a mapping? a number?' a checkable
question without a shared base class. Verified on current interpreters.
"""

from abc import ABC, abstractmethod
from collections.abc import Sized, Sequence, Mapping


def main() -> None:
    print("--- ABCs answer BEHAVIOURAL isinstance, without shared inheritance ---")
    print(f"  isinstance([], Sequence)   : {isinstance([], Sequence)}")
    print(f"  isinstance('hi', Sequence) : {isinstance('hi', Sequence)}")
    print(f"  isinstance({{}}, Mapping)    : {isinstance({}, Mapping)}")
    print(f"  isinstance({{}}, Sequence)   : {isinstance({}, Sequence)}")
    print("  list, str, and dict do NOT inherit from these ABCs, yet isinstance")
    print("  says list/str are Sequences and dict is a Mapping. the ABC answers")
    print("  'does it behave like one?', which is the duck-typing question")

    print("--- __len__ alone makes you a Sized: the structural hook ---")
    class Bag:
        def __len__(self):
            return 3
    print(f"  Bag defines only __len__")
    print(f"  isinstance(Bag(), Sized) : {isinstance(Bag(), Sized)}")
    print(f"  issubclass(Bag, Sized)   : {issubclass(Bag, Sized)}")
    print("  Bag never mentions Sized, but Sized.__subclasshook__ checks for a")
    print("  __len__ method and says yes. the ABC recognises the SHAPE of the")
    print("  class, not its ancestry - structural typing built into isinstance")

    print("--- registration: declare an unrelated class a virtual subclass ---")
    class Temperature:
        def __init__(self, c):
            self.celsius = c

    from numbers import Number
    Number.register(Temperature)                 # 'treat Temperature as a Number'
    t = Temperature(20)
    print(f"  Number.register(Temperature)")
    print(f"  isinstance(Temperature(20), Number) : {isinstance(t, Number)}")
    print(f"  but Temperature.__mro__ has no Number : "
          f"{Number not in Temperature.__mro__}")
    print("  register() makes isinstance say yes WITHOUT touching the class or")
    print("  its bases - a virtual subclass. you can retrofit a third-party")
    print("  class into an ABC hierarchy you do not control")

    print("--- @abstractmethod: a contract the interpreter enforces ---")
    class Repository(ABC):
        @abstractmethod
        def get(self, key): ...
        @abstractmethod
        def put(self, key, value): ...

    try:
        Repository()                             # abstract methods unimplemented
    except TypeError as exc:
        print(f"  instantiating the ABC raises : TypeError({exc})")

    class DictRepo(Repository):
        def __init__(self): self._d = {}
        def get(self, key): return self._d.get(key)
        def put(self, key, value): self._d[key] = value

    r = DictRepo()
    r.put("x", 1)
    print(f"  a concrete subclass implementing both methods works : {r.get('x')}")
    print("  a class with an unimplemented @abstractmethod cannot be")
    print("  instantiated - the contract is enforced at construction, not left")
    print("  to a NotImplementedError at some later call site")

    print("--- the constraint answered ---")
    print("  duck typing asks 'does it behave like X?' but isinstance asked")
    print("  'does it inherit X?'. ABCs (2.6) reconciled them: __subclasshook__")
    print("  recognises shape, register() adopts unrelated classes, and")
    print("  @abstractmethod enforces the contract. isinstance finally answers")
    print("  the behavioural question a duck-typed language actually asks")


if __name__ == "__main__":
    main()
