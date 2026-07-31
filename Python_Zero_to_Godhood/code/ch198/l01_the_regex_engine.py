"""Listing 198.1 - the regex engine: compiled programs, backtracking, and verbs.

Deep P opens with the stdlib's most-used little language. Three facts anchor
everything about `re`: a pattern is COMPILED to a program (an object you can
hold, inspect, and reuse); the engine EXECUTES that program by backtracking,
which is provable from CAPTURED GROUPS alone (greedy quantifiers consume too
much and give back; the groups show exactly where the engine settled); and
the module's verbs (match/search/fullmatch/findall/finditer/sub) are distinct
questions, not synonyms.

Chapter 82 owns the pathological blowup (ReDoS); this chapter owns the
engine's ordinary behaviour. What backtracking COSTS is the benchmark's job -
a first draft here tried to count character probes through a str subclass,
and the C engine, which reads the underlying buffer directly, ignored it:
instruments must touch the layer they claim to measure.
"""

import re


def main() -> None:
    print("--- a pattern is a compiled program ---")
    program = re.compile(r"(?P<key>\w+)=(?P<value>\d+)")
    print(f"  type(re.compile(...)) : {type(program).__name__}")
    print(f"  groups declared       : {program.groups}, "
          f"named {sorted(program.groupindex)}")
    match = program.search("retries=3; timeout=45")
    print(f"  first match           : {match.group(0)!r} at {match.span()}")
    print(f"  by name               : key={match['key']!r}, "
          f"value={match['value']!r}")
    print("  compile once, hold the object: the module-level functions do this")
    print("  through a cache, but the OBJECT is the honest interface - a")
    print("  pattern is a program, and programs are values")

    print("--- backtracking, proven by where the groups settled ---")
    give_back = re.fullmatch(r"(a+)(ab)", "aaab")
    print(f"  (a+)(ab)  on 'aaab'   -> groups {give_back.groups()}")
    print("  a+ grabbed 'aaa', hit the wall, GAVE BACK one 'a' so (ab) could")
    print("  match: the retry is invisible in the result except right here")
    greedy = re.fullmatch(r"(.*)(\d+)", "build4711")
    lazy = re.fullmatch(r"(.*?)(\d+)", "build4711")
    print(f"  (.*)(\\d+)  greedy     -> groups {greedy.groups()}")
    print(f"  (.*?)(\\d+) lazy       -> groups {lazy.groups()}")
    print("  greedy .* swallowed the digits and surrendered ONE, leaving '1';")
    print("  lazy .*? stopped at the first digit, leaving '4711'. neither is")
    print("  wrong and neither is free: each settlement is a trail of retries,")
    print("  and the pathological trails are Chapter 82's subject")

    print("--- alternation order is semantics, not style ---")
    print(f"  (cat|category) on 'category:9' -> "
          f"{re.match(r'(cat|category)', 'category:9').group(1)!r}")
    print(f"  (category|cat) on 'category:9' -> "
          f"{re.match(r'(category|cat)', 'category:9').group(1)!r}")
    print("  the engine tries alternatives LEFT TO RIGHT and keeps the first")
    print("  success at each position - longest-match is not the rule here")
    print("  (unlike POSIX tools), so order alternations longest-first")

    print("--- the verbs are different questions ---")
    text = "a=1, b=22, c=333"
    program = re.compile(r"(\w)=(\d+)")
    is_pair = re.compile(r"\w=\d+")
    print(f"  fullmatch 'a=1'   : {bool(is_pair.fullmatch('a=1'))}"
          f"    'a=1,' : {bool(is_pair.fullmatch('a=1,'))}")
    print(f"  findall           : {program.findall(text)}")
    print(f"  finditer spans    : "
          f"{[m.span() for m in program.finditer(text)]}")
    print(f"  sub with function : "
          f"{program.sub(lambda m: m[1] + ':' + m[2][::-1], text)!r}")
    print("  match/search/fullmatch answer WHERE (fullmatch is validation: the")
    print("  whole string or nothing); findall/finditer answer WHAT (finditer")
    print("  streams Match objects, Chapter 91's shape); sub answers INSTEAD.")
    print("  choosing the verb is half of regex clarity")


if __name__ == "__main__":
    main()
