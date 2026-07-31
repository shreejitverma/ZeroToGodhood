# Chapter 288: Except Without Parentheses

## The constraint

To catch several exception types in one handler, you wrote a parenthesized tuple:

```python
except (ValueError, TypeError):
    ...
```

The parentheses were mandatory, and forgetting them had a notorious history.
In Python 2, `except ValueError, e:` was how you *bound* the exception to a variable `e`.
So `except ValueError, TypeError:` in Python 2 did not catch two types - it caught `ValueError` and bound it to a variable named `TypeError`, silently *not* catching actual `TypeError`s.
This was one of the classic Python 2 traps, and Python 3.0 responded by making the parenthesis-free form a `SyntaxError` - safer, because it turned a silent bug into a loud one, but still a papercut: the natural spelling `except A, B:` was simply forbidden, and you had to remember the parentheses every time.

By 3.14, the `as`-based binding syntax (`except SomeError as e:`) had long since replaced the comma-binding of Python 2, so the comma no longer meant "bind."
That freed the comma to mean the obvious thing - "or" - in the unbound case.

The constraint Python 3.14 (2025, PEP 758) answered: **let `except A, B:` (with no `as`) mean "catch either"**, so the natural comma-separated spelling reads naturally.

This is a two-track chapter.
Exception handling is Deep Volume B's subject.
What this chapter owns is the release: the day the obvious spelling was allowed to mean the obvious thing.

## What shipped

PEP 758 allows `except` and `except*` to list exception types *without* parentheses when there is no `as` binding.
With an `as` binding, parentheses remain required (to keep the grammar unambiguous).
Listing 288.1 shows this on the 3.14 builds (it is gated to 3.14+, since the syntax is new).

Verified output (CPython 3.14.6):

```text
--- except without parentheses catches any of the listed types ---
  a ValueError : caught ValueError or TypeError
  a TypeError  : caught ValueError or TypeError
  a KeyError   : caught KeyError or IndexError
  `except ValueError, TypeError:` now means 'catch either one' -
  reading as the plain comma-separated list it looks like. no tuple
  parentheses required when you are not binding with `as`
--- it is exactly equivalent to the parenthesised tuple form ---
  parenthesised form catches TypeError  : 'caught'
  bare-list form catches TypeError       : 'caught'
  same behaviour : True
  the two spellings compile to the same handler. PEP 758 just removed
  the required parentheses for the common no-`as` case
--- with `as`, parentheses are STILL required (no ambiguity) ---
  binding form : caught TypeError
  when you bind the exception with `as`, you must keep the parentheses
  - `except A, B as e:` would be ambiguous, so it stays a tuple. the
  relaxation applies only to the unbound, comma-list case
--- the history: this exact syntax was the classic 2.x-to-3.x trap ---
  in Python 2, `except ValueError, e:` BOUND the error to e (that was
  how you named it), so `except ValueError, TypeError:` silently bound
  to a var called TypeError and did NOT catch TypeErrors. 3.0 made it
  a SyntaxError; 3.14 reclaims the spelling with the SAFE meaning
--- the constraint answered ---
  catching several types needed tuple parentheses, and the
  parenthesis-free version was a historical footgun turned
  SyntaxError. PEP 758 (3.14) makes `except A, B:` (no `as`) mean
  'catch either', so the natural spelling reads naturally. with `as`,
  parentheses remain required to keep it unambiguous
```

## Why each part answers the constraint

**The bare list catches any listed type.**
The first block shows `except ValueError, TypeError:` catching both a `ValueError` and a `TypeError`, and a separate `except KeyError, IndexError:` catching those.
The comma-separated list reads as exactly what it does - "catch either one" - with no tuple parentheses required when there is no `as`.

**It is equivalent to the tuple form.**
The second block confirms the two spellings compile to the same handler: the parenthesized `except (ValueError, TypeError):` and the bare `except ValueError, TypeError:` both catch a `TypeError`, with identical behavior.
PEP 758 did not add new *semantics* - it removed the required parentheses for the common no-`as` case.

**`as` still needs parentheses.**
The third block shows the one place parentheses remain mandatory: when binding with `as`.
`except (ValueError, TypeError) as exc:` keeps its parentheses, because `except A, B as e:` would be grammatically ambiguous.
The relaxation applies only to the unbound, comma-list case - a deliberate, careful scoping that avoids reintroducing any ambiguity.

**The history it reclaims.**
The fourth block tells the story that makes this more than a cosmetic change.
The exact syntax `except ValueError, TypeError:` was the Python 2 trap - it bound to a variable named `TypeError` and silently failed to catch `TypeError`s.
Python 3.0 made it a `SyntaxError` to kill the trap; Python 3.14 *reclaims* the spelling with the *safe* meaning, now that `as` (not the comma) is how you bind.
The syntax that was once a footgun is now the natural, correct spelling - a small but satisfying resolution of a decades-old wart.

## The two-track note

Exception handling - how a handler matches types, how `as` binds, how `except*` (Chapter 21) matches exception groups - is Deep Volume B's to develop.
PEP 758 is a pure grammar relaxation on top of that unchanged machinery.
What the timeline records is the release act: in 3.14, `except A, B:` (without `as`) became legal, meaning "catch either."
The modern consequence, verified above, is that the parentheses are optional for the common multi-type catch, the natural spelling is finally allowed, and the historical trap is closed - the comma means "or," not "bind," because binding is `as`'s job now.

## Where this lands

This is a small ergonomic and historical-cleanup change.
Write `except ValueError, TypeError:` when catching multiple types without binding - it reads as the list it is.
Keep the parentheses when you bind with `as`: `except (ValueError, TypeError) as exc:`.
Remember the compatibility direction: this syntax requires 3.14+, so code supporting older Pythons must still use the parenthesized form everywhere.
Deep Volume B explains exception handling; this chapter is the record of the release that let the obvious spelling mean the obvious thing, forty years after the comma first misled people.
