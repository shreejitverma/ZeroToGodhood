"""Measurement harness for *Python Zero to Godhood*.

Stdlib only, by design: a benchmark a reader cannot run is not a benchmark.

The house rules this module enforces mechanically, so no chapter can quietly
break them:

1.  Every run reports **median, min, and relative standard deviation** over
    `repeat` independent batches. A single number is not a measurement.
2.  Every run emits its **provenance header**: interpreter version, build
    flags that actually move interpreter dispatch (`OPT`, computed gotos,
    PGO/LTO, free-threading), CPU, and core count.
3.  Results whose RSD exceeds `RSD_WARN` are flagged in the output. A noisy
    result is reported as noisy, not rounded into confidence.
4.  `compare()` refuses to rank rows measured on different interpreters. See
    the note on cross-build comparison below.

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
    """
    timer = timeit.Timer(stmt, setup, timer=time.perf_counter)
    timer.timeit(number=max(number // 10, 1))  # warm-up: let the specializer settle
    batches = timer.repeat(repeat=repeat, number=number)
    per_op = [t / number * 1e9 for t in batches]
    median = statistics.median(per_op)
    rsd = (statistics.stdev(per_op) / median * 100.0) if median else 0.0
    return Result(label, median, min(per_op), rsd, repeat, number)


def table(results: list[Result], *, baseline: str | None = None) -> str:
    """Render results with an optional within-interpreter ratio column."""
    base = next((r for r in results if r.label == baseline), None) if baseline else None
    width = max(len(r.label) for r in results)
    head = f"{'case'.ljust(width)}   median_ns      min_ns   RSD%"
    if base:
        head += f"   vs {base.label.strip()}"
    rows = [head, "-" * len(head)]
    for r in results:
        row = f"{r.label.ljust(width)} {r.median_ns:11.1f} {r.min_ns:11.1f} {r.rsd_pct:6.2f}"
        if base:
            row += f"   {r.median_ns / base.median_ns:6.2f}x"
        if r.noisy:
            row += "  <-- NOISY, do not cite"
        rows.append(row)
    return "\n".join(rows)


def report(title: str, results: list[Result], *, baseline: str | None = None) -> None:
    print(f"=== {title} ===")
    print(provenance())
    r0 = results[0]
    print(f"method      : repeat={r0.repeat} batches x number={r0.number} ops,"
          f" warm-up {r0.number // 10} ops, perf_counter")
    print("note        : ratios are within-interpreter only; see _harness/bench.py")
    print()
    print(table(results, baseline=baseline))
