"""Listing 8.2 - one Executor API, two interchangeable backends.

PEP 3148 (concurrent.futures, 3.2) replaced hand-managed threading.Thread and
multiprocessing.Process objects with one interface: an Executor with a
ThreadPoolExecutor and a ProcessPoolExecutor backend, and a Future carrying each
task's eventual result or exception. Because the API is identical across
backends, you choose threads vs processes by changing one class name: threads
for I/O-bound work (they overlap while blocked in C-level I/O that releases the
GIL), processes for CPU-bound work (separate interpreters, real parallelism).

The pool code sits under `if __name__ == "__main__"` because the spawn start
method (the macOS and Windows default) re-imports this module in each worker;
without the guard, that re-import would re-run the pool and recurse.
"""

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed


def io_task(n):          # mostly waiting -> threads overlap
    return n * n


def cpu_task(n):         # pure computation -> needs separate processes to parallelize
    return sum(i * i for i in range(n))


def main():
    print("--- ThreadPoolExecutor: submit returns a Future; as_completed yields them ---")
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(io_task, i) for i in range(5)]
        results = sorted(f.result() for f in as_completed(futures))
    print("  thread pool results:", results)

    print()
    print("--- ProcessPoolExecutor: same API, separate interpreters ---")
    with ProcessPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(cpu_task, [1000, 2000, 3000]))
    print("  process pool results:", results)

    print()
    print("A Future carries a result OR an exception; .result() re-raises in the")
    print("caller. Arguments and results cross the process boundary via pickle")
    print("through an OS pipe, which is why a process pool loses to serial code")
    print("on tiny tasks: the transfer dominates. Pool coarse-grained work.")


if __name__ == "__main__":
    main()
