# Chapter 2: The Other Ancestors

Chapter 1 read the ABC ledger, the language Guido van Rossum set out to fix. But ABC was not Python's only parent, and reading Python as "ABC, corrected" misses the two other languages whose marks are in every program written today. **Modula** (Modula-2 and its successor Modula-3) gave Python the **module** as a first-class, named namespace with explicit import, and the **exception** as structured control flow. **C** gave the implementation substrate, and, just as importantly, the *counter-example*: a Python integer is unbounded precisely because Guido refused C's machine-word `int`.

This chapter is the rest of the lineage, and its method is Chapter 1's. The historical influences are stated at the confidence the record supports (Modula's module system and Modula-3's exception model are well-documented influences Guido has named in his own accounts of Python's design). The code demonstrates the **modern consequence** of each inheritance on the verification interpreters, it does not regenerate 1991 output, and says so. The point is the thesis this volume closes on: **Python is not any one of its ancestors; it is a set of deliberate choices *about* them**, which is why the timeline that follows is a series of constraints answered, never a changelog.

## Section index

- **2.1** The problem: a scripting language needs structure at the seams
- **2.2** Modula's module: a namespace you import from
- **2.3** Modula-3's exception: errors as raised objects, not returned codes
- **2.4** C's substrate, and the integer that refused to be a machine word
- **2.5** The three ancestors, as one sentence each
- **2.6** Edges: what Python took and then changed
- **2.7** Connections
- **2.8** Exercises
- **2.9** Summary and cross-references

Listings live under `code/ch214/` and are re-executed by `make verify` on the verification interpreters, demonstrating modern consequences of 1989 decisions.

---

## 2.1 The problem: a scripting language needs structure at the seams

Chapter 1 established the two flaws Guido diagnosed in ABC: no file I/O and no extensibility. But fixing those flaws opened a design question ABC never had to answer, because ABC was one monolithic environment. **If Python is to be a language that grows in pieces, third-party code, a standard library, embedded interpreters, then it needs structure at its seams**: a way to name and import units of code, and a way to signal and handle errors across those units.

