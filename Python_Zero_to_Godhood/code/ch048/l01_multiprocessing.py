"""Listing 48.1 - multiprocessing: real parallelism, paid for by pickling.

A process Pool runs work on several CPU cores at once, sidestepping the GIL
(Chapter 8) because each worker is a separate interpreter. But there is no shared
memory by default: arguments are PICKLED (Chapter 42) in the parent, shipped
through a pipe, and unpickled in the worker, and results make the return trip.
So multiprocessing buys parallel CPU at the cost of serializing every argument
and result. This listing shows Pool.map and the pickle requirement; the
benchmark shows when the IPC cost erases the parallelism win.

Must be guarded by if __name__ == '__main__' (the spawn/fork requirement).
"""

import multiprocessing as mp


def square(x):
    return x * x


def main() -> None:
    print("--- Pool.map: distribute work across worker processes ---")
    with mp.Pool(processes=4) as pool:
        results = pool.map(square, [1, 2, 3, 4, 5, 6])   # order preserved
    print(f"  pool.map(square, 1..6) : {results}")

    print("--- arguments and results cross the boundary by pickling ---")
    # A lambda is not picklable, so it cannot be sent to a worker. (The exact
    # exception type varies by version/start-method; that a lambda fails does not.)
    import pickle
    try:
        pickle.dumps(lambda x: x + 1)
        picklable = True
    except Exception:
        picklable = False
    print(f"  is a lambda picklable? : {picklable} (so it cannot be sent to a worker)")

    print("--- each worker is a separate interpreter (its own PID, not the parent's) ---")
    with mp.Pool(processes=2) as pool:
        worker_pid = pool.apply(_worker_pid, (0,))
    print(f"  worker PID != parent   : {worker_pid != _worker_pid(0)} (work ran in another process)")
    print(f"  parent is MainProcess  : {mp.current_process().name == 'MainProcess'}")


def _worker_pid(_):
    import os
    return os.getpid()


if __name__ == "__main__":
    main()
