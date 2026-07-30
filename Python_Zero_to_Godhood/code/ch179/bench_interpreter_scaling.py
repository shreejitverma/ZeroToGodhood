# requires: 3.14+
"""Benchmark 179.1 - the other escape, priced: scaling, startup, and crossing.

179.1a  the volume's headline table completed: the same CPU-bound work, four
        ways, on whichever build runs this. On the GIL build, subinterpreters
        (and processes) deliver the parallelism threads cannot; on the
        free-threaded build, threads deliver it cheapest and subinterpreters
        keep pace. Executors are pre-warmed so the rows price steady-state
        execution, not pool construction.

179.1b  startup: what one worker costs to bring up and retire, thread vs
        subinterpreter vs process. This is the number that decides pool
        design: an interpreter is tens of threads' worth of startup, a
        process is several interpreters' worth.

179.1c  crossing: what moving one value over the isolation boundary costs,
        via concurrent.interpreters.Queue, for a shareable int, a shareable
        1 KB bytes, and a pickled 100-element list, against queue.Queue as
        the same-interpreter baseline. Isolation's price is per value
        crossed, which is why Chapter 84's rule (cross per batch, never per
        element) reappears here with interpreters instead of C.

Run under 3.14 and 3.14t (skipped on 3.13, which lacks PEP 734).
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import queue as thread_queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

N = 2_000_000


def work(n=N):
    total = 0
    for i in range(n):
        total += i * i
    return total


def main():
    import concurrent.interpreters as interpreters
    from concurrent.futures import (InterpreterPoolExecutor,
                                    ProcessPoolExecutor, ThreadPoolExecutor)

    thread_pool = ThreadPoolExecutor(4)
    interp_pool = InterpreterPoolExecutor(4)
    process_pool = ProcessPoolExecutor(4)
    for pool in (thread_pool, interp_pool, process_pool):
        list(pool.map(work, [1000] * 4))          # warm: build workers, import

    scaling_env = {
        "work": work, "N": N,
        "thread_pool": thread_pool, "interp_pool": interp_pool,
        "process_pool": process_pool,
    }
    import __main__
    for k, v in scaling_env.items():
        setattr(__main__, f"_bench_{k}", v)

    SETUP = "import __main__ as m"
    rows = [
        measure("one call", "m._bench_work()", SETUP, repeat=5, number=1),
        measure("4 calls, sequential",
                "[m._bench_work() for _ in range(4)]", SETUP, repeat=5, number=1),
        measure("4 calls, thread pool",
                "list(m._bench_thread_pool.map(m._bench_work, [m._bench_N]*4))",
                SETUP, repeat=5, number=1),
        measure("4 calls, interpreter pool",
                "list(m._bench_interp_pool.map(m._bench_work, [m._bench_N]*4))",
                SETUP, repeat=5, number=1),
        measure("4 calls, process pool",
                "list(m._bench_process_pool.map(m._bench_work, [m._bench_N]*4))",
                SETUP, repeat=5, number=1),
    ]
    report("179.1a  the same CPU-bound work, four ways (pools pre-warmed)",
           rows, baseline="4 calls, sequential")
    thread_pool.shutdown()
    interp_pool.shutdown()
    process_pool.shutdown()

    print()
    print("=== 179.1b  bring up one worker and retire it ===")

    def startup(label, fn, repeat=10):
        best = min(_timed(fn) for _ in range(repeat))
        print(f"  {label:<28} {best * 1000:8.2f} ms")

    def _timed(fn):
        t0 = time.perf_counter()
        fn()
        return time.perf_counter() - t0

    def one_thread():
        t = threading.Thread(target=lambda: None)
        t.start()
        t.join()

    def one_interpreter():
        interp = interpreters.create()
        interp.exec("pass")
        interp.close()

    def one_process():
        with ProcessPoolExecutor(1) as ex:
            ex.submit(int).result()

    startup("thread, start+join", one_thread)
    startup("subinterpreter, create+close", one_interpreter)
    startup("process pool of 1, up+down", one_process, repeat=3)

    print()
    print("=== 179.1c  one value across the boundary, put+get ===")
    iq = interpreters.create_queue()
    tq = thread_queue.Queue()
    payloads = (
        ("int (shareable)", 12345),
        ("1 KB bytes (shareable)", b"x" * 1024),
        ("100-elem list (pickled)", list(range(100))),
    )

    def roundtrip(q, value, count=10_000):
        t0 = time.perf_counter()
        for _ in range(count):
            q.put(value)
            q.get()
        return (time.perf_counter() - t0) / count * 1e9

    for label, value in payloads:
        via_interp = min(roundtrip(iq, value) for _ in range(3))
        via_thread = min(roundtrip(tq, value) for _ in range(3))
        print(f"  {label:<24} interpreters.Queue {via_interp:8.0f} ns"
              f"   queue.Queue {via_thread:6.0f} ns"
              f"   x{via_interp / via_thread:5.1f}")

    print()
    print("Reading this. On the GIL build, the thread-pool row ties sequential")
    print("and the interpreter and process rows divide by the core count: PEP")
    print("684's per-interpreter GIL delivers CPU parallelism on the build")
    print("everyone already runs. On the free-threaded build the thread row")
    print("joins them and wins, sharing memory and skipping the boundary.")
    print()
    print("The startup and crossing tables are isolation's invoice: an")
    print("interpreter costs milliseconds to create (amortise it in a pool),")
    print("and every value that crosses costs marshalling - cheap for")
    print("shareable primitives, a pickle for everything else. The design that")
    print("wins is Chapter 84's: few crossings, big payloads, workers that own")
    print("their data. Subinterpreters do not remove the boundary; they move")
    print("it inside the process and make it explicit.")


if __name__ == "__main__":
    main()
