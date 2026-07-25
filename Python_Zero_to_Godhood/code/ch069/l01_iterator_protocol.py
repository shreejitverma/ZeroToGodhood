"""Listing 69.1 - the iterator protocol: iterable vs iterator, and generators.

Two roles, often confused. An ITERABLE can produce an iterator (it has __iter__);
iter() called on it returns a FRESH iterator each time. An ITERATOR produces
values on demand (it has __next__, raising StopIteration when done) and is its own
iterable (its __iter__ returns self). Consequences: an iterable (list) can be
looped many times; an iterator is SINGLE-USE (once exhausted, it yields nothing).
A generator function is the idiomatic, and fast, way to write an iterator: the
generator machinery implements __iter__/__next__ for you in C. This listing shows
the protocol and the equivalence.
"""


class CountIter:
    """A hand-written iterator: __iter__ returns self, __next__ yields values."""

    def __init__(self, n):
        self.i = 0
        self.n = n

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= self.n:
            raise StopIteration
        value = self.i
        self.i += 1
        return value


def count_gen(n):
    """The same iterator as a generator function (yields the same sequence)."""
    i = 0
    while i < n:
        yield i
        i += 1


def main() -> None:
    print("--- iterable vs iterator ---")
    lst = [10, 20, 30]
    it = iter(lst)
    print(f"  iter(list) is a NEW iterator (not the list) : {iter(lst) is not lst}")
    print(f"  an iterator's __iter__ returns itself       : {iter(it) is it}")

    print("--- an iterator is single-use; an iterable is not ---")
    print(f"  list looped twice : {list(lst)} {list(lst)}")
    print(f"  iterator drained  : {list(it)} {list(it)}  (second pass is empty)")

    print("--- next() drives the protocol; StopIteration ends it ---")
    g = count_gen(2)
    print(f"  next(g): {next(g)}  next(g): {next(g)}")
    try:
        next(g)
        ended = False
    except StopIteration:
        ended = True
    print(f"  next past the end raises StopIteration : {ended}")

    print("--- a generator IS an iterator with the same output as the class ---")
    print(f"  class output : {list(CountIter(5))}")
    print(f"  gen output   : {list(count_gen(5))}")
    print(f"  identical    : {list(CountIter(5)) == list(count_gen(5))}")


if __name__ == "__main__":
    main()
