# requires: 3.14+
"""Listing 290.1 - Python 3.14 (2025): uuid6/7/8, time-ordered UUIDs.

uuid4 (random) is the usual choice for a unique id, and it has a hidden database
cost: because the values are RANDOM, inserting them as a primary key scatters
writes all over the index's B-tree, fragmenting it and thrashing the cache. The
industry answer is a TIME-ORDERED uuid: put a timestamp in the high bits so new
ids sort AFTER old ones, and inserts append to the end of the index instead of
scattering. RFC 9562 standardized these as UUID versions 6, 7, and 8, and Python
3.14 added uuid.uuid6/7/8. uuid7 is the one to reach for: millisecond timestamp
plus randomness, monotonic, globally unique. Deep volumes own no id mechanism;
this is the release that put time-ordered UUIDs in the stdlib. This listing tests
ordering PROPERTIES, never the random values. Verified on 3.14 builds.
"""

import uuid


def main() -> None:
    print("--- uuid7 is a real UUID, version 7 ---")
    u = uuid.uuid7()
    print(f"  uuid7().version : {u.version}")
    print(f"  it is a uuid.UUID : {isinstance(u, uuid.UUID)}")
    print(f"  uuid6 and uuid8 also exist : "
          f"{hasattr(uuid, 'uuid6') and hasattr(uuid, 'uuid8')}")
    print("  3.14 added the RFC 9562 time-ordered versions: 6, 7, and 8. uuid7")
    print("  is the general-purpose one - a Unix-millisecond timestamp in the")
    print("  high bits, random in the low bits")

    print("--- uuid7 values sort in CREATION order (time-ordered) ---")
    made = [uuid.uuid7() for _ in range(10000)]
    print(f"  generated 10000 uuid7 in a row")
    print(f"  they are strictly increasing (monotonic) : "
          f"{all(made[i] < made[i + 1] for i in range(len(made) - 1))}")
    print(f"  sorting them yields the SAME order they were made : "
          f"{made == sorted(made)}")
    print("  because the timestamp leads the bits, later ids compare GREATER.")
    print("  Python's uuid7 also carries a monotonic counter, so even ids made")
    print("  in the same millisecond stay in order - strictly increasing")

    print("--- contrast: uuid4 is random, so it does NOT sort by creation time ---")
    made4 = [uuid.uuid4() for _ in range(1000)]
    print(f"  1000 uuid4 sorted == creation order : {made4 == sorted(made4)}")
    print("  uuid4's bits are random, so its sort order is unrelated to WHEN it")
    print("  was created. that randomness is exactly what scatters database")
    print("  inserts across the index - the cost uuid7 removes")

    print("--- why time-ordering matters: index-friendly inserts ---")
    print("  a database B-tree index on a random uuid4 primary key inserts into")
    print("  RANDOM positions, splitting pages all over and trashing cache")
    print("  locality. a uuid7 key always inserts at the END (newest), so pages")
    print("  fill sequentially - far less fragmentation, much better write")
    print("  throughput. that is why teams switched to time-ordered UUIDs")

    print("--- still globally unique, like any UUID ---")
    sample = {uuid.uuid7() for _ in range(10000)}
    print(f"  10000 uuid7 are all distinct : {len(sample) == 10000}")
    print("  time-ordering does NOT cost uniqueness: the random/counter bits keep")
    print("  collisions astronomically unlikely, so uuid7 is a drop-in unique id")
    print("  that ALSO sorts by time - the best of both")

    print("--- the constraint answered ---")
    print("  random uuid4 keys scatter database inserts and fragment indexes. the")
    print("  industry fix is time-ordered UUIDs - a timestamp in the high bits so")
    print("  ids sort by creation and inserts append. RFC 9562 standardized them")
    print("  and Python 3.14 added uuid6/7/8. uuid7 gives you a unique id that is")
    print("  also index-friendly - no third-party library needed")


if __name__ == "__main__":
    main()
