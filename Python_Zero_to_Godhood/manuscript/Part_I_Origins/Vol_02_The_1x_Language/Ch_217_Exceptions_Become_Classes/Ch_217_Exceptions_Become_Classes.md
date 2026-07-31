# Chapter 7: Exceptions Become Classes

Volume 1 founded Python on "everything is an object" (Chapter 4). This volume watches the 1.x line (1994-2000) turn that founding into a working language, and this chapter is one of its most consequential single decisions: in **Python 1.5 (1997)**, exceptions stopped being strings and became **classes**.

The constraint 1.5 answered was concrete. Early Python raised strings: `raise "file error"`. This *signalled* a problem, but it could not *organise* problems. You could not catch "any I/O error" without enumerating every string an I/O operation might raise, and two unrelated modules that both raised the string `"error"` were indistinguishable to a handler. String exceptions had no superclass, so they had no *family*, and a language whose errors have no families cannot let a handler say "catch any error of this kind". Class-based exceptions gave errors a hierarchy, and the hierarchy gave handlers *selection*: catch a base class, catch every subclass.

The change deprecated string exceptions (removed entirely in Python 2.6/3.0), and its consequences define how Python code handles failure to this day, the EAFP style, the domain-exception base class, exception chaining, and eventually exception groups (Chapter 104). This chapter demonstrates the modern consequence, the exception *tree*, on the verification interpreters, where selective handling by hierarchy is so fundamental it is hard to imagine the string-era language.

## Section index

- **7.1** The constraint: strings can signal but not organise
- **7.2** The exception tree, and what strings could not have
- **7.3** Catch a base class, catch the subtree
- **7.4** EAFP: the tree made "ask forgiveness" idiomatic
- **7.5** What the tree grew into
- **7.6** Edges: the hierarchy's own hazards
- **7.7** Connections
- **7.8** Exercises
- **7.9** Summary and cross-references

Listings live under `code/ch217/` and are re-executed by `make verify` on the verification interpreters.

---

## 7.1 The constraint: strings can signal but not organise

A string exception is a bare signal: `raise "disk full"` says *something* went wrong and names it, and a handler `except "disk full":` can catch that exact string. This is enough for a program with a handful of distinct errors. It fails the moment errors need *structure*.

Consider a program that talks to the filesystem, the network, and a database, each of which can fail a dozen ways. With string exceptions, a handler that wants to catch "any filesystem error" must know all twelve filesystem strings, and if the filesystem library adds a thirteenth, the handler silently stops catching it. Worse, the network library might use the string `"timeout"` and the database library might also use `"timeout"`, and a handler catching `"timeout"` catches both, or the wrong one, with no way to distinguish. Strings are flat; errors are hierarchical; the mismatch is the constraint.

The 1.5 answer was to make an exception a *class*, so that errors could form a tree: `FileNotFoundError` under `OSError` under `Exception`, and a handler naming `OSError` catches the whole filesystem subtree, present and future. This is the founding "everything is an object" decision (Chapter 4) applied to errors: because a class is an object with a base-class chain, errors gained families, and families gave handlers the selection strings could never provide.

---

## 7.2 The exception tree, and what strings could not have

```python
# code/ch217/l01_exceptions_become_classes.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the built-in exception tree is a hierarchy, by design ---
  ValueError         : ValueError -> Exception -> BaseException
  KeyError           : KeyError -> LookupError -> Exception -> BaseException
  FileNotFoundError  : FileNotFoundError -> OSError -> Exception -> BaseException
  ZeroDivisionError  : ZeroDivisionError -> ArithmeticError -> Exception -> BaseException
  every exception is a class with a base-class chain up to
  BaseException - which is exactly what string exceptions could
  not have (a string has no superclass)
```

**Every exception has a base-class chain, and that chain is the organisation strings lacked.**
`KeyError` is a `LookupError` is an `Exception` is a `BaseException`; `FileNotFoundError` is an `OSError`. The intermediate classes (`LookupError`, `OSError`, `ArithmeticError`) are the *families*, catch `LookupError` and you catch both `KeyError` and `IndexError`; catch `OSError` and you catch every filesystem and network error CPython defines. A string has no superclass, so it could never sit in such a tree, and the whole point of the 1.5 change is visible here: the chain up to `BaseException` is the structure that makes selective handling possible.

**The tree is designed, not accidental.**
`BaseException` at the root, `Exception` below it (for errors ordinary code should catch), and special siblings like `KeyboardInterrupt` and `SystemExit` *under `BaseException` but not `Exception`* (so `except Exception` does not swallow a Ctrl-C), the hierarchy encodes policy. That `except Exception` catches "normal" errors but not control-flow signals is a deliberate design that string exceptions could not express, and it is why the standard advice is `except Exception`, not the bare `except:` that also catches `KeyboardInterrupt`.

