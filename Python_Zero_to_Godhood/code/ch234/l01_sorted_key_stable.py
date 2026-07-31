"""Listing 234.1 - Python 2.4 (2004): sorted(), key=, and guaranteed stable sort.

Pre-2.4 sorting meant list.sort() (in place only) steered by a cmp= function -
a two-argument comparator Python called O(n log n) times, once per comparison,
each call crossing into Python. 2.4 changed the model: a `sorted()` builtin
that returns a new list, and a `key=` function called exactly ONCE per element
to extract a sort key. Same result, far fewer Python-level calls. 2.4 also
GUARANTEED the sort is stable (equal elements keep their input order), which
turns 'sort by multiple criteria' into a sequence of simple sorts. Deep B owns
the comparison protocol; this is the release that made key-based, stable
sorting the model - the reason you almost never write a comparator in Python.
Verified on current interpreters.
"""


def main() -> None:
    print("--- sorted() returns a new list; sort() mutates in place ---")
    data = [3, 1, 4, 1, 5, 9, 2, 6]
    s = sorted(data)
    print(f"  sorted(data) -> {s}")
    print(f"  original unchanged : {data}")
    print("  sorted() is the expression form: it returns a NEW sorted list and")
    print("  leaves the input alone, so it works in a comprehension or argument.")
    print("  list.sort() still exists for in-place sorting of a list you own")

    print("--- key=: called ONCE per element, not once per comparison ---")
    words = ["banana", "Apple", "cherry", "Date"]
    by_lower = sorted(words, key=str.lower)
    print(f"  sorted(words, key=str.lower) -> {by_lower}")
    calls = []
    def keyfn(w):
        calls.append(w)
        return len(w)
    by_len = sorted(words, key=keyfn)
    print(f"  sorted by len -> {by_len}")
    print(f"  key called {len(calls)} times for {len(words)} elements (once each)")
    print("  the OLD cmp= comparator ran O(n log n) times, each a Python call;")
    print("  key= runs exactly n times to extract keys, then compares those in C.")
    print("  same order, far fewer Python-level calls - the performance reason")
    print("  key= replaced cmp= (which 3.0 removed entirely)")

    print("--- stability: equal keys keep their input order (guaranteed since 2.4) ---")
    people = [("Alice", 30), ("Bob", 25), ("Carol", 30), ("Dave", 25)]
    by_age = sorted(people, key=lambda p: p[1])
    print(f"  by age : {by_age}")
    print("  Alice before Carol (both 30), Bob before Dave (both 25) - equal")
    print("  keys stayed in INPUT order. 2.4 made this a guarantee, not luck,")
    print("  which is what makes the next trick correct")

    print("--- stability composes: multi-key sort by sorting LEAST-significant first ---")
    # Want: by age ascending, then name ascending within an age.
    step1 = sorted(people, key=lambda p: p[0])   # secondary key first (name)
    step2 = sorted(step1, key=lambda p: p[1])    # primary key last (age)
    print(f"  sort by name, then STABLE-sort by age -> {step2}")
    print("  because the age sort is stable, it preserves the name order within")
    print("  each age. so 'sort by A then B' = sort by B, then stable-sort by A.")
    print("  stability turns multi-criteria sorting into a pipeline of simple")
    print("  one-key sorts - no comparator, no compound key tuples needed")

    print("--- the modern one-liner: a tuple key does it in a single pass ---")
    one_pass = sorted(people, key=lambda p: (p[1], p[0]))  # (age, name)
    print(f"  key=lambda p: (p[1], p[0]) -> {one_pass}")
    print("  or extract a TUPLE key and let tuple ordering do the tiebreak in")
    print("  one pass. either way you describe the KEY, never a comparison -")
    print("  the model 2.4 established and Python has used ever since")

    print("--- the constraint answered ---")
    print("  pre-2.4 sorting was in-place and comparator-driven: O(n log n)")
    print("  Python calls per sort. 2.4 gave sorted() (a new list), key= (n")
    print("  calls, compared in C), and a stability guarantee (multi-key sorts")
    print("  compose). describe the key, not the comparison - that is why real")
    print("  Python almost never writes a cmp function")


if __name__ == "__main__":
    main()