C's answers were inadequate for a high-level scripting language. C's `#include` is textual substitution, not a namespace; two headers defining the same name collide, and there is no object you can inspect at runtime to ask "what does this module provide". C's error model is the returned code, every call potentially returns an error you must check, and forgetting to check is the archetypal C bug (Chapter 84's `errno` discipline is this problem, decades later). A language built for programmers who are not systems programmers (ABC's audience, which Python inherited) could not ship C's seams.

Modula had solved both. Niklaus Wirth's Modula-2, and its research successor Modula-3, were designed around the *module* as the unit of program structure and around *exceptions* as the unit of error handling. Guido drew on both, and the drawing is visible today.

---

## 2.2 Modula's module: a namespace you import from

```python
# code/ch214/l01_the_other_ancestors.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- Modula's inheritance I: a module is a namespace object ---
  a module is an object of type : module
  its namespace IS a dict       : dict
  and one can be built at runtime: 42
  Modula gave Python the module as an explicit, named namespace
  you import from - not C's textual #include, but a real object
  with its own dict (Deep G owns the machinery this seeded)
```

**A Python module is a runtime object, not a preprocessor directive.**
`sys` is an object of type `module`; its namespace is a `dict`; and, the tell that it is a genuine runtime construct, one can be *built at runtime* (`types.ModuleType`). This is Modula's model, not C's: a module is a named unit with an explicit interface you import from, and it exists as an inspectable object rather than as text spliced into your compilation unit. The consequences run through the whole language, `import` binds a name to an object (Deep G), a module's `__dict__` is where its globals live (Deep A), and the ability to construct and manipulate modules at runtime underlies plugin systems, lazy imports, and the entire packaging story (Deep N).

**The senior-engineer contrast.** In C, `#include <stdio.h>` pastes the header's text into your file; there is no `stdio` object, no namespace, no way to ask the running program what `stdio` contains. In Modula and in Python, the module is a first-class thing: you can pass it, inspect it, replace it. This is why Python's import system could grow namespace packages (Python 3.3), import hooks, and finders/loaders (Deep G) without changing the language, the module was an object from the start, and objects can be extended.

---

## 2.3 Modula-3's exception: errors as raised objects, not returned codes

```text
--- Modula-3's inheritance: exceptions as structured control ---
  no-fail path : ['try', 'ok', 'finally']
  fail path    : ['try', 'caught:boundary', 'finally']
  try/except/finally is Modula-3's structured exception model:
  errors are not returned codes to check (C) but raised objects
  that unwind the stack to a matching handler (Chapter 6, Deep A)
```

**An error is a raised object that unwinds to a handler, not a code you remember to check.**
The trace shows the structure: `try` runs, and either the body completes (`ok`) or a `raise` transfers control to the matching `except`, and in both cases `finally` runs. This is Modula-3's structured exception model, and it is the opposite of C's convention. In C, a function signals failure by returning a sentinel (`-1`, `NULL`, a nonzero `errno`), and the caller must check every one; a forgotten check is a silent bug that surfaces arbitrarily later. In Python, failure *raises*, and an unhandled exception unwinds the stack to the nearest handler or terminates the program with a traceback, errors are hard to ignore by construction.

**This choice compounds through the whole language.** Because errors are objects (Deep A), they have types (so `except ValueError` can select), carry data (the message, chained causes), and form hierarchies (`IndentationError` is a `SyntaxError`, Chapter 1). Because raising unwinds the stack, `finally` and context managers (`with`, Chapter 5) can guarantee cleanup, and the "zero-cost exceptions" of modern CPython (Chapter 73, Deep H) make the non-error path free. The structured-exception decision, inherited from Modula-3, is the root of Python's entire error-handling story, and Chapter 6 (low-level I/O and exception unwinding) is where its mechanism is first taught.

---

## 2.4 C's substrate, and the integer that refused to be a machine word

```text
--- C's inheritance, and the decision to reject its int ---
  2**200 is an exact Python int  : 1606938044258990275541962092341162602522202993782792835301376
  it did not overflow a 64-bit word (C would): True
  its type is plain int          : int
```

**Python is written in C, but a Python integer is not a C integer, and that gap is the language's defining split.**
`2**200` is an exact value with plain type `int`; it did not wrap around a 64-bit word, as C's `int` or `long` would. This is ABC's arbitrary-precision arithmetic *kept*, over C's fixed-width arithmetic *rejected*, even though C is the implementation language. The split is the heart of CPython: the **value model** comes from ABC (an integer is a mathematical integer, a string is a sequence of characters, a list holds anything), and the **runtime substrate** comes from C (the interpreter, the object layout, the garbage collector are all C). A Python object is a C `struct` (`PyObject`, Deep A) with a value model that owes nothing to C's.

**C is the counter-example as much as the ancestor.** Where C offered a struct, Python built an object (with a type, methods, a refcount, Deep A). Where C offered a machine word, Python built an unbounded integer (Deep A measures its cost: 28+ bytes for a small int, the price of never overflowing). Where C offered manual memory, Python built reference counting and a cyclic collector (Deep B). CPython is the marriage of C's *implementation* efficiency with a value model that is deliberately *not* C's, and every "why is Python slower than C" question in this book (Deep K's whole subject) is a consequence of that marriage, as is every "why is Python so much easier to write" answer.

---

## 2.5 The three ancestors, as one sentence each

```text
--- the three ancestors, as one sentence each ---
  ABC     : the ergonomics (indentation, few powerful types)
  Modula  : the module and the exception (structure at the seams)
  C       : the substrate and the counter-example (unbounded int
            over the machine word, an object over a struct)
```

The lineage compresses to three sentences, and the compression is the volume's thesis. **ABC** gave the ergonomics, indentation as grammar (Chapter 1), a small set of powerful built-in types, readability as a value. **Modula** gave the structure at the seams, the module as a namespace object and the exception as raised control flow, the two mechanisms a growable language needs. **C** gave the substrate *and* the counter-example, the implementation efficiency Python runs on, and the design decisions Python defined itself by refusing.

Python is not any one of them. It is a set of deliberate choices *about* them, keep ABC's clarity, adopt Modula's seams, run on C while rejecting C's value model, and the choices are what a designer made, not features a language accreted. This is why the anti-changelog rule (this book's binding structure) fits Python's history so well: every release from here forward is a *constraint answered*, a problem the world posed that the core developers could not change, met by a specific mechanism. The mechanisms have ancestors; the choices to deploy them are Python's own.

---

## 2.6 Edges: what Python took and then changed

**Modula's static typing: rejected.**
Modula-2 and Modula-3 are statically typed; Python took their module and exception structure but not their type discipline, choosing dynamic typing (Deep A) and adding optional static types only decades later (PEP 484, Python 3.5, Deep I). The seams came from Modula; the typing did not.

**Modula's interface/implementation split: absorbed, not copied.**
Modula-2 separates a module's interface (`.def`) from its implementation (`.mod`); Python has no separate interface file, a module *is* its implementation, and its public interface is convention (`__all__`, leading-underscore privacy) rather than a compiler-enforced boundary. Python took the module concept and made it lighter, trusting programmers where Modula constrained them, the same "quietness in the common case" value ABC's lowercase keywords expressed (Chapter 1).

**C's explicitness: kept at the boundary, hidden in the core.**
Python hides C's manual memory and fixed-width arithmetic from ordinary code, but exposes them exactly at the C-API boundary (Deep M), where an extension author works in C's terms again. The two-layer design, C's efficiency underneath, ABC's ergonomics on top, is the whole architecture, and the boundary between the layers is where this series' shared trading system splits (Chapter 84, the capstone of Deep V).

**And the numeric tower: partly inherited, mostly deferred.**
ABC had sophisticated numerics; Python kept unbounded integers but shipped rationals (`fractions`) and decimals (`decimal`) as *library modules* later, not built-in types, the extensibility decision (Chapter 1) paying off. What could be a library was a library, which is why Python's core stayed small while its capability grew.

---

## 2.7 Connections

**Forward.**
The module system Modula seeded is Deep G (the import machinery) and Deep N (packaging). The exception model from Modula-3 is Chapter 6 (unwinding), Chapter 5 (`with` and cleanup), and Chapter 73 / Deep H (zero-cost exceptions). C's substrate and the object-over-struct decision are Deep A (the object model) and Deep M (the C-API). The unbounded integer's cost is measured in Deep A and Chapter 89.

**Across books.**
C as the substrate is the seam this series is built on: **Book I** is the C++ side of the shared system, and the C-API (Deep M) is where Python's C-derived runtime meets Book I's C++ engine. Python's rejection of C's value model, an object where C has a struct, is exactly what makes the boundary interesting: a C++ object must be *wrapped* to appear as a Python object (a `PyTypeObject`, Chapter 1), because Python's value model is not C's. Deep M owns that wrapping.

---

## 2.8 Exercises

**1. Build a module at runtime.** Using `types.ModuleType`, construct a module with two functions and install it in `sys.modules`; then `import` it by name from other code. Explain what Modula's model makes possible that C's `#include` cannot.

**2. The returned-code counter-example.** Rewrite a small function that raises exceptions into C-style returned-error-code form (return a `(value, error)` tuple, check it at every call). Count the extra lines and the places a check could be forgotten; this is the cost Modula-3's model removed.

**3. Feel the unbounded integer.** Compute `2**1000` in Python and reason about what a C program would need to do the same (arbitrary-precision library, manual allocation). Then measure the Python int's memory with `sys.getsizeof` at a few sizes (Deep A's subject) and explain what the value model costs.

