# requires: 3.14+
"""Listing 288.1 - Python 3.14 (2025): PEP 758, except without parentheses.

To catch several exception types in one handler you wrote `except (ValueError,
TypeError):` - the parentheses making a tuple. Forget them and you got a subtle,
notorious trap in older Python: `except ValueError, TypeError:` was 2.x syntax
that BOUND the exception to a variable named TypeError, silently NOT catching
TypeErrors. 3.x turned it into a SyntaxError, which was safer but still a papercut.
Python 3.14's PEP 758 finally allows the parenthesis-free form when there is no
`as` binding: `except ValueError, TypeError:` now means 'catch either', reading
like the natural list it is. Deep B owns exception handling; this is the release
that let the obvious spelling mean the obvious thing. Verified on 3.14 builds.
"""


def classify(raiser):
    try:
        raiser()
    except ValueError, TypeError:                # no parentheses, catches either
        return "caught ValueError or TypeError"
    except KeyError, IndexError:
        return "caught KeyError or IndexError"


def main() -> None:
    print("--- except without parentheses catches any of the listed types ---")
    print(f"  a ValueError : {classify(lambda: (_ for _ in ()).throw(ValueError()))}")
    print(f"  a TypeError  : {classify(lambda: (_ for _ in ()).throw(TypeError()))}")
    print(f"  a KeyError   : {classify(lambda: (_ for _ in ()).throw(KeyError()))}")
    print("  `except ValueError, TypeError:` now means 'catch either one' -")
    print("  reading as the plain comma-separated list it looks like. no tuple")
    print("  parentheses required when you are not binding with `as`")

    print("--- it is exactly equivalent to the parenthesised tuple form ---")
    def with_parens(raiser):
        try:
            raiser()
        except (ValueError, TypeError):          # the classic form
            return "caught"
    def without_parens(raiser):
        try:
            raiser()
        except ValueError, TypeError:            # the new 3.14 form
            return "caught"
    boom = lambda: (_ for _ in ()).throw(TypeError())
    print(f"  parenthesised form catches TypeError  : {with_parens(boom)!r}")
    print(f"  bare-list form catches TypeError       : {without_parens(boom)!r}")
    print(f"  same behaviour : {with_parens(boom) == without_parens(boom)}")
    print("  the two spellings compile to the same handler. PEP 758 just removed")
    print("  the required parentheses for the common no-`as` case")

    print("--- with `as`, parentheses are STILL required (no ambiguity) ---")
    def bound(raiser):
        try:
            raiser()
        except (ValueError, TypeError) as exc:   # `as` -> parens still needed
            return f"caught {type(exc).__name__}"
    print(f"  binding form : {bound(boom)}")
    print("  when you bind the exception with `as`, you must keep the parentheses")
    print("  - `except A, B as e:` would be ambiguous, so it stays a tuple. the")
    print("  relaxation applies only to the unbound, comma-list case")

    print("--- the history: this exact syntax was the classic 2.x-to-3.x trap ---")
    print("  in Python 2, `except ValueError, e:` BOUND the error to e (that was")
    print("  how you named it), so `except ValueError, TypeError:` silently bound")
    print("  to a var called TypeError and did NOT catch TypeErrors. 3.0 made it")
    print("  a SyntaxError; 3.14 reclaims the spelling with the SAFE meaning")

    print("--- the constraint answered ---")
    print("  catching several types needed tuple parentheses, and the")
    print("  parenthesis-free version was a historical footgun turned")
    print("  SyntaxError. PEP 758 (3.14) makes `except A, B:` (no `as`) mean")
    print("  'catch either', so the natural spelling reads naturally. with `as`,")
    print("  parentheses remain required to keep it unambiguous")


if __name__ == "__main__":
    main()
