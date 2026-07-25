"""Benchmark 133.1 - spawning a subprocess is expensive; never do it per item.

subprocess.run forks the process, execs a whole new program, sets up pipes, and waits
for it to exit, milliseconds of work, even for a trivial program like 'true'. Compared
to an in-process call (nanoseconds), a subprocess is tens of thousands of times more
expensive. This measures the cost of spawning a trivial external process, to show that
shelling out per item in a loop is a serious anti-pattern.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 300


def main():
    print("=== 133.1  cost of spawning a subprocess vs an in-process call ===")
    print(provenance())
    print()

    t0 = time.perf_counter()
    for _ in range(N):
        subprocess.run(["true"], capture_output=True)   # fork + exec a whole program
    t_sub = (time.perf_counter() - t0) / N

    t0 = time.perf_counter()
    for _ in range(N):
        os.getpid()                                      # a trivial in-process call
    t_inproc = (time.perf_counter() - t0) / N

    print(f"  subprocess.run(['true']) : {t_sub * 1e6:7.0f} us/call   ({t_sub * 1e3:.2f} ms)")
    print(f"  in-process os.getpid()   : {t_inproc * 1e9:7.0f} ns/call")
    print(f"  the subprocess costs ~{t_sub / t_inproc:,.0f}x more")

    print()
    print("Reading this. Launching even a trivial external program costs a couple of")
    print("milliseconds: the OS forks the process, execs a new program image, wires up")
    print("pipes for its stdio, and waits for it to exit, tens of thousands of times")
    print("the cost of an in-process call. So calling a subprocess PER ITEM in a loop")
    print("(a thousand items, a thousand spawns) is seconds of pure overhead. The")
    print("rules: (1) prefer a Python LIBRARY over shelling out when one exists (parse")
    print("in-process, do not spawn 'grep'); (2) if you must call an external tool, do")
    print("it ONCE over a batch (pass all the data in), not once per item, the")
    print("amortize-the-boundary rule at the process-spawn boundary.")


if __name__ == "__main__":
    main()
