# Chapter 4: December 1989

The three preceding chapters were prologue: the ABC ledger (1), the other ancestors (2), the values (3). This chapter is the founding itself, the Christmas break of 1989 when Guido van Rossum wrote the prototype, and the one architectural decision it carried that everything in this book rests on: **everything is an object.**

Not just the data, the numbers, strings, and lists ABC also had, but the functions, the types, the modules, the code itself. There is no privileged category of "primitives" sitting outside the object system, no split like Java's `int` (a machine value) versus `Integer` (an object wrapping it). In Python, from the prototype forward, there is *one* category, objects, and the smallest integer and the largest class are the same kind of thing. This chapter demonstrates the commitment as it survives in today's interpreter, the direct descendant of the 1991 release (Chapter 1's `0.9.0`), and closes Volume 1 on the sentence the whole timeline elaborates.

The historical frame is Chapter 1's: the dates (Christmas 1989 for the prototype, February 1991 for `0.9.0`) are sourced to Guido's own accounts and stated at the confidence the record supports; the code shows the *modern consequence* of the 1989 decision on the verification interpreters, never regenerating 1991 output.

## Section index

- **4.1** The constraint: a scripting language that had to be uniform
- **4.2** Data is objects, and so is everything else
- **4.3** Functions are objects: first-class by construction
- **4.4** Types are objects: turtles all the way down
- **4.5** No privileged primitives, and what that cost
- **4.6** Edges: what "everything is an object" does not mean
- **4.7** Connections
- **4.8** Exercises
- **4.9** Summary and cross-references

Listings live under `code/ch216/` and are re-executed by `make verify` on the verification interpreters.

---

## 4.1 The constraint: a scripting language that had to be uniform

The Amoeba project needed a scripting language (Chapter 1), and a scripting language has a specific constraint: it glues things together, so it must handle *every* kind of value uniformly. A script that can pass integers to functions but not functions to functions, or that can store strings in lists but not types in lists, forces the programmer to know which values are "real objects" and which are "primitives", exactly the friction ABC's inextensibility caused (Chapter 1) in a different form.

Guido's answer was to have *no* second category. In the 1989 prototype, a value was a `PyObject`, always, whether it was an integer or a function or the `int` type itself. This is a stronger commitment than "Python has objects", it is "Python has *only* objects", and it is the decision that made the language uniform enough to glue anything to anything. The extensibility decision (Chapter 1, a C type is an object) and this decision (everything is an object) are two views of one commitment: the object system has no boundary, not between built-in and user types, and not between data and code.

---

## 4.2 Data is objects, and so is everything else

```python
# code/ch216/l01_everything_is_an_object.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- data is objects (obviously) - but so is everything else ---
  42 is an object      : True
  'hi' is an object    : True
  [1,2] is an object   : True
```

**The obvious half establishes the baseline.**
`42`, `'hi'`, and `[1, 2]` are all instances of `object`, the root of the type hierarchy. This much any object-oriented language provides for its data. The interesting claim, the one that distinguishes Python, is that the *non*-data, the functions, types, and modules, are objects too, by the same test, in the same hierarchy. The baseline is here so the extension can be measured against it: if functions and types pass the identical `isinstance(x, object)` test that `42` passes, then there is genuinely one category, which is §4.3 and §4.4.

---

## 4.3 Functions are objects: first-class by construction

```text
--- functions are objects: they have attributes and identity ---
  a function has a type   : function
  and attributes you set  : 'annotated at runtime'
  and can be passed around: [2, 3, 4]
```

**A function is a first-class object, and everything that makes functional Python work follows from it.**
`a_function` has a type (`function`), carries attributes you assign at runtime (`a_function.tag`), and can be passed to `map` like any value. Because a function is an object, it can be stored in a list, returned from another function, bound to a name, and given attributes, and that single property is why decorators, closures, higher-order functions, and callbacks all *just work* with no special language mechanism. Python did not add "support for passing functions"; functions were objects, and objects can be passed, so the capability was free.

**The senior-engineer contrast.** In C, a function is not a value, it is a symbol with an address, and "passing a function" means passing a function *pointer*, a distinct and more limited thing (no attributes, no closures). In Java before lambdas, "passing behaviour" required wrapping it in an object implementing an interface. Python needed neither, because a function *was* an object from the prototype, so the machinery those languages bolted on later (function objects, method references, functional interfaces) was Python's default. Deep A owns the object; Deep F owns what makes a function callable and how closures capture their environment.

---

## 4.4 Types are objects: turtles all the way down

```text
--- types are objects, and a class is an instance of a type ---
  type of AClass          : type
  type of int             : type
  type of type            : type
  a class is an instance of 'type'; 'type' is an instance of
  itself. the object system has no floor and no ceiling - it is
  turtles all the way down, by design (Deep A, Deep C own this)
```

**The object system has no floor and no ceiling, and that is deliberate.**
`AClass` is an instance of `type`; so is `int`; and `type` is an instance of *itself*. A class is an object (an instance of the type `type`), which means classes can be created at runtime (Chapter 1's `type(...)` call), passed around, and inspected, and it means `type` is the root that terminates the regress by being its own type. There is no special "class thing" outside the object system, a class is an object like any other, whose type happens to be `type`. This is the architectural elegance that makes metaclasses (Deep C), runtime class creation, and full introspection (Deep S) possible: they are not features added to a closed system but consequences of the system having no boundary.

**This is the decision at its most radical.**
Most object-oriented languages have objects (instances) and a separate, privileged notion of classes that are *not* objects (you cannot pass `int` as a value in C++ the way you pass an `int`). Python collapsed the distinction: classes are objects, `type` is an object, the tower is uniform from the smallest integer to `type` itself. The cost is conceptual (the "a class is an instance of a metaclass" idea takes getting used to) and real (the machinery to make it work, Deep C), but the payoff is a language with no seams, which is exactly what a glue language needs.

---

## 4.5 No privileged primitives, and what that cost

```text
--- there is no privileged 'primitive' category ---
  int has methods          : 6 = (42).bit_length()
  int is subclassable      : 6 (a Ticks, still an int)
```

**The smallest value in Python is a full object, and there is no primitive escape hatch.**
`(42).bit_length()` calls a *method* on an integer, because an integer is an object with methods, not a machine word. And `int` is subclassable (`class Ticks(int)`), so even the most primitive-seeming type participates fully in the object system, a `Ticks` is an `int` and can be used anywhere an `int` can (the order book's fixed-point prices, Chapter 131, are exactly this pattern). There is no Java-style `int`-versus-`Integer` split, no boxing and unboxing, no category of values that are "not really objects".

**And this is where the founding decision's cost becomes concrete, closing the volume honestly.**
Every value carrying a full object identity means every value carries an *object header*, a type pointer, a reference count, and more (Deep A, Chapter 89 measures it: a small Python `int` costs ~28 bytes where a C `int` costs 4). The uniformity that makes Python pleasant and extensible is paid for on *every object, forever*, in memory and in the indirection of going through the object system for operations a machine could do in one instruction. This trade, chosen in December 1989, is the root of Deep K's entire performance discipline and Deep M's entire escape-to-C boundary: Python is slower than C *because* everything is an object, and Python is more extensible and uniform than C *because* everything is an object. The timeline that Volume 2 opens is thirty-five years of refining that trade, never abandoning it.

---

## 4.6 Edges: what "everything is an object" does not mean

**It does not mean everything is mutable.**
Integers, strings, and tuples are objects *and* immutable; "everything is an object" is about identity and uniformity, not about mutability. The immutable objects (Deep A) are still full objects, they have types, methods, and identity, they simply do not allow in-place change, which is a separate design axis (and the reason `int` can be safely shared and cached, Chapter 89).

**It does not mean everything is equally cheap.**
Objects have wildly different costs, a cached small `int` is nearly free, a large `dict` is expensive, and the uniform object *model* hides a very non-uniform object *economy* (Deep K, Chapter 89). "Everything is an object" is a statement about the type system's shape, not about performance, and conflating the two is the mistake behind most "Python is slow" surprise.

**It does not mean there is no C underneath.**
The object system is uniform *to Python code*; underneath, `int` is a C struct with special-cased arithmetic, and the interpreter takes shortcuts (the specializing interpreter, Deep H) precisely because it knows the C-level reality behind the uniform Python-level model. The uniformity is a *contract* the implementation upholds, not a description of the machine, and the gap between them is where CPython's optimisations live.

**And it does not mean the model never leaks.**
`is` versus `==` (identity versus equality), the small-int cache, string interning, all are places where the object model's implementation details (Deep A) surface into observable behaviour. "Everything is an object" is true; "every object behaves identically" is not, and the leaks are the subject of some of the language's subtlest bugs (Chapter 89's measurement discipline exists partly to make them visible).

---

## 4.7 Connections

**Forward, and this closes Volume 1 into Volume 2.**
The object model this chapter founds is Deep A (the `PyObject`, the header, the cost); the type-of-types machinery is Deep C (metaclasses, descriptors); functions as objects and their callability are Deep F; introspection the uniformity enables is Deep S; the performance cost of universal objecthood is Deep K and Chapter 89; the escape to C when the cost is too high is Deep M. Volume 2 (Chapter 5 forward) opens the 1.x language, where this founding commitment gets its first decade of refinement.

**Across books.**
"Everything is an object" is precisely what makes the Book I / Book II boundary work: a C++ object from the shared trading system's matching engine is *wrapped* to appear as a Python object (Deep M), and it works because Python has one uniform category a C++ object can be made to join. Book I's C++ has no such uniformity (primitives, objects, and functions are distinct kinds), which is why the *Python* side of the boundary is where the wrapping lives, Python can absorb a C++ object into its object system, but not vice versa. The capstone (Chapter 132) is this founding decision, thirty-five years later, letting a C++ engine appear as an ordinary Python object.

---

## 4.8 Exercises

**1. Test the one category.** Write a function that takes any value, a number, a string, a function, a class, a module, and prints its type and whether it is an `object`. Confirm every case passes, then explain why that uniformity is what a glue language needs.

**2. Attributes on a function.** Assign three attributes to a function object and use them (a cache, a call counter, a tag). Explain what capability this gives that a C function pointer cannot, and connect it to how decorators work (Chapter 5).

**3. Build a class at runtime.** Use `type(name, bases, namespace)` to create a class with a method, instantiate it, and call the method, all with no `class` statement. Explain what "a class is an object" makes possible here.

**4. Subclass a primitive.** Subclass `int` to make a `Price` type that formats as currency; show it works anywhere an `int` does. Relate to Chapter 131's fixed-point order-book prices and explain why Java would need a wrapper class here.

**5. The design question.** "Everything is an object" gives Python uniformity, extensibility, and introspection at the cost of a header on every value (Deep A). Argue whether the trade was right *for Python's goals* (a scripting/glue language), then argue whether the same trade would be right for a systems language (Book I's C++, which chose the opposite), and use the difference to state precisely what "the right design depends on the requirement" means, the thesis this whole series argues.

---

## 4.9 Summary and cross-references

- **December 1989's prototype carried the founding commitment: everything is an object**, the data, the functions, the types, the modules, the code, with no privileged "primitive" category (contrast Java's `int` vs `Integer`).
- **Functions are objects** (first-class, attribute-bearing, passable), which is why decorators, closures, and higher-order functions work with no special mechanism; **types are objects** (a class is an instance of `type`, `type` is an instance of itself), which is why metaclasses, runtime class creation, and full introspection are consequences rather than features.
- **There is one category, objects, from the smallest int to `type` itself**: `(42).bit_length()` is a method call, `int` is subclassable, and the object system has no floor and no ceiling.
- **The cost, chosen at the start, is a header on every value** (Deep A, Chapter 89: ~28 bytes for a small int), paid forever in memory and indirection, and it is the root of both Python's slowness relative to C and its extensibility and uniformity relative to C, the trade the whole timeline refines.
- **The edges**: everything-is-an-object does not mean everything is mutable, equally cheap, free of C underneath, or free of model leaks (`is` vs `==`, the small-int cache).

**Cross-references.** The ABC/Modula/C lineage and the values → Chapters 1-3. The object model and its cost → Deep A, Chapter 89. Metaclasses and descriptors → Deep C. Functions and closures → Deep F. Introspection → Deep S. Performance and the escape to C → Deep K, Deep M. The 1.x language that refines this → Chapter 5 forward. The C++ object as a Python object → Chapter 132, Deep M.
