"""Listing 244.1 - Python 3.0 (2008): extended iterable unpacking, first, *rest = seq.

Python long allowed tuple unpacking: a, b, c = triple. But it required the
count to match EXACTLY, so 'take the first item and the rest' meant
first, rest = seq[0], seq[1:] - two indexings, and only if seq was sliceable.
Python 3.0's PEP 3132 added a starred target: first, *rest = seq binds first to
one item and rest to a LIST of everything else, in one assignment, from any
iterable. It handles head/tail, first/last, and middle-splitting cleanly, and
it works on iterators that cannot be sliced. Deep B owns the assignment and
unpacking model; this is the release that made 'destructure a sequence into
head and rest' a single, position-driven assignment. Verified on current
interpreters.
"""


def main() -> None:
    print("--- a starred target absorbs 'the rest' as a list ---")
    first, *rest = [10, 20, 30, 40]
    print(f"  first, *rest = [10,20,30,40] -> first={first}, rest={rest}")
    print("  first binds one item; *rest collects everything else into a LIST,")
    print("  in one assignment. the pre-3.0 form was first, rest = seq[0],")
    print("  seq[1:] - two indexings that only work on a sliceable sequence")

    print("--- the star can go anywhere: head, tail, or middle ---")
    *init, last = [1, 2, 3, 4]
    print(f"  *init, last  -> init={init}, last={last}")
    head, *mid, tail = [1, 2, 3, 4, 5]
    print(f"  head, *mid, tail -> head={head}, mid={mid}, tail={tail}")
    print("  the starred name takes as many items as are left after the fixed")
    print("  targets are filled from both ends. one assignment expresses")
    print("  first/last, drop-first, drop-last, and split-the-middle")

    print("--- it works on ANY iterable, including un-sliceable ones ---")
    gen = (x * x for x in range(5))              # a generator - has no [1:]
    first_sq, *other_sqs = gen
    print(f"  from a generator: first_sq={first_sq}, other_sqs={other_sqs}")
    print("  seq[1:] would fail on a generator (no slicing); starred unpacking")
    print("  just consumes the iterator. it is defined on ITERATION, not on")
    print("  indexing, so it covers cases the old slice idiom could not")

    print("--- the starred target is always a list, even when empty ---")
    only, *nothing = [99]
    print(f"  only, *nothing = [99] -> only={only}, nothing={nothing}")
    a, b, *rest2 = [1, 2]
    print(f"  a, b, *rest2 = [1,2] -> a={a}, b={b}, rest2={rest2}")
    print("  when there is nothing left, the starred name is an EMPTY list, not")
    print("  an error - so head/tail code does not need a length check first")

    print("--- a practical use: split a record into key and values ---")
    row = ["2024-01-15", "12.5", "13.1", "11.9", "12.8"]
    date, *readings = row
    numbers = [float(r) for r in readings]
    print(f"  date={date}, readings avg={sum(numbers) / len(numbers):.2f}")
    print("  'the first field is the label, the rest are data' is exactly")
    print("  date, *readings = row - the shape of parsing a CSV line, a command")
    print("  and its args, a header and its payload")

    print("--- the constraint answered ---")
    print("  tuple unpacking required an exact count, so head/rest meant manual")
    print("  slicing that only worked on sequences. starred targets (3.0) bind")
    print("  one part to a list of 'everything else' in a single assignment,")
    print("  from any iterable, with the star anywhere. destructuring a sequence")
    print("  into fixed and variable parts became one readable line")


if __name__ == "__main__":
    main()
