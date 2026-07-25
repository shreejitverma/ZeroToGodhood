"""Benchmark 65.1 - eager imports cost interpreter startup time.

Every module imported at startup runs its body before main() begins. This spawns
a fresh interpreter that imports nothing versus one that imports several heavy
stdlib modules, and times the whole process, so the import cost that a lazy import
would defer is visible as startup latency. Subprocess/startup timing is OS-bound
and noisy; min is the headline and the ratio is the finding.

Does its own subprocess timing (measure() cannot time a fresh interpreter),
guarded by __main__. See _harness/bench.py.
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

PY = sys.executable
HEAVY = "import decimal, json, xml.etree.ElementTree, email, http.client"


def best(args, reps=9):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        subprocess.run(args, capture_output=True)
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    print("=== 65.1  interpreter startup: bare vs eager heavy imports ===")
    print(provenance())
    print()

    bare = best([PY, "-c", "pass"])
    heavy = best([PY, "-c", HEAVY])

    print(f"  bare startup (import nothing) : {bare * 1000:7.1f} ms")
    print(f"  + eager heavy imports         : {heavy * 1000:7.1f} ms")
    print(f"  import overhead               : {(heavy - bare) * 1000:7.1f} ms  ({heavy / bare:.2f}x)")

    print()
    print("Reading this. Every module imported at startup runs its body before")
    print("your program does, so eagerly importing heavy modules adds real startup")
    print("latency, here several milliseconds for a handful of stdlib modules; a")
    print("large app importing dozens can spend hundreds of ms before main(). For")
    print("a long-running server this is paid once and irrelevant. For a CLI or a")
    print("frequently-invoked script it is user-visible lag. Defer heavy imports")
    print("(import inside the function that needs them, or PEP 562 lazy submodules,")
    print("Listing 65.1) so a run that does not use a feature does not pay to load")
    print("it.")


if __name__ == "__main__":
    main()
