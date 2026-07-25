"""Listing 114.2 - classmethod and staticmethod: two more descriptors.

Both are descriptors (Chapter 32) that change what __get__ binds:
  - classmethod's __get__ binds the CLASS, not the instance, so the method gets
    cls. Its canonical use is ALTERNATIVE CONSTRUCTORS (cls(...) works for
    subclasses too). Called on an instance, it still gets the class.
  - staticmethod's __get__ returns the plain function with NO binding: no self,
    no cls. It is a plain function that lives in the class namespace.
Contrast with a normal instance method, whose __get__ binds the instance. This
listing shows all three and the alternative-constructor pattern.
"""


class Date:
    def __init__(self, year, month, day):
        self.year, self.month, self.day = year, month, day

    @classmethod
    def from_string(cls, s):             # alternative constructor: uses cls
        y, m, d = (int(p) for p in s.split("-"))
        return cls(y, m, d)              # cls, so subclasses build subclass instances

    @staticmethod
    def is_valid_year(y):                # a utility; needs neither self nor cls
        return 1 <= y <= 9999

    def iso(self):                       # normal instance method: uses self
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


def main() -> None:
    print("--- classmethod: alternative constructor, receives cls ---")
    d = Date.from_string("2026-07-25")
    print(f"  Date.from_string('2026-07-25').iso() : {d.iso()}")

    print("--- classmethod called via instance still gets the class ---")
    print(f"  d.from_string('1999-12-31').iso()    : {d.from_string('1999-12-31').iso()}")

    print("--- staticmethod: no binding, plain function in the namespace ---")
    print(f"  Date.is_valid_year(2026) : {Date.is_valid_year(2026)}")
    print(f"  Date.is_valid_year(0)    : {Date.is_valid_year(0)}")

    print("--- all three are descriptors, binding differently ---")
    print(f"  type(Date.__dict__['from_string'])  : {type(Date.__dict__['from_string']).__name__}")
    print(f"  type(Date.__dict__['is_valid_year']): {type(Date.__dict__['is_valid_year']).__name__}")
    print(f"  type(Date.from_string) (bound)      : {type(Date.from_string).__name__}   (cls bound)")
    print(f"  type(Date.is_valid_year)            : {type(Date.is_valid_year).__name__}   (plain function)")

    print("--- the rule ---")
    print(f"  classmethod binds cls (use for alternative constructors);")
    print(f"  staticmethod binds nothing (a namespaced plain function)")


if __name__ == "__main__":
    main()
