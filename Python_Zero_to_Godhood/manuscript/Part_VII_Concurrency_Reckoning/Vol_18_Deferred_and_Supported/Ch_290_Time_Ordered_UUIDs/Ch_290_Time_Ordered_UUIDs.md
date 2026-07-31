# Chapter 290: Time-Ordered UUIDs

## The constraint

`uuid4` - a random 128-bit identifier - is the reflexive choice for a unique id, and it has a hidden cost that shows up at scale, in the database.

When you use a random UUID as a primary key, every new row's key lands in a *random* position in the index's B-tree.
Inserts scatter across the whole index, splitting pages everywhere, fragmenting the structure, and thrashing the cache (the page you need next is rarely the page you just touched).
For a high-insert-rate table, this is a real and measurable throughput problem - random primary keys are one of the classic database anti-patterns.

The industry answer, arrived at independently many times, is a *time-ordered* UUID: put a timestamp in the high bits so that newer ids sort *after* older ones.
Then inserts always append to the *end* of the index - pages fill sequentially, fragmentation drops, and cache locality is restored.
This idea was standardized as UUID versions 6, 7, and 8 in RFC 9562, and third-party libraries offered it for years.

The constraint Python 3.14 (2025) answered: **put time-ordered UUIDs in the standard library**, so the index-friendly id needs no third-party package.

This chapter owns no Deep-Volume mechanism; UUID generation is a standard-library capability.
What it owns is the release: the day time-ordered UUIDs arrived in `uuid`.

## What shipped

Python 3.14 added `uuid.uuid6`, `uuid.uuid7`, and `uuid.uuid8`.
`uuid7` is the general-purpose one - a Unix-millisecond timestamp in the high bits plus randomness (and a monotonic counter) in the low bits - so its values sort in creation order while remaining globally unique.
Listing 290.1 shows the ordering properties on the 3.14 builds (gated to 3.14+), testing properties rather than the random values.

Verified output (CPython 3.14.6):

```text
--- uuid7 is a real UUID, version 7 ---
  uuid7().version : 7
  it is a uuid.UUID : True
  uuid6 and uuid8 also exist : True
  3.14 added the RFC 9562 time-ordered versions: 6, 7, and 8. uuid7
  is the general-purpose one - a Unix-millisecond timestamp in the
  high bits, random in the low bits
--- uuid7 values sort in CREATION order (time-ordered) ---
  generated 10000 uuid7 in a row
  they are strictly increasing (monotonic) : True
  sorting them yields the SAME order they were made : True
  because the timestamp leads the bits, later ids compare GREATER.
  Python's uuid7 also carries a monotonic counter, so even ids made
  in the same millisecond stay in order - strictly increasing
--- contrast: uuid4 is random, so it does NOT sort by creation time ---
  1000 uuid4 sorted == creation order : False
  uuid4's bits are random, so its sort order is unrelated to WHEN it
  was created. that randomness is exactly what scatters database
  inserts across the index - the cost uuid7 removes
--- why time-ordering matters: index-friendly inserts ---
  a database B-tree index on a random uuid4 primary key inserts into
  RANDOM positions, splitting pages all over and trashing cache
  locality. a uuid7 key always inserts at the END (newest), so pages
  fill sequentially - far less fragmentation, much better write
  throughput. that is why teams switched to time-ordered UUIDs
--- still globally unique, like any UUID ---
  10000 uuid7 are all distinct : True
  time-ordering does NOT cost uniqueness: the random/counter bits keep
  collisions astronomically unlikely, so uuid7 is a drop-in unique id
  that ALSO sorts by time - the best of both
--- the constraint answered ---
  random uuid4 keys scatter database inserts and fragment indexes. the
  industry fix is time-ordered UUIDs - a timestamp in the high bits so
  ids sort by creation and inserts append. RFC 9562 standardized them
  and Python 3.14 added uuid6/7/8. uuid7 gives you a unique id that is
  also index-friendly - no third-party library needed
```

## Why each part answers the constraint

**A real UUID, version 7.**
The first block confirms `uuid7()` is a `uuid.UUID` reporting version 7, and that `uuid6` and `uuid8` also exist.
These are the RFC 9562 time-ordered versions; `uuid7` is the general-purpose choice, with a Unix-millisecond timestamp in the high bits and randomness in the low bits.

**They sort by creation order.**
The second block is the defining property: 10,000 `uuid7` generated in a row are *strictly increasing*, and sorting them yields the same order they were created.
Because the timestamp leads the bits, a later id compares greater than an earlier one.
And crucially, Python's `uuid7` carries a monotonic counter, so even ids created within the same millisecond stay in order - the values are strictly increasing, not merely increasing across time gaps.

**uuid4 does not.**
The third block draws the contrast: 1,000 `uuid4` sorted do *not* match their creation order, because their bits are random.
That randomness is exactly what scatters database inserts across the index - the cost `uuid7` was designed to remove.

**Why it matters.**
The fourth block explains the database consequence.
A B-tree index on a random `uuid4` primary key inserts into random positions, splitting pages all over and trashing cache locality.
A `uuid7` key always inserts at the *end* (it is the newest), so pages fill sequentially - far less fragmentation and much better write throughput.
This is a concrete, measurable win, and it is why teams switched to time-ordered UUIDs at scale.

**Still unique.**
The fifth block confirms the property you cannot give up: 10,000 `uuid7` are all distinct.
Time-ordering does not cost uniqueness - the random and counter bits keep collisions astronomically unlikely - so `uuid7` is a drop-in unique id that *also* sorts by time.
You get both properties, where `uuid4` gave you only uniqueness.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; time-ordered UUID generation is a standard-library implementation of RFC 9562.
What the timeline records is the release act: in 3.14, `uuid.uuid6`/`uuid7`/`uuid8` brought time-ordered UUIDs into the standard library.
The modern consequence, verified above, is that the index-friendly identifier the industry adopted is now built in, so choosing `uuid7` over `uuid4` for a database key is a one-line change with no dependency - and it fixes a performance problem that random keys quietly cause.

## Where this lands

Time-ordered UUIDs are a targeted addition with a clear "when to use" story.
Reach for `uuid7` whenever a UUID will be used as a database primary key, a sort key, or anywhere insert locality or time-ordering matters - it gives you uniqueness *and* creation-order sorting, fixing the random-key fragmentation problem.
Keep `uuid4` when you specifically want *unpredictability* (an id that reveals nothing about when it was made, for security or privacy) - time-ordered UUIDs deliberately leak their creation time.
The compatibility direction applies: these require 3.14+, so older Pythons still need a third-party library.
No Deep Volume owns an id mechanism; this chapter is the record of the release that put time-ordered UUIDs in the standard library.
