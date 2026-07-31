# Chapter 280: Batched

## The constraint

"Process this in batches of N" is one of the most common shapes in real code.
Insert 500 rows per database query instead of 500 separate queries.
Send 100 items per API call because the endpoint has a page limit.
Paginate output into screens of 20.
The need is everywhere, and the standard library had no primitive for it, so everyone re-wrote the same helper.

The two hand-rolled approaches both had problems.
The naive one used sequence slicing - `data[i:i+n]` in a loop - which only works on sequences (not generators or streams) and requires the *entire* input to be materialized in memory first.
The correct lazy one used a `while` loop pulling `itertools.islice(it, n)` until it came up empty, which is fiddly to write correctly (getting the termination condition right is easy to botch) and appeared, slightly differently, as a `chunk` or `grouper` helper in project after project.

The constraint Python 3.12 (2023) answered: **make batching a standard, lazy, one-call tool** that works on any iterable.

This is a two-track chapter.
The streaming cost model - why lazy, constant-memory processing matters - is Chapter 91's.
What this chapter owns is the release: the day chunking became a standard-library primitive.

## What shipped

`itertools.batched(iterable, n)` lazily yields tuples of up to `n` items from any iterable, with a short final tuple for the remainder.
Listing 280.1 shows it on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- batched(iterable, n) yields tuples of up to n items ---
  list(batched([1..7], 3)) : [(1, 2, 3), (4, 5, 6), (7,)]
  seven items in groups of three: two full batches, then a short
  final batch (7,) with the remainder. no dropped items, no padding -
  the last batch is just smaller
--- it works on ANY iterable, lazily - not just sequences ---
  first 3 batches of an INFINITE generator : [(1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12)]
  batched consumes an ITERATOR, so it batches infinite or streaming
  sources in constant memory - it holds one batch at a time, never
  the whole input (Chapter 91). list-slicing could not do this
--- the classic use: process fixed-size chunks ---
    query 1: 10 rows 1..10
    query 2: 10 rows 11..20
    query 3: 3 rows 21..23
  23 records in batches of 10 took 3 queries
  this is the batching a database inserter or API client needs: N per
  request, one short request at the end. exactly the loop everyone
  used to hand-write with islice or manual index math
--- each batch is a tuple; the total item count is preserved ---
  batched('abcdefgh', 3) : [('a', 'b', 'c'), ('d', 'e', 'f'), ('g', 'h')]
  every element appears exactly once : True
  batches are TUPLES (immutable, cheap), and concatenating them
  reconstructs the input - batching partitions, it never drops or
  duplicates
--- an empty input yields no batches; n must be at least 1 ---
  list(batched([], 5)) : []   (nothing in, nothing out)
  batched(x, 0) -> ValueError: n must be at least one
  no items means no batches (not one empty batch), and a batch size
  below 1 is rejected - the sensible, unsurprising edge behaviour
--- the constraint answered ---
  chunking into fixed-size groups was a hand-written islice loop or a
  sequence-only slicing helper re-implemented everywhere. batched
  (3.12) makes it one lazy call over any iterable: tuples of N with a
  short final group, constant memory, no items lost. 'in batches of N'
  became a standard-library primitive
```

## Why each part answers the constraint

**Tuples of up to n, with a short final batch.**
The first block shows the core behavior: `batched([1..7], 3)` yields `(1, 2, 3)`, `(4, 5, 6)`, and `(7,)` - two full batches and a short final one holding the remainder.
No items are dropped and nothing is padded; the last batch is simply smaller.
This is the correct, unsurprising semantics for chunking, and it comes for free.

**Lazy over any iterable.**
The second block shows the property that the slicing approach could never offer: `batched` consumes an *iterator*, so it batches an *infinite* generator in constant memory, holding one batch at a time and never the whole input.
This is the streaming discipline of Chapter 91 - you can batch a file, a network stream, or an unbounded sequence, processing each batch and discarding it, with a memory footprint of one batch regardless of the input's size.

**The canonical use.**
The third block shows the real-world pattern: 23 records processed in batches of 10 take exactly 3 queries - two full batches of 10 and a final batch of 3.
This is precisely the loop a database inserter or API client needs: N items per request, one short request at the end.
It replaces the `islice` loop or manual index math that everyone used to hand-write, and gets the final-batch edge case right by construction.

**Partitioning, not dropping.**
The fourth block confirms the correctness invariant: batches are tuples, and concatenating them reconstructs the input - every element appears exactly once.
`batched` *partitions* the input; it never drops or duplicates.
The tuple type is a deliberate choice: immutable and cheap, appropriate for a batch you will iterate and discard.

**Sensible edge cases.**
The fifth block shows the boundaries: an empty input yields *no* batches (not one empty batch), and a batch size below 1 raises `ValueError`.
Both are the unsurprising behaviors, requiring no special handling at call sites.

## The two-track note

The streaming cost model - why processing an iterable lazily in constant memory matters, and when it is worth the batching overhead - is Chapter 91's to develop, and `batched` is a clean instance of it.
What the timeline records is the release act: in 3.12, `itertools.batched` added fixed-size chunking to the standard library's iterator toolkit.
The modern consequence, verified above, is that "process in batches of N" is a one-call, lazy, correct primitive, and the hand-rolled `chunk`/`grouper` helpers that populated every codebase are no longer needed.

## Where this lands

`batched` is a small, exact addition that captured a genuinely universal pattern and got its edge cases right.
Reach for it whenever you process an iterable in fixed-size groups - bulk database operations, paginated API calls, chunked I/O, screen-at-a-time output - and rely on its laziness to keep memory constant even for large or infinite sources.
Take the short final batch as given; it is the correct handling of a remainder, not something to guard against.
Chapter 91 explains the streaming cost model; this chapter is the record of the release that made batching a standard-library primitive.
