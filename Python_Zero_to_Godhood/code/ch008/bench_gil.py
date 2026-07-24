"""Benchmark 8.1 - the GIL, made visible: threads do not parallelize CPU work,
but they do parallelize I/O.

This is the measurement a GIL chapter needs. The same four tasks are run
serially, across four threads, and (for CPU work) across four processes. The
result is the whole practical meaning of the GIL:

  CPU-bound + threads : no speedup (the GIL serializes bytecode)
  CPU-bound + processes: real speedup, minus a serialization tax
  I/O-bound + threads : near-linear speedup (the GIL is released during I/O)

This does NOT use the microbenchmark harness (measure()), because the tasks are
coarse-grained and a process pool cannot be spun up thousands of times. It does
its own min-of-N timing and reuses the harness provenance header so the run is
still fully attributed.

Because it launches a ProcessPoolExecutor, the whole file is guarded by
`if __name__ == "__main__"` for the spawn start method.
"""

import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

WORKERS = 4
CPU_N = 3_000_000
IO_SLEEP = 0.05


def cpu_task(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


def io_task(_):
    time.sleep(IO_SLEEP)
    return 1


def best(fn, repeat=5):
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return min(times)


def serial_cpu():
    for _ in range(WORKERS):
        cpu_task(CPU_N)


def threads_cpu():
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(cpu_task, [CPU_N] * WORKERS))


def processes_cpu():
    with ProcessPoolExecutor(WORKERS) as ex:
        list(ex.map(cpu_task, [CPU_N] * WORKERS))


def serial_io():
    for _ in range(WORKERS):
        io_task(0)


def threads_io():
    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(io_task, [0] * WORKERS))


def main():
    print("=== 8.1  the GIL, made visible ===")
    print(provenance())
    print(f"method      : {WORKERS} tasks, min of 5 runs, perf_counter")
    print()

    processes_cpu()  # warm the pool (pay spawn cost outside timing)
    s_cpu = best(serial_cpu)
    t_cpu = best(threads_cpu)
    p_cpu = best(processes_cpu)
    s_io = best(serial_io)
    t_io = best(threads_io)

    print(f"CPU-bound  serial     : {s_cpu * 1e3:7.1f} ms   1.00x")
    print(f"CPU-bound  4 threads  : {t_cpu * 1e3:7.1f} ms   {s_cpu / t_cpu:.2f}x   <- GIL: no speedup")
    print(f"CPU-bound  4 processes: {p_cpu * 1e3:7.1f} ms   {s_cpu / p_cpu:.2f}x   <- real parallelism, minus tax")
    print(f"I/O-bound  serial     : {s_io * 1e3:7.1f} ms   1.00x")
    print(f"I/O-bound  4 threads  : {t_io * 1e3:7.1f} ms   {s_io / t_io:.2f}x   <- GIL released during I/O")


if __name__ == "__main__":
    main()
