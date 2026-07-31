"""Listing 256.1 - Python 3.4 (2014): tracemalloc, seeing where memory actually goes.

'Why is this process using so much memory?' used to be nearly unanswerable from
inside Python. You could see the total from the OS, but not WHICH lines of Python
allocated it. Python 3.4's PEP 454 added tracemalloc: it hooks the interpreter's
allocator and records, per allocation, the Python traceback that made it - so you
can take a snapshot, run some code, take another, and see exactly which lines
grew memory and by how much. It is the measurement tool behind any real Python
memory investigation. Deep K owns the cost model and the discipline of measuring
before optimising; this is the release that made the measurement possible. To
stay deterministic across machines this listing reports only DIRECTIONS and
FLAGS (memory rose, peak >= current), never raw byte counts. Verified on current
interpreters.
"""

import tracemalloc


def main() -> None:
    print("--- tracemalloc hooks the allocator; you can ask if it is tracing ---")
    print(f"  before start, is_tracing() : {tracemalloc.is_tracing()}")
    tracemalloc.start()
    print(f"  after start,  is_tracing() : {tracemalloc.is_tracing()}")
    print("  start() begins recording the Python traceback behind every")
    print("  allocation. it is off by default (it has overhead) and turned on")
    print("  for the duration of an investigation")

    print("--- allocate memory and watch the traced total rise ---")
    before, _ = tracemalloc.get_traced_memory()
    data = [object() for _ in range(100_000)]     # a real allocation
    after, peak = tracemalloc.get_traced_memory()
    print(f"  current memory rose after allocating 100k objects : {after > before}")
    print(f"  peak >= current (peak tracks the high-water mark)  : {peak >= after}")
    print("  get_traced_memory() returns (current, peak) in bytes. we report")
    print("  only the DIRECTION here so the demo is machine-independent, but in")
    print("  practice you read the actual numbers to size the problem")

    print("--- a snapshot attributes memory to the LINES that allocated it ---")
    snapshot = tracemalloc.take_snapshot()
    stats = snapshot.statistics("lineno")
    print(f"  snapshot has per-line statistics : {len(stats) > 0}")
    top = stats[0]
    print(f"  the top entry is a real code location : "
          f"{top.traceback[0].filename.endswith('.py')}")
    print(f"  the top entry accounts for some bytes : {top.size > 0}")
    print("  each statistic ties a byte count to a file and line, so 'what is")
    print("  using memory' becomes a ranked list of code locations - the answer")
    print("  that was impossible to get before")

    print("--- comparing two snapshots isolates what a block of code allocated ---")
    snap1 = tracemalloc.take_snapshot()
    more = [bytearray(1000) for _ in range(1000)]  # allocate between snapshots
    snap2 = tracemalloc.take_snapshot()
    diff = snap2.compare_to(snap1, "lineno")
    grew = [d for d in diff if d.size_diff > 0]
    print(f"  compare_to() found lines that GREW between snapshots : {len(grew) > 0}")
    print("  the diff shows size_diff per line - exactly what the code BETWEEN")
    print("  the two snapshots allocated. this is how you localise a leak: snap,")
    print("  run the suspect code, snap, and read what grew")

    print("--- stop() when done: tracing has overhead ---")
    del data, more
    tracemalloc.stop()
    print(f"  after stop(), is_tracing() : {tracemalloc.is_tracing()}")
    print("  tracing every allocation costs time and memory, so you stop it once")
    print("  the investigation is over - it is a diagnostic tool, not something")
    print("  you leave on in production")

    print("--- the constraint answered ---")
    print("  'which Python lines are using the memory?' had no answer from")
    print("  inside the language. tracemalloc (3.4) records the traceback behind")
    print("  each allocation, so snapshots and their diffs attribute bytes to")
    print("  exact code locations. Deep K says measure before optimising; this")
    print("  release made memory measurable from inside Python")


if __name__ == "__main__":
    main()
