"""Listing 166.1 - the five ways a microbenchmark measures nothing, made checkable.

A benchmark that produces a number is not a benchmark that produced a measurement. Each
failure below yields a confident, reproducible, meaningless figure, and each one is
detectable BEFORE you trust it, by asking what work actually ran.

  1  the clock's resolution is coarser than the thing being timed
  2  the expression was evaluated by the COMPILER, so nothing ran at all
  3  the expression was LAZY, so nothing ran until something consumed it
  4  the operation cached its own result, so run 2..n measured a dict lookup
  5  the input was already in the state the operation produces, so the fast path ran

None of these needs statistics to detect. Each is a question about what executed, and
this listing answers each by counting or by inspecting the code object, which is
deterministic and therefore identical on both verification interpreters.
"""

import functools
import gc
import time
import timeit


def compiled_away():
    return 2 ** 10                      # folded to 1024 at compile time


def not_folded(base, power):
    return base ** power                # a real computation


CALLS = []


def counted(value):
    CALLS.append(value)
    return value * 2


@functools.lru_cache(maxsize=None)
def cached_work(n):
    CALLS.append(n)
    return sum(range(n))


def gc_state_during_timing():
    """timeit disables the cyclic collector while timing; record what the body sees."""
    observed = []
    timeit.Timer(lambda: observed.append(gc.isenabled())).timeit(number=1)
    return observed[0], gc.isenabled()


def comparisons_to_sort(data):
    """How many comparisons list.sort() actually performs on this input."""
    count = 0

    class Counting(int):
        def __lt__(self, other):
            nonlocal count
            count += 1
            return int(self) < int(other)

    items = [Counting(x) for x in data]
    items.sort()
    return count


def main() -> None:
    info = time.get_clock_info("perf_counter")

    print("--- 1. the clock is coarser than most single operations ---")
    print(f"  timeit's default timer is perf_counter : {timeit.default_timer is time.perf_counter}")
    print(f"  its resolution                         : {info.resolution * 1e9:.1f} ns")
    print(f"  it is monotonic                        : {info.monotonic}")
    print(f"  so timing ONE 3 ns operation is noise  : {info.resolution * 1e9 > 3}")
    print("  the fix is batching: time N operations and divide, never time one")

    print("--- 2. the compiler may have evaluated it already ---")
    print(f"  1024 is a constant of compiled_away    : {1024 in compiled_away.__code__.co_consts}")
    print(f"  not_folded has no such constant        : {1024 not in not_folded.__code__.co_consts}")
    print("  timing `2 ** 10` measures LOAD_CONST, not exponentiation")

    print("--- 3. a lazy object does no work until consumed ---")
    CALLS.clear()
    lazy = map(counted, range(5))
    print(f"  calls after building map(...)          : {len(CALLS)}")
    consumed = list(lazy)
    print(f"  calls after list(...)                  : {len(CALLS)}")
    print(f"  the result, for the record             : {consumed}")

    print("--- 4. an operation that caches measures its cache after the first run ---")
    CALLS.clear()
    cached_work.cache_clear()
    for _ in range(100):
        cached_work(500)
    print(f"  bodies executed for 100 calls          : {len(CALLS)}")
    info_ = cached_work.cache_info()
    print(f"  hits / misses                          : {info_.hits} / {info_.misses}")
    print("  a loop of 100 timed calls measured 1 computation and 99 dict lookups")

    print("--- 5. the input's state decides which path runs ---")
    ascending = list(range(64))
    shuffled = [(i * 37) % 64 for i in range(64)]
    print(f"  comparisons to sort already-sorted     : {comparisons_to_sort(ascending)}")
    print(f"  comparisons to sort shuffled           : {comparisons_to_sort(shuffled)}")
    print("  Timsort detects the run and returns early; benchmark the input you have")

    print("--- and one thing timeit does FOR you, which is also a distortion ---")
    inside, after = gc_state_during_timing()
    print(f"  cyclic collector enabled inside timeit : {inside}")
    print(f"  and restored afterwards                : {after}")
    print("  so timed code never pays for a collection your production code will")

    print("--- the rule ---")
    print("  before trusting a number, ask what executed: count the calls, read the")
    print("  code object, consume the iterator, clear the cache, and vary the input")


if __name__ == "__main__":
    main()
