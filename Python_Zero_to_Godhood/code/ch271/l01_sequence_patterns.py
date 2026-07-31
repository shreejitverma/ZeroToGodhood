"""Listing 271.1 - Python 3.10 (2021): sequence patterns in match/case.

Building on the fundamentals (Chapter 270), sequence patterns match a value by
its STRUCTURE as a sequence: length, fixed elements, and a starred rest. This is
the tool for parsing token lists, command arguments, and structured records - the
'dispatch on how many parts, and pull them apart' logic that was nested len()
checks and index math before. A subtle, important rule: sequence patterns match
lists and tuples (any Sequence) but deliberately NOT str/bytes, so a string is
never accidentally torn into characters. Deep B owns matching; this chapter is
the sequence-pattern facet of the 3.10 release. Verified on current interpreters.
"""


def run(command):
    """Parse a command given as a list of tokens - classic sequence matching."""
    match command:
        case []:
            return "empty command"
        case ["quit"]:                           # exactly one element, the literal 'quit'
            return "quitting"
        case ["go", direction]:                  # two elements; bind the second
            return f"going {direction}"
        case ["move", x, y]:
            return f"moving to ({x}, {y})"
        case ["say", *words]:                    # 'say' then any number of words
            return f"saying: {' '.join(words)}"
        case [action, *rest]:
            return f"unknown action {action!r} with args {rest}"


def main() -> None:
    print("--- match by length and fixed elements ---")
    for cmd in [[], ["quit"], ["go", "north"], ["move", 3, 4]]:
        print(f"  run({cmd!r}) : {run(cmd)}")
    print("  each case fixes a LENGTH and some element values/positions. `case")
    print("  ['go', direction]` means 'a 2-element sequence starting with go',")
    print("  binding the second element - length and shape checked together")

    print("--- the starred pattern captures a variable-length REST ---")
    for cmd in [["say", "hello", "there"], ["say"], ["dance", "a", "b", "c"]]:
        print(f"  run({cmd!r}) : {run(cmd)}")
    print("  `['say', *words]` matches 'say' followed by ANY number of elements,")
    print("  binding them as a list. one starred name per pattern, exactly like")
    print("  the assignment unpacking of Chapter 244 - now inside match")

    print("--- fixed elements around a star: first, middle, last ---")
    def ends(seq):
        match seq:
            case [first, *_, last]:              # first and last, ignore the middle
                return f"first={first}, last={last}"
            case [only]:
                return f"single={only}"
            case []:
                return "empty"
    for s in [[1, 2, 3, 4], [9], []]:
        print(f"  ends({s}) : {ends(s)}")
    print("  the star can sit BETWEEN fixed patterns, so `[first, *_, last]`")
    print("  grabs the two ends and ignores the middle with *_ (a starred")
    print("  wildcard). structural, length-aware destructuring in one line")

    print("--- the crucial rule: strings and bytes do NOT match sequence patterns ---")
    def kind(value):
        match value:
            case [a, b]:
                return f"a 2-element sequence: {a}, {b}"
            case str():
                return "a string (NOT torn into characters)"
            case _:
                return "something else"
    print(f"  kind([1, 2]) : {kind([1, 2])}")
    print(f"  kind('ab')   : {kind('ab')}")
    print("  'ab' has two characters, but a sequence pattern does NOT match it -")
    print("  str and bytes are excluded on purpose, so you never accidentally")
    print("  destructure a string into characters. it falls to `case str()`")

    print("--- tuples and lists match the same patterns (any Sequence) ---")
    def point(p):
        match p:
            case [x, y]:                         # matches BOTH [x, y] and (x, y)
                return f"2D ({x}, {y})"
            case [x, y, z]:
                return f"3D ({x}, {y}, {z})"
    print(f"  point((1, 2))    : {point((1, 2))}")
    print(f"  point([1, 2, 3]) : {point([1, 2, 3])}")
    print("  the pattern `[x, y]` is about SEQUENCE STRUCTURE, not the literal")
    print("  bracket type - it matches a tuple or a list alike. write it with")
    print("  either brackets or parens; they mean the same in a pattern")

    print("--- the constraint answered ---")
    print("  dispatching on 'how many parts and what they are' meant nested")
    print("  len() checks and index math. sequence patterns (3.10) match a")
    print("  value's length and element structure and bind the parts - with a")
    print("  starred rest, mid-sequence stars, and a safety rule that str/bytes")
    print("  never match, so strings are not silently split")


if __name__ == "__main__":
    main()