---

## 7.3 Catch a base class, catch the subtree

```text
--- catch a base class, catch the whole subtree ---
  raised InsufficientFunds   caught as TradingError : InsufficientFunds
  raised MarketClosed        caught as TradingError : MarketClosed
  one except clause handles every trading error, because the
  handler names a BASE class. this is the selection string
  exceptions could not do: 'catch any error of THIS family'
```

**A domain base class turns a family of errors into one handler, and that is the pattern the tree enables.**
`InsufficientFunds` and `MarketClosed` both subclass `TradingError`, so a single `except TradingError` catches either, and any future trading error added under `TradingError` is caught by the same clause with no change. This is the *idiom* class-based exceptions created: define a base exception for your domain, subclass it for specific failures, and let callers catch the base to handle "any error from this subsystem". String exceptions could not do this, there was no "any string of this family", and so the every-library-defines-a-base-exception convention (which the entire ecosystem follows) is a direct consequence of the 1.5 decision.

**This is selection, and selection is the whole value.**
A handler that catches `TradingError` is making a precise statement: "I handle trading errors here; I do not handle everything, and I do not handle nothing". It catches more than one specific error (the family) but less than all errors (not `KeyError` from a bug), and that precision, catch exactly the family you understand, let the rest propagate, is what makes Python error handling composable. The trading service of Deep V (Chapter 131's `TradingError` is this exact pattern) validates and rejects using this hierarchy, catching domain errors it can turn into 422 responses while letting bugs propagate to the 500 handler.

---

## 7.4 EAFP: the tree made "ask forgiveness" idiomatic

```text
--- LBYL vs EAFP: the tree enables 'ask forgiveness' ---
  LBYL get('ACME')=100, get('X')=None
  EAFP get('ACME')=100, get('X')=None
  class-based exceptions made EAFP - try the operation, catch the
  specific failure - Python's idiomatic style, because you can
  catch EXACTLY the exception you expect and let others propagate
```

**Class-based exceptions made "easier to ask forgiveness than permission" a viable idiom, and Python adopted it as its default style.**
The two functions produce identical results, but they embody opposite philosophies. LBYL (Look Before You Leap) checks `if sym in prices` *then* accesses, C's and Java's default. EAFP (Easier to Ask Forgiveness) *tries* the access and catches `KeyError`, Python's idiomatic choice. EAFP is only safe because you can catch the *specific* exception you expect (`KeyError`) and let every other exception propagate, which requires exceptions to be distinguishable classes. In the string era, EAFP was dangerous, catching a string might catch the wrong failure; class-based exceptions with precise types made "try it and catch exactly what you expect" safe, and Python's culture shifted to prefer it.

**Why EAFP is often better than LBYL is a real technical argument, not just style.**
LBYL has a race: between the `if sym in prices` check and the access, another thread (or a callback) could remove the key, so the check is stale by the time you act (Chapter 99's check-then-act, exactly). EAFP has no race, the operation and its failure are atomic. LBYL also duplicates the lookup (check, then access, two `__contains__`/`__getitem__` calls); EAFP does one. So EAFP is frequently *faster* and *more correct*, and it is idiomatic Python precisely because the 1.5 class-based exceptions made catching "exactly the expected failure" possible.

---

## 7.5 What the tree grew into

```text
--- chaining: an exception carries its cause (Python 3.0+) ---
  TradingError raised FROM KeyError
```

**The 1.5 decision was the root every later exception feature grew on.**
Exception *chaining* (`raise X from Y`, Python 3.0) records that one exception was caused by another, so `TradingError.__cause__` is the `KeyError` that triggered it, preserving the full failure story through a traceback. This is only meaningful because exceptions are objects that can *hold* another exception, the string era had nowhere to put a cause. From the same root grew implicit chaining (an exception raised while handling another records `__context__`), exception *notes* (`add_note`, Python 3.11), and **exception groups** (`except*`, Python 3.11, Chapter 104), which let structured concurrency raise many exceptions at once. Every one of these is a class-based exception feature, impossible on strings, and the timeline from 1.5 to 3.11's `except*` is one continuous elaboration of "an exception is an object with structure".

---

## 7.6 Edges: the hierarchy's own hazards

**Catching too broad a base swallows bugs.**
`except Exception` catches your domain errors *and* the `KeyError` from a typo in your own code; a handler that catches too high in the tree hides bugs as if they were expected failures. The discipline is to catch the *narrowest* class that covers what you actually handle, `except TradingError`, not `except Exception`, so that unexpected errors (bugs) propagate loudly (Chapter 3's "errors should never pass silently").

**`except BaseException` (or bare `except:`) catches control flow.**
`KeyboardInterrupt` and `SystemExit` are under `BaseException`, not `Exception`, so a bare `except:` swallows Ctrl-C and `sys.exit()`, turning a interruptible program into an unkillable one. The hierarchy's design (control signals above `Exception`) only helps if handlers respect it: catch `Exception`, never bare.

**Custom exceptions should subclass `Exception`, and usually a domain base.**
An exception subclassing `BaseException` directly escapes `except Exception` handlers (surprising), and one that subclasses nothing relevant cannot be caught by family. The convention, a single domain base under `Exception`, then specific subclasses, is what makes the hierarchy useful, and libraries that ignore it (raising bare `Exception` or `ValueError` for domain errors) force callers into fragile handling.

**Over-deep hierarchies are as bad as flat ones.**
A ten-level exception tree where every error is its own leaf class is as hard to catch correctly as strings were, callers cannot know which of ten levels to catch. The useful depth is shallow, a domain base and a handful of specific subclasses, and resisting the urge to model every failure as its own class is part of designing an exception hierarchy well.

---

## 7.7 Connections

**Backward.**
The Modula-3 exception model this builds on is Chapter 2; the "errors should never pass silently" value it serves is Chapter 3; "everything is an object" (a class is an object with a base chain) is Chapter 4. The low-level unwinding mechanism is Chapter 6 (this volume).

**Forward.**
Exception groups and `except*` are Chapter 104 (Deep J); zero-cost exceptions (the non-error path is free) are Chapter 73 (Deep H); the `TradingError` domain-hierarchy pattern in a real service is Chapter 131 (Deep V); the testing discipline that asserts `raises` and depends on exceptions being loud is Deep O.

**Across books.**
**Book I**'s C++ uses class-based exceptions too (they were C++'s from the start), and the shared trading system's error hierarchy crosses the boundary: a C++ `TradingError` and a Python `TradingError` model the same failures, and the C-API (Deep M) translates a C++ exception into a Python one at the boundary. The 1.5 decision made Python's side of that translation possible, an error can be a class with a family, matching C++'s model.

---

## 7.8 Exercises

**1. Map the tree.** Walk the base-class chain of ten built-in exceptions; draw the tree. Identify which intermediate classes (`OSError`, `LookupError`) are the "family" catch points and which are leaves.

**2. Design a hierarchy.** For a domain you know, design a shallow exception hierarchy (one base, a few subclasses); write a caller that catches the base and one that catches a specific subclass, and explain when each is right.

**3. EAFP vs LBYL race.** Construct the check-then-act race in LBYL (Chapter 99): a dict access guarded by `if key in d` where another thread deletes the key between. Show EAFP has no such race and explain why.

**4. Chain a cause.** Write code that catches a low-level exception and re-raises a domain exception `from` it; inspect `__cause__` and show the full traceback preserving both. Relate to Chapter 131's boundary error handling.

**5. The design question.** Class-based exceptions gave selection at the cost of requiring every library to design a hierarchy (and many do it badly, flat, too deep, or subclassing the wrong base). Argue whether the language should enforce any hierarchy discipline (a required domain base, a depth limit) or leave it to convention, and find one standard-library exception hierarchy you consider well-designed and one you consider poorly-designed, with reasons.

---

## 7.9 Summary and cross-references

- **Python 1.5 (1997) made exceptions classes**, deprecating string exceptions (removed in 2.6/3.0), because strings could *signal* a problem but not *organise* problems, a string has no superclass, so it has no family, and no family means no selective handling.
- **The class tree gave errors families**: catch a base class (`OSError`, `LookupError`, a domain `TradingError`) and catch its whole subtree, present and future, which is the selection strings could never provide and the root of the every-library-defines-a-base-exception convention.
- **The tree made EAFP idiomatic**: because you can catch *exactly* the expected exception and let others propagate, "try it and ask forgiveness" became Python's default style, and it is often more correct (no check-then-act race, Chapter 99) and faster (one lookup, not two) than LBYL.
- **The 1.5 decision is the root every later feature grew on**: chaining (`from`), implicit context, notes, and exception groups (`except*`, Chapter 104), each impossible on strings, each an elaboration of "an exception is an object with structure".
- **The hazards are the hierarchy's own**: catching too broad swallows bugs, bare `except:` catches control flow, custom exceptions must subclass sensibly, and over-deep trees are as bad as flat ones.

**Cross-references.** The exception model's origin and the loud-errors value → Chapters 2, 3. Everything-is-an-object → Chapter 4. Unwinding → Chapter 6. Exception groups → Chapter 104. Zero-cost exceptions → Chapter 73. The domain hierarchy in a service → Chapter 131. Check-then-act races → Chapter 99. The C++ boundary → Deep M.
