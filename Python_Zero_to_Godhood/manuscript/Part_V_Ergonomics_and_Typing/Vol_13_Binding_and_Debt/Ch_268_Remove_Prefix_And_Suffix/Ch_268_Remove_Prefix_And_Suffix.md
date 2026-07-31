# Chapter 268: Remove Prefix and Suffix

## The constraint

Removing a known prefix or suffix from a string is one of the most ordinary text operations there is: strip `https://` from a URL, drop the `.py` from a filename, remove an `un` prefix.
And for Python's entire history before 3.9, the method programmers reached for to do it - `strip`, `lstrip`, `rstrip` - was the *wrong tool*, in a way that silently corrupted data.

The trap is that `strip`/`lstrip`/`rstrip` take a **set of characters**, not a substring.
`"happy.py".rstrip(".py")` does not remove the suffix `".py"`.
It removes every trailing character that is a member of the set `{'.', 'p', 'y'}`, and it keeps going as long as it finds one.
Starting from the right of `"happy.py"`: it strips `y`, `p`, `.`, then `y`, `p`, `p`, and stops at `a` - leaving `"ha"`.
The programmer wanted `"happy"` and got `"ha"`.

This is not a contrived edge case; it is a real, common, data-corrupting bug that appeared throughout Python code, because the method name (`rstrip`) reads like "strip from the right" and the character-set semantics are not obvious from the call.
The safe workaround existed - `s[len(p):] if s.startswith(p) else s` - but it was verbose, easy to get the length wrong, and rarely the first thing people wrote.

The constraint Python 3.9 (2020, PEP 616) answered: **give "remove this exact prefix/suffix string" a correct, unambiguous method**, so the common operation stops being a trap.

This is a two-track chapter.
Strings themselves are Deep Volume D's subject.
What this chapter owns is the release: the day exact affix removal got a method that means what it says.

## What shipped

`str.removeprefix(p)` and `str.removesuffix(s)` remove exactly the given string, once, if it is present at the correct end, and return the string unchanged otherwise.
Listing 268.1 shows the trap and the fix on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- the trap: rstrip takes a CHARACTER SET, not a suffix ---
  'happy.py'.rstrip('.py')      : 'ha'   <- WRONG
  'happy.py'.removesuffix('.py'): 'happy'   <- right
  rstrip('.py') strips any trailing '.', 'p', or 'y' - it keeps eating
  characters as long as they are in the set {'.', 'p', 'y'}, so it
  removes '.py' and then 'ypp' from 'happy', leaving just 'ha'. it
  treats '.py' as a SET of chars, not the string - a data-corruption bug
--- removeprefix/removesuffix remove the EXACT string, once ---
  'unhappy'.removeprefix('un')   : 'happy'
  'report.csv'.removesuffix('.csv') : 'report'
  they match the whole given string as a unit and remove it a single
  time from the correct end - no character-set semantics, no
  surprise over-stripping
--- if the affix is absent, the string is returned UNCHANGED ---
  'data.json'.removesuffix('.py') : 'data.json'   (no '.py' -> unchanged)
  'happy'.removeprefix('un')      : 'happy'   (no 'un' -> unchanged)
  when the prefix/suffix is not there, you get the original back -
  no error, no partial removal. safe to call unconditionally
--- it removes only ONE occurrence, not repeated ones ---
  'xxbody'.removeprefix('x')  : 'xbody'   (one x)
  'aaa'.removesuffix('a')     : 'aa'   (one a)
  unlike strip(), which greedily removes ALL matching leading/trailing
  chars, removeprefix/removesuffix take off exactly one copy of the
  given string - predictable, not greedy
--- the empty-affix and whole-string edge cases ---
  'abc'.removeprefix('')   : 'abc'   (empty -> unchanged)
  'abc'.removesuffix('abc'): ''   (whole -> '')
  removing an empty affix changes nothing; removing the whole string
  leaves the empty string. both are the intuitive results, with no
  special-casing needed at call sites
--- the correct idiom vs the old workaround ---
  old: startswith-check + slice : 'example.com'
  new: removeprefix              : 'example.com'   (same, one call)
  the safe pre-3.9 way was `s[len(p):] if s.startswith(p) else s` -
  correct but verbose and easy to get the length wrong. removeprefix
  is that idiom as one clear, correct method
--- the constraint answered ---
  strip/lstrip/rstrip take a character SET, so using them to remove a
  prefix or suffix STRING silently over-strips - a real bug
  ('happy.py'.rstrip('.py') -> 'ha'). removeprefix/removesuffix (3.9) remove exactly
  the given string once, or leave the input unchanged. 'strip this
  exact affix' finally has a method that means what it says
```

## Why each part answers the constraint

**The trap, demonstrated.**
The first block shows the corruption directly: `"happy.py".rstrip(".py")` returns `"ha"`, because `rstrip` treats `".py"` as the character set `{'.', 'p', 'y'}` and keeps eating trailing characters in that set - through the `.py`, and on into `ypp` of `happy`.
`removesuffix(".py")` returns the correct `"happy"`.
The two methods, which look interchangeable, produce wildly different results, and only one is what anyone wanted.

**Exact, single removal.**
The second block shows the correct behavior: `removeprefix` and `removesuffix` match the *whole given string as a unit* and remove it once from the correct end.
`"unhappy".removeprefix("un")` is `"happy"`; `"report.csv".removesuffix(".csv")` is `"report"`.
No character-set semantics, no over-stripping.

**Absent affix leaves the string unchanged.**
The third block shows the safe default: if the prefix or suffix is not present, the original string comes back untouched - no error, no partial removal.
This makes the methods safe to call unconditionally, without a `startswith`/`endswith` guard.

**Exactly one occurrence, not greedy.**
The fourth block highlights a deliberate contrast with `strip`: `"xxbody".removeprefix("x")` removes just one `x` (giving `"xbody"`), and `"aaa".removesuffix("a")` removes one `a` (giving `"aa"`).
Where `strip` greedily removes *all* matching leading/trailing characters, `removeprefix`/`removesuffix` take off exactly one copy of the given string - predictable, not greedy.

**Intuitive edge cases.**
The fifth block confirms the corner cases behave sensibly: removing an empty affix changes nothing, and removing the whole string leaves the empty string.
Both are the results you would expect, requiring no special-casing at call sites.

**The idiom it replaces.**
The sixth block shows the old safe workaround, `s[len(p):] if s.startswith(p) else s`, producing the same result as `removeprefix` - correct but verbose, and prone to a length mistake.
`removeprefix` is that idiom distilled into one clear, correct method call.

## The two-track note

Strings and their methods are Deep Volume D's subject; `removeprefix`/`removesuffix` are a small, targeted addition to that vocabulary.
What the timeline records is the release act: in 3.9, PEP 616 added exact-affix removal, closing the `rstrip`-as-suffix-remover trap.
The modern consequence, verified above, is that stripping a known prefix or suffix has a method that does exactly that - and the `strip` family is recognized as being for character-set trimming (whitespace, punctuation), never for removing a known substring.

## Where this lands

`removeprefix` and `removesuffix` fixed one of the more insidious everyday string bugs in Python.
Reach for them any time you want to remove a *known string* from the start or end of another - filenames, URLs, prefixes, protocol markers.
Reserve `strip`/`lstrip`/`rstrip` for what they are actually for: trimming a *set of characters* (whitespace, quotes, punctuation) from the ends.
The rule of thumb: if the argument is a substring you want gone, use `removeprefix`/`removesuffix`; if it is a set of characters to trim, use `strip`.
Deep Volume D covers strings in depth; this chapter is the record of the release that gave exact affix removal a method that means what it says.