**4. The interface Python does not have.** Modula-2 has separate `.def` (interface) and `.mod` (implementation) files. Design what Python's equivalent would look like and argue why Python chose *not* to have it, using the "quietness in the common case" value from Chapter 1.

**5. The design question.** Python took Modula's module and exception but rejected its static typing, then added optional typing 25 years later (Deep I). Argue whether taking the seams without the typing was the right call for 1989's goals (a scripting language for the Amoeba project), and identify one place in this book where the *absence* of Modula's static typing costs Python something the later optional-typing system only partly recovers.

---

## 2.9 Summary and cross-references

- **ABC was not Python's only ancestor.** Modula gave the **module** (a namespace object you import from, not C's textual `#include`) and Modula-3 gave the **exception** (errors as raised objects that unwind to a handler, not returned codes to check).
- **C gave the substrate and the counter-example.** Python is implemented in C but a Python integer is unbounded (ABC's value model kept, C's machine word rejected), and a Python object is an object, not a struct, the split that defines CPython.
- **The three ancestors compress to one sentence each**: ABC the ergonomics, Modula the seams, C the substrate-and-counter-example, and Python is a set of deliberate choices *about* them, which is why its history is constraints answered, not a changelog.
- **What was taken was also changed**: Modula's static typing and interface files were rejected, C's explicitness was hidden in the core and exposed only at the C-API boundary, and the numeric tower was mostly deferred to libraries, the extensibility decision paying off.
- **The historical influences are stated at the confidence the record supports** and the code demonstrates modern consequences on the verification interpreters, never regenerating 1991 output.

**Cross-references.** Indentation and extensibility (the ABC ledger) → Chapter 1. The module system → Deep G, Deep N. Exception unwinding → Chapter 6; `with` and cleanup → Chapter 5; zero-cost exceptions → Chapter 73, Deep H. The object model and the unbounded int → Deep A. The C-API boundary → Deep M. The language boundary in the shared system → Chapter 84.
