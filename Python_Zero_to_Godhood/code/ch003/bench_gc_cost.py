"""Benchmark 3.1 - when disabling the cyclic collector helps, and when it hurts.

The folklore is "disable gc for speed." It is right in one case and actively
wrong in another, and the difference is the whole lesson.

Case A - building a large, long-lived structure. Every object survives, so each
automatic gen-0 collection traces a growing survivor set for nothing: the
objects are not garbage and will not be collected. Disabling the collector
during the build removes that wasted tracing. This is the case the folklore has
in mind, and here disabling HELPS.

Case B - churning short-lived cycles. Each iteration builds a reference cycle
and drops it. Refcounting cannot reclaim a cycle, so only the collector can.
Disable it and the cycles pile up until a single final collect() must trace all
of them at once, which is more expensive than the incremental gen-0 passes it
replaced. Here disabling HURTS.

Within a single interpreter; min is the headline statistic. See bench.py.
"""

import gc
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

# Case A: build a long-lived list of tracked objects. All survive.
BUILD = "big = [{'i': i} for i in range(50000)]"
A_ENABLED = "gc.enable()\ngc.collect()\n" + BUILD
A_DISABLED = "gc.disable()\n" + BUILD + "\ngc.enable()"

# Case B: churn short-lived cycles that only the collector can reclaim.
CHURN = "\n".join([
    "for _ in range(50000):",
    "    a = {}",
    "    b = {}",
    "    a['b'] = b",
    "    b['a'] = a",
])
B_ENABLED = "gc.enable()\ngc.collect()\n" + CHURN
B_DISABLED = "gc.disable()\n" + CHURN + "\ngc.collect()\ngc.enable()"


def main() -> None:
    a = [
        measure("collector enabled ", A_ENABLED, "import gc", number=100),
        measure("collector disabled", A_DISABLED, "import gc", number=100),
    ]
    report("3.1a  building 50k long-lived objects: disabling HELPS",
           a, baseline="collector enabled ")

    print()
    b = [
        measure("collector enabled ", B_ENABLED, "import gc", number=100),
        measure("collector disabled", B_DISABLED, "import gc", number=100),
    ]
    report("3.1b  churning 50k short-lived cycles: disabling HURTS",
           b, baseline="collector enabled ")

    print()
    print("The rule the two cases teach. gc.disable() removes tracing work, and")
    print("tracing is wasted only when the objects being traced will not be")
    print("collected: long-lived survivors (3.1a). When there is real cyclic")
    print("garbage to reclaim (3.1b), disabling only defers the work into a")
    print("larger, later batch and grows memory in the meantime. Reach for")
    print("gc.disable()/gc.freeze() around a bounded phase that builds long-lived")
    print("state, not as a blanket speedup.")


if __name__ == "__main__":
    main()
