"""Listing 217.1 - Python 1.5 (1997): exceptions become classes, and gain a tree.

Early Python raised STRINGS as exceptions: `raise "file error"`. This worked
for signalling but not for SELECTING - you could not catch 'any I/O error'
without knowing every string, and two modules using the string 'error' were
indistinguishable. Python 1.5 (1997) made exceptions CLASSES, which gave them
a hierarchy: catch a base class and you catch all its subclasses. String
exceptions were deprecated and finally removed in Python 2.6/3.0. This listing
demonstrates the modern consequence - the exception TREE that class-based
exceptions made possible - on current interpreters, where selective handling
by hierarchy is so fundamental it is hard to imagine the string-era language.
"""


class TradingError(Exception):
    """A domain base class: catch this, catch every trading error."""


class InsufficientFunds(TradingError):
    pass


class MarketClosed(TradingError):
    pass


def main() -> None:
    print("--- the built-in exception tree is a hierarchy, by design ---")
    for exc in (ValueError, KeyError, FileNotFoundError, ZeroDivisionError):
        chain = []
        cls = exc
        while cls is not object:
            chain.append(cls.__name__)
            cls = cls.__bases__[0]
        print(f"  {exc.__name__:<18} : {' -> '.join(chain)}")
    print("  every exception is a class with a base-class chain up to")
    print("  BaseException - which is exactly what string exceptions could")
    print("  not have (a string has no superclass)")

    print("--- catch a base class, catch the whole subtree ---")
    for raise_it in (InsufficientFunds, MarketClosed):
        try:
            raise raise_it("boom")
        except TradingError as exc:              # one handler, both subclasses
            print(f"  raised {raise_it.__name__:<18} caught as TradingError"
                  f" : {type(exc).__name__}")
    print("  ONE except clause handles every trading error, because the")
    print("  handler names a BASE class. this is the selection string")
    print("  exceptions could not do: 'catch any error of THIS family'")

    print("--- LBYL vs EAFP: the tree enables 'ask forgiveness' ---")
    prices = {"ACME": 100}

    def get_lbyl(sym):                            # Look Before You Leap
        if sym in prices:
            return prices[sym]
        return None

    def get_eafp(sym):                            # Easier to Ask Forgiveness
        try:
            return prices[sym]
        except KeyError:
            return None
    print(f"  LBYL get('ACME')={get_lbyl('ACME')}, get('X')={get_lbyl('X')}")
    print(f"  EAFP get('ACME')={get_eafp('ACME')}, get('X')={get_eafp('X')}")
    print("  class-based exceptions made EAFP - try the operation, catch the")
    print("  specific failure - Python's idiomatic style, because you can")
    print("  catch EXACTLY the exception you expect and let others propagate")

    print("--- chaining: an exception carries its cause (Python 3.0+) ---")
    try:
        try:
            raise KeyError("ACME")
        except KeyError as exc:
            raise TradingError("lookup failed") from exc
    except TradingError as exc:
        print(f"  {type(exc).__name__} raised FROM {type(exc.__cause__).__name__}")
    print("  the tree grew richer over time: chaining (from), groups")
    print("  (except*, Chapter 104), notes - but the 1.5 decision to make")
    print("  exceptions classes is the root every later feature grew on")

    print("--- the constraint answered ---")
    print("  1.5 faced a real limit: string exceptions could signal but not")
    print("  be organised. classes gave a hierarchy, hierarchy gave selection,")
    print("  selection made EAFP idiomatic - one decision, a cascade of")
    print("  consequences that define how Python code handles failure today")


if __name__ == "__main__":
    main()
