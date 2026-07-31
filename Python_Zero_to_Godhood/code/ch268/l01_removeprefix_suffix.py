"""Listing 268.1 - Python 3.9 (2020): str.removeprefix/removesuffix, exact affix stripping.

Everyone reaches for s.strip('...') / s.lstrip / s.rstrip to remove a leading or
trailing PIECE of a string - and it is a trap, because those methods take a SET
OF CHARACTERS, not a substring. 'test.py'.rstrip('.py') does not remove the
suffix '.py'; it strips any trailing '.', 'p', or 'y' characters, so it eats the
final 't' too and returns 'tes'. This is a real, common, data-corrupting bug.
Python 3.9's PEP 616 added removeprefix and removesuffix: they remove exactly the
given string if it is present, and return the string unchanged otherwise.
Deep D owns strings; this is the release that gave 'strip this exact prefix/
suffix' a correct, unambiguous method. Verified on current interpreters.
"""


def main() -> None:
    print("--- the trap: rstrip takes a CHARACTER SET, not a suffix ---")
    filename = "happy.py"
    print(f"  'happy.py'.rstrip('.py')      : {filename.rstrip('.py')!r}   <- WRONG")
    print(f"  'happy.py'.removesuffix('.py'): {filename.removesuffix('.py')!r}   <- right")
    print("  rstrip('.py') strips any trailing '.', 'p', or 'y' - it keeps eating")
    print("  characters as long as they are in the set {'.', 'p', 'y'}, so it")
    print("  removes '.py' and then 'ypp' from 'happy', leaving just 'ha'. it")
    print("  treats '.py' as a SET of chars, not the string - a data-corruption bug")

    print("--- removeprefix/removesuffix remove the EXACT string, once ---")
    print(f"  'unhappy'.removeprefix('un')   : {'unhappy'.removeprefix('un')!r}")
    print(f"  'report.csv'.removesuffix('.csv') : "
          f"{'report.csv'.removesuffix('.csv')!r}")
    print("  they match the whole given string as a unit and remove it a single")
    print("  time from the correct end - no character-set semantics, no")
    print("  surprise over-stripping")

    print("--- if the affix is absent, the string is returned UNCHANGED ---")
    print(f"  'data.json'.removesuffix('.py') : "
          f"{'data.json'.removesuffix('.py')!r}   (no '.py' -> unchanged)")
    print(f"  'happy'.removeprefix('un')      : {'happy'.removeprefix('un')!r}   (no 'un' -> unchanged)")
    print("  when the prefix/suffix is not there, you get the original back -")
    print("  no error, no partial removal. safe to call unconditionally")

    print("--- it removes only ONE occurrence, not repeated ones ---")
    print(f"  'xxbody'.removeprefix('x')  : {'xxbody'.removeprefix('x')!r}   (one x)")
    print(f"  'aaa'.removesuffix('a')     : {'aaa'.removesuffix('a')!r}   (one a)")
    print("  unlike strip(), which greedily removes ALL matching leading/trailing")
    print("  chars, removeprefix/removesuffix take off exactly one copy of the")
    print("  given string - predictable, not greedy")

    print("--- the empty-affix and whole-string edge cases ---")
    print(f"  'abc'.removeprefix('')   : {'abc'.removeprefix('')!r}   (empty -> unchanged)")
    print(f"  'abc'.removesuffix('abc'): {'abc'.removesuffix('abc')!r}   (whole -> '')")
    print("  removing an empty affix changes nothing; removing the whole string")
    print("  leaves the empty string. both are the intuitive results, with no")
    print("  special-casing needed at call sites")

    print("--- the correct idiom vs the old workaround ---")
    url = "https://example.com"
    old = url[len("https://"):] if url.startswith("https://") else url
    new = url.removeprefix("https://")
    print(f"  old: startswith-check + slice : {old!r}")
    print(f"  new: removeprefix              : {new!r}   (same, one call)")
    print("  the safe pre-3.9 way was `s[len(p):] if s.startswith(p) else s` -")
    print("  correct but verbose and easy to get the length wrong. removeprefix")
    print("  is that idiom as one clear, correct method")

    print("--- the constraint answered ---")
    print("  strip/lstrip/rstrip take a character SET, so using them to remove a")
    print("  prefix or suffix STRING silently over-strips - a real bug")
    print("  ('happy.py'.rstrip('.py') -> 'ha'). removeprefix/removesuffix (3.9) remove exactly")
    print("  the given string once, or leave the input unchanged. 'strip this")
    print("  exact affix' finally has a method that means what it says")


if __name__ == "__main__":
    main()
