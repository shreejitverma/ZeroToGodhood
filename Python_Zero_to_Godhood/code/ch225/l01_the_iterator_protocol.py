"""Listing 225.1 - Python 2.2 (2001): the iterator protocol, and what 'for' became.

Before 2.2, `for x in obj` worked by calling obj[0], obj[1], ... until
IndexError - it required INTEGER INDEXING. Python 2.2 introduced the ITERATOR
PROTOCOL: `for` calls iter(obj) to get an iterator, then next() repeatedly
until StopIteration. This decoupled iteration from indexing, so ANYTHING that
defines __iter__/__next__ can be looped over - dicts, sets, files, generators,
infinite sequences, database cursors. It is the single abstraction behind for,
comprehensions, unpacking, *args, and the whole 'iterable' vocabulary. Deep F
owns the mechanism; this is the release that made 'for' universal. Verified on
current interpreters.
"""


class CountdownIterator:
    """A hand-built iterator: __iter__ returns self, __next__ yields or stops."""

    def __init__(self, start):
        self.n = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.n <= 0:
            raise StopIteration                  # the signal 'for' catches
        self.n -= 1
        return self.n + 1


def main() -> None:
    print("--- for works on anything with the protocol, no indexing needed ---")
    print(f"  a hand-built iterator : {list(CountdownIterator(3))}")
    print("  for called iter() then next() until StopIteration - it never")
    print("  indexed anything. this is the decoupling 2.2 introduced: iteration")
    print("  no longer requires obj[0], obj[1], ... (which needed integer keys)")

    print("--- the protocol is two methods, and that is the whole abstraction ---")
    it = iter([10, 20, 30])
    print(f"  iter(list) gives an iterator : {type(it).__name__}")
    print(f"  next(it) : {next(it)}, next(it) : {next(it)}, next(it) : {next(it)}")
    try:
        next(it)
    except StopIteration:
        print(f"  next(it) past the end raises : StopIteration")
    print("  __iter__ gives an iterator; __next__ advances or raises")
    print("  StopIteration. every loop in Python is these two calls in a")
    print("  hidden while-loop (Deep F owns the machinery)")

    print("--- one protocol, every 'iterable' - built-ins included ---")
    print(f"  a dict iterates its keys   : {list(iter({'a': 1, 'b': 2}))}")
    print(f"  a set iterates its members : {sorted(iter({3, 1, 2}))}")
    print(f"  a str iterates its chars   : {list(iter('hi'))}")
    print(f"  range is lazily iterable   : {list(iter(range(3)))}")
    print("  none of these support integer indexing the old for-loop needed")
    print("  (a set has no order to index, a dict indexes by KEY) - yet all")
    print("  loop, because they define the protocol. that is its power")

    print("--- the protocol powers far more than for-loops ---")
    a, b, c = CountdownIterator(3)                # unpacking uses the protocol
    print(f"  unpacking a, b, c = iterator : {a}, {b}, {c}")
    print(f"  comprehension over iterator  : "
          f"{[x * 10 for x in CountdownIterator(3)]}")
    print(f"  sum/max/any over iterable    : "
          f"sum={sum(CountdownIterator(4))}, max={max(CountdownIterator(4))}")
    print("  for, unpacking, comprehensions, *args, sum/max/any/sorted - ALL")
    print("  consume the iterator protocol. define __iter__/__next__ once and")
    print("  your object works with the entire iteration vocabulary")

    print("--- the constraint answered ---")
    print("  pre-2.2 iteration required integer indexing, which excluded dicts,")
    print("  sets, files, and lazy/infinite sequences. the iterator protocol")
    print("  decoupled 'looping' from 'indexing', making 'for' work on any")
    print("  iterable - the abstraction generators (also 2.2) and the whole")
    print("  lazy-evaluation story (Chapter 91, Deep F) are built on")


if __name__ == "__main__":
    main()
