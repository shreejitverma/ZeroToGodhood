"""Measurement harness for *Python Zero to Godhood*.

Stdlib only, by design: a benchmark a reader cannot run is not a benchmark.

The house rules this module enforces mechanically, so no chapter can quietly
break them:

1.  Every run reports **min, median, and relative standard deviation** over
    `repeat` independent batches. A single number is not a measurement.
    `min` is the headline statistic and the basis for every ratio; see
    `measure()` for why. Median and RSD are machine-quietness diagnostics.
2.  Every run emits its **provenance header**: interpreter version, build
    flags that actually move interpreter dispatch (`OPT`, computed gotos,
    PGO/LTO, free-threading), CPU, and core count.
3.  Results whose RSD exceeds `RSD_WARN` are marked `(machine busy)`. That is
    a caveat on the median, not a rejection of the min.
4.  Ratios are computed **within a single interpreter only**. See the note on
    cross-build comparison below, and `_harness/interpreters.py` for the
    diagnostic that reports whether two builds are comparable at all.

**Precision discipline.** Repeated runs of the same benchmark on an ordinary
developer machine reproduce a ratio to roughly one decimal place, not two. Cite
"about 2.7x", never "2.70x". Where a chapter needs a tighter figure than the
harness can defend, the chapter is wrong, not the harness.

**Cross-build comparison is invalid and this harness will not do it.**
Two CPython builds of different versions typically differ in optimisation
level and in whether computed gotos are enabled, either of which swamps the
effect sizes in this book. Comparisons are only ever made *within* a single
interpreter, between rows measured back to back. To compare versions, build
both from source with identical flags; until then, report each version's
table separately and draw no cross-version conclusion.
"""

from __future__ import annotations

import platform
import statistics
import subprocess
import sys
import sysconfig
import time
import timeit
from dataclasses import dataclass

RSD_WARN = 5.0  # percent; above this a row is flagged as noisy


@dataclass(frozen=True)
class Result:
    label: str
    median_ns: float
    min_ns: float
    rsd_pct: float
    repeat: int
    number: int

    @property
    def noisy(self) -> bool:
        return self.rsd_pct > RSD_WARN


def _cpu() -> str:
    if sys.platform == "darwin":
        try:
            return subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return platform.processor() or platform.machine()


def provenance() -> str:
    """The header every benchmark table in this book carries."""
    gil = "n/a"
    if hasattr(sys, "_is_gil_enabled"):
        gil = "enabled" if sys._is_gil_enabled() else "DISABLED (free-threaded)"
    cfg = sysconfig.get_config_var
    args = cfg("CONFIG_ARGS") or ""
    lines = [
        f"interpreter : CPython {platform.python_version()} ({platform.python_implementation()})",
        f"build       : OPT={ (cfg('OPT') or '').strip() !r}"
        f"  computed_gotos={cfg('USE_COMPUTED_GOTOS')}"
        f"  pgo={'--enable-optimizations' in args}"
        f"  lto={'--with-lto' in args}",
        f"gil         : {gil}",
        f"platform    : {platform.system()} {platform.release()} / {platform.machine()}",
        f"cpu         : {_cpu()}",
    ]
    return "\n".join(lines)


def measure(label: str, stmt: str, setup: str = "pass", *,
            repeat: int = 15, number: int = 20_000) -> Result:
    """Time `stmt` and return a Result carrying its own spread.

    Uses `time.perf_counter` explicitly rather than timeit's platform default
    so the timer source is the same on every machine that runs this book.

    **Why `min` is the headline statistic, not the mean or median.** For a
    CPU-bound microbenchmark, measurement noise is *one-sided*: a scheduler
    preemption, an interrupt, or a competing process can only ever make a batch
    slower, never faster. The fastest observed batch is therefore the closest
    estimate of the work's true cost, and the mean is an estimate of the work
    plus whatever else the machine was doing. This is the reasoning the
    `timeit` documentation gives for the same choice.

    The median and RSD are still computed and reported, but as *diagnostics*:
    they describe how quiet the machine was, not how fast the code is. A high
    RSD alongside a stable min means the measurement is fine and the machine is
    busy. A high RSD with a drifting min means the benchmark itself is unstable
    and should not be cited at all.
    """
    timer = timeit.Timer(stmt, setup, timer=time.perf_counter)
    timer.timeit(number=max(number // 10, 1))  # warm-up: let the specializer settle
    batches = timer.repeat(repeat=repeat, number=number)
    per_op = [t / number * 1e9 for t in batches]
    median = statistics.median(per_op)
    rsd = (statistics.stdev(per_op) / median * 100.0) if median else 0.0
    return Result(label, median, min(per_op), rsd, repeat, number)


def table(results: list[Result], *, baseline: str | None = None) -> str:
    """Render results. Ratios are computed from `min`, the robust statistic."""
    base = next((r for r in results if r.label == baseline), None) if baseline else None
    width = max(len(r.label) for r in results)
    head = f"{'case'.ljust(width)}      min_ns   median_ns   RSD%"
    if base:
        head += "   ratio"
    rows = [head, "-" * len(head)]
    for r in results:
        row = f"{r.label.ljust(width)} {r.min_ns:11.1f} {r.median_ns:11.1f} {r.rsd_pct:6.1f}"
        if base:
            row += f"   {r.min_ns / base.min_ns:5.2f}x"
        if r.noisy:
            row += "   (machine busy)"
        rows.append(row)
    return "\n".join(rows)


def report(title: str, results: list[Result], *, baseline: str | None = None) -> None:
    print(f"=== {title} ===")
    print(provenance())
    r0 = results[0]
    print(f"method      : repeat={r0.repeat} batches x number={r0.number} ops,"
          f" warm-up {r0.number // 10} ops, perf_counter")
    print("statistic   : min is the headline (noise is one-sided); median/RSD are")
    print("              machine-quietness diagnostics, not speed. See bench.py.")
    print("note        : ratios are within-interpreter only.")
    print()
    print(table(results, baseline=baseline))
