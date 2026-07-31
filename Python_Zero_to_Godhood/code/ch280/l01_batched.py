"""Listing 280.1 - Python 3.12 (2023): itertools.batched, chunk an iterable into fixed-size groups.

'Process this in batches of N' is a constant need: insert 500 rows per query,
send 100 items per API call, paginate output. The correct lazy implementation is
fiddly - a while loop pulling islice(it, n) until empty - and the naive
list-slicing version (lst[i:i+n]) only works on sequences and materialises the
whole input. People re-wrote a 'chunk' or 'grouper' helper in every project.
Python 3.12 added itertools.batched: it lazily yields tuples of up to N items
from ANY iterable, with a short final batch for the remainder. Chapter 91 owns
the streaming cost model; this is the release that made batching a standard,
lazy, one-call tool. Verified on current interpreters.
"""

from itertools import batched


def main() -> None:
    print("--- batched(iterable, n) yields tuples of up to n items ---")
    data = [1, 2, 3, 4, 5, 6, 7]
    batches = list(batched(data, 3))
    print(f"  list(batched([1..7], 3)) : {batches}")
    print("  seven items in groups of three: two full batches, then a short")
    print("  final batch (7,) with the remainder. no dropped items, no padding -")
    print("  the last batch is just smaller")

    print("--- it works on ANY iterable, lazily - not just sequences ---")
    def count_up():
        n = 0
        while True:                              # an infinite generator
            n += 1
            yield n
    import itertools
    first_batches = list(itertools.islice(batched(count_up(), 4), 3))
    print(f"  first 3 batches of an INFINITE generator : {first_batches}")
    print("  batched consumes an ITERATOR, so it batches infinite or streaming")
    print("  sources in constant memory - it holds one batch at a time, never")
    print("  the whole input (Chapter 91). list-slicing could not do this")

    print("--- the classic use: process fixed-size chunks ---")
    records = list(range(1, 24))                  # 23 records
    query_count = 0
    for chunk in batched(records, 10):            # insert 10 per query
        query_count += 1
        print(f"    query {query_count}: {len(chunk)} rows {chunk[0]}..{chunk[-1]}")
    print(f"  23 records in batches of 10 took {query_count} queries")
    print("  this is the batching a database inserter or API client needs: N per")
    print("  request, one short request at the end. exactly the loop everyone")
    print("  used to hand-write with islice or manual index math")

    print("--- each batch is a tuple; the total item count is preserved ---")
    src = "abcdefgh"
    grouped = list(batched(src, 3))
    print(f"  batched('abcdefgh', 3) : {grouped}")
    total = sum(len(b) for b in grouped)
    print(f"  every element appears exactly once : {total == len(src)}")
    print("  batches are TUPLES (immutable, cheap), and concatenating them")
    print("  reconstructs the input - batching partitions, it never drops or")
    print("  duplicates")

    print("--- an empty input yields no batches; n must be at least 1 ---")
    print(f"  list(batched([], 5)) : {list(batched([], 5))}   (nothing in, nothing out)")
    try:
        list(batched([1, 2], 0))                  # n=0 is invalid
    except ValueError as exc:
        print(f"  batched(x, 0) -> ValueError: {exc}")
    print("  no items means no batches (not one empty batch), and a batch size")
    print("  below 1 is rejected - the sensible, unsurprising edge behaviour")

    print("--- the constraint answered ---")
    print("  chunking into fixed-size groups was a hand-written islice loop or a")
    print("  sequence-only slicing helper re-implemented everywhere. batched")
    print("  (3.12) makes it one lazy call over any iterable: tuples of N with a")
    print("  short final group, constant memory, no items lost. 'in batches of N'")
    print("  became a standard-library primitive")


if __name__ == "__main__":
    main()
