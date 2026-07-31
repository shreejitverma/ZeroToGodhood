"""Listing 248.1 - Python 3.2 (2011): concurrent.futures, a high-level concurrency API.

Running work in parallel used to mean managing threads or processes by hand:
create them, hand each a queue, start them, join them, collect results, handle
exceptions crossing the boundary. It was low-level and error-prone. Python 3.2's
concurrent.futures (PEP 3148) raised the abstraction: an Executor is a pool you
SUBMIT callables to; each submit() returns a Future - a handle to a result that
is not ready yet; and executor.map() runs a function over an iterable across the
pool, returning results IN INPUT ORDER. Swapping ThreadPoolExecutor for
ProcessPoolExecutor changes threads to processes with no other code change.
Deep E owns the GIL, threads, and processes - WHEN each pool actually speeds
things up; this is the release that gave concurrency one clean, uniform API.
This listing uses threads and ordered map() so its output is deterministic.
Verified on current interpreters.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed


def square(n):
    return n * n


def main() -> None:
    print("--- an Executor is a pool you submit work to ---")
    with ThreadPoolExecutor(max_workers=4) as pool:
        future = pool.submit(square, 9)          # returns immediately
        print(f"  pool.submit(square, 9) returned a : {type(future).__name__}")
        print(f"  future.result() blocks for the answer : {future.result()}")
    print("  submit() schedules the call and hands back a Future - a handle to")
    print("  a result that may not exist yet. result() waits for it. you never")
    print("  created, started, or joined a thread by hand")

    print("--- map() runs a function over an iterable, results IN INPUT ORDER ---")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(square, range(8)))
    print(f"  pool.map(square, range(8)) : {results}")
    print("  map() distributes the calls across the pool but returns results in")
    print("  the ORDER of the inputs, not the order they finished - so the")
    print("  output is deterministic even though the work ran concurrently")

    print("--- Futures carry exceptions across the boundary ---")
    def boom(x):
        raise ValueError(f"cannot process {x}")
    with ThreadPoolExecutor(max_workers=2) as pool:
        f = pool.submit(boom, 42)
        try:
            f.result()                           # re-raises in the caller
        except ValueError as exc:
            print(f"  future.result() re-raised : ValueError({exc})")
    print("  an exception in a worker is captured by its Future and RE-RAISED")
    print("  when you call result(). errors cross the concurrency boundary")
    print("  cleanly instead of vanishing in a background thread")

    print("--- as_completed: react to results as they arrive (order sorted here) ---")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(square, n) for n in range(5)]
        done = [f.result() for f in as_completed(futures)]
    print(f"  results via as_completed, then sorted : {sorted(done)}")
    print("  as_completed() yields futures the moment each finishes - ideal for")
    print("  streaming results. completion order is nondeterministic, so we")
    print("  sort here purely to keep this listing's output stable")

    print("--- the uniformity: threads or processes, same code ---")
    print("  ThreadPoolExecutor and ProcessPoolExecutor share this API. swap")
    print("  the class and the SAME submit/map/Future code runs on processes")
    print("  instead of threads - the choice of pool is one line, not a rewrite")
    print("  (WHICH to pick, and why, is the GIL question Deep E answers)")

    print("--- the constraint answered ---")
    print("  hand-managing threads and processes - create, start, join, collect,")
    print("  marshal errors - was low-level and fragile. concurrent.futures")
    print("  (3.2) gave one high-level API: an Executor pool, submit() returning")
    print("  a Future, map() for ordered results, uniform across threads and")
    print("  processes. Deep E tells you which pool helps; this made USING one easy")


if __name__ == "__main__":
    main()
