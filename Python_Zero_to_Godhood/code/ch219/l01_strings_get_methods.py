"""Listing 219.1 - Python 1.6 (2000): string operations become methods.

Early Python put string operations in a MODULE: string.upper(s),
string.split(s, sep), string.join(words, sep). You imported `string` and
called functions on your string. Python 1.6 (2000) made them METHODS on the
str type: s.upper(), s.split(sep), sep.join(words). This is 'everything is an
object' (Chapter 4) applied to strings - an operation on a string belongs ON
the string - and it is why modern Python string code reads the way it does.
The string module's functions were deprecated and the common ones removed by
Python 3. This listing shows the method form and the object-oriented reading
it created, verified on current interpreters.
"""


def main() -> None:
    print("--- string operations are methods on the str object ---")
    s = "  Trade: ACME buy 100  "
    print(f"  s.strip()          : {s.strip()!r}")
    print(f"  s.upper()          : {s.upper()!r}")
    print(f"  s.split()          : {s.split()!r}")
    print(f"  s.replace('buy','sell') : {s.replace('buy', 'sell').strip()!r}")
    print("  the operation lives ON the string (s.upper()), not in a separate")
    print("  module (string.upper(s)) - which is Chapter 4's decision applied:")
    print("  an operation on an object belongs on the object")

    print("--- join is a method on the SEPARATOR, which surprises newcomers ---")
    words = ["ACME", "buy", "100"]
    print(f"  ','.join(words)  : {','.join(words)!r}")
    print(f"  ' '.join(words)  : {' '.join(words)!r}")
    print("  join is s.join(iterable), a method on the SEPARATOR - because")
    print("  the separator is the string that knows how to stitch, and the")
    print("  argument can be any iterable of strings (Chapter 74's efficient")
    print("  accumulation, not repeated +)")

    print("--- methods chain, which the module form could not do cleanly ---")
    raw = "  ACME , buy , 100  "
    fields = [f.strip() for f in raw.strip().split(",")]
    print(f"  raw.strip().split(',') then strip each : {fields}")
    chained = "ACME-BUY-100".lower().replace("-", " ").title()
    print(f"  chained: lower().replace().title()     : {chained!r}")
    print("  s.strip().split().title() reads left-to-right as a pipeline;")
    print("  string.title(string.split(string.strip(s))) reads inside-out.")
    print("  the method form made string processing a readable chain")

    print("--- the str type is where the operations belong ---")
    print(f"  str has {sum(1 for m in dir(str) if not m.startswith('_'))}"
          f" public methods")
    print(f"  a few: {[m for m in dir(str) if not m.startswith('_')][:6]}")
    print("  putting them on str (not in a module) means autocomplete finds")
    print("  them, they document themselves as the type's interface, and new")
    print("  string types (Chapter 4: str is subclassable) inherit them")

    print("--- the constraint answered ---")
    print("  1.6 faced a mismatch: string operations lived in a module while")
    print("  'everything is an object' (Chapter 4) said they belonged on the")
    print("  string. moving them to methods fixed the mismatch, enabled")
    print("  chaining, and made string code read as operations on a value -")
    print("  a small change with a large effect on how Python is written")


if __name__ == "__main__":
    main()
