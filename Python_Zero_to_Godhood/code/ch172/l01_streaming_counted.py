"""Listing 172.1 - streaming, counted: the memory exponent, laziness, and the schedule.

Chapter 89 measured what a container costs per element. This chapter is about the
representation with no per-element cost at all, because it never holds the elements: a
generator produces values on demand and forgets each one as the next is requested.

Four facts, counted rather than timed (the timings are in bench_streaming.py):

  the memory exponent: a list's peak allocation grows with n, a generator's does not
  laziness: a pipeline over a billion potential items pulls exactly what the answer needs
  the price: one pass, no len(), and a silent nothing the second time
  the schedule: stages run item-at-a-time, so in-flight data is O(stages), not O(n)
"""

import itertools
import sys
import tracemalloc


def peak_allocation(run):
    """Peak bytes allocated while running, measured by tracemalloc."""
    tracemalloc.start()
    tracemalloc.reset_peak()
    run()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def main() -> None:
    N = 100_000

    print("--- the memory exponent, measured at two sizes ---")
    list_n = peak_allocation(lambda: sum([i * i for i in range(N)]))
    list_2n = peak_allocation(lambda: sum([i * i for i in range(2 * N)]))
    gen_n = peak_allocation(lambda: sum(i * i for i in range(N)))
    gen_2n = peak_allocation(lambda: sum(i * i for i in range(2 * N)))
    print(f"  sum over a LIST of squares      : peak grows {list_2n / list_n:.1f}x"
          f" when n doubles")
    print(f"  sum over a GENERATOR of squares : peak grows {gen_2n / gen_n:.1f}x"
          f" when n doubles")
    print(f"  generator peak is under 1% of the list's at n={N:,} : "
          f"{gen_n < list_n / 100}")
    print("  the list's memory is O(n); the generator's is O(1). streaming changes")
    print("  the MEMORY exponent, and no time optimisation in this volume does that")

    print("--- a generator's size does not depend on what it will yield ---")
    ten = (i for i in range(10))
    billion = (i for i in range(10**9))
    print(f"  getsizeof(generator over 10 items) == getsizeof(over 10**9) : "
          f"{sys.getsizeof(ten) == sys.getsizeof(billion)}")
    print("  the generator stores a frame and a position, never the data")

    print("--- laziness, counted at the source ---")
    pulled = 0

    def source(limit):
        nonlocal pulled
        for i in range(limit):
            pulled += 1
            yield i

    wanted = list(itertools.islice(
        (x for x in source(10**9) if x % 3 == 0), 5))
    print(f"  pipeline: source(10**9) -> keep multiples of 3 -> first 5")
    print(f"  result           : {wanted}")
    print(f"  items the source produced : {pulled}  (of 1,000,000,000 possible)")
    print("  demand flows backwards: nothing is computed until something downstream")
    print("  asks, so an early exit is a free optimisation over the whole pipeline")

    print("--- the price: one pass, then nothing, silently ---")
    squares = (i * i for i in range(5))
    first = list(squares)
    second = list(squares)
    print(f"  first pass  : {first}")
    print(f"  second pass : {second}   <- not an error")
    try:
        len(i for i in range(5))
    except TypeError as exc:
        print(f"  len(generator) : TypeError: {exc}")
    print("  a stream is a position, not a container: no len, no indexing, no")
    print("  second pass, and exhaustion is SILENT, which is a real bug class")

    print("--- the schedule: item at a time, not stage at a time ---")
    log = []

    def parse(items):
        for x in items:
            log.append(f"parse {x}")
            yield x

    def keep(items):
        for x in items:
            log.append(f"keep  {x}")
            yield x

    for _ in keep(parse(range(3))):
        pass
    print(f"  execution order : {', '.join(log)}")
    print("  each item runs the WHOLE pipeline before the next is produced, so the")
    print("  data in flight is one item per stage, however long the input")

    print("--- the rule ---")
    print("  size the state to the ANSWER, not the input: a reduction needs O(1),")
    print("  the top K needs O(K), and only a sort or a second pass needs the list")


if __name__ == "__main__":
    main()
