"""Listing 129.1 - concurrent.futures: the high-level, unified pool API.

concurrent.futures is the recommended way to use pools: one API over both threads
(ThreadPoolExecutor, for IO-bound work, Chapter 46) and processes
(ProcessPoolExecutor, for CPU-bound work, Chapter 47). Its central abstraction is the
FUTURE, a handle to a result that is not ready yet:
  - executor.submit(fn, *args) returns a Future immediately; Future.result() blocks
    until the value is ready (and RE-RAISES any exception the worker raised).
  - executor.map(fn, iterable) runs fn over the inputs and yields results IN ORDER.
  - as_completed(futures) yields each Future as it FINISHES (out of submission order),
    so you can process results as soon as they are ready.
This listing shows each, on a ThreadPoolExecutor. Swapping to ProcessPoolExecutor
changes nothing but the import, that is the point of the unified API.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed


def work(x):
    return x * x


def boom():
    raise ValueError("worker failed")


def main() -> None:
    with ThreadPoolExecutor(max_workers=3) as ex:
        print("--- submit returns a Future; result() gives the value ---")
        future = ex.submit(work, 7)
        value = future.result()                  # blocks until ready
        print(f"  ex.submit(work, 7).result() : {value}")
        print(f"  future.done() after result  : {future.done()}")

        print("--- map runs over inputs and returns results IN ORDER ---")
        print(f"  list(ex.map(work, [1,2,3,4])) : {list(ex.map(work, [1, 2, 3, 4]))}")

        print("--- as_completed yields futures as they finish (order not guaranteed) ---")
        futures = [ex.submit(work, i) for i in range(5)]
        collected = sorted(f.result() for f in as_completed(futures))
        print(f"  all results via as_completed (sorted) : {collected}")

    print("--- an exception in a worker RE-RAISES at result() ---")
    with ThreadPoolExecutor() as ex:
        f = ex.submit(boom)
        try:
            f.result()
        except ValueError as e:
            print(f"  worker exception surfaced at result() : {e}")

    print("--- the rule ---")
    print(f"  submit -> Future -> result(); map for ordered results; as_completed")
    print(f"  for results-as-ready; same API for ThreadPool (IO) and ProcessPool (CPU)")


if __name__ == "__main__":
    main()
