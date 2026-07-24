"""Benchmark 22.1 - why sys.monitoring replaced sys.settrace for tools.

sys.settrace installs one global tracer that the interpreter calls on every line
(or call) of every frame, which not only adds per-line dispatch but defeats the
specializing interpreter (Chapter 17): a traced frame cannot run specialized
opcodes. sys.monitoring only pays when an event a tool subscribed to actually
fires, and idle monitoring costs nothing. This measures the difference.

Coarse-grained timing done directly; provenance header reused from the harness.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


def work(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


def best(fn, repeat=5):
    return min(_timed(fn) for _ in range(repeat))


def _timed(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def line_tracer(frame, event, arg):
    return line_tracer


def main():
    print("=== 22.1  monitoring overhead: settrace vs sys.monitoring ===")
    print(provenance())
    print(f"method      : work(N={N:,}), min of 5 runs")
    print()

    base = best(lambda: work(N))

    sys.settrace(line_tracer)
    traced = best(lambda: work(N))
    sys.settrace(None)

    mon = sys.monitoring
    mon.use_tool_id(mon.DEBUGGER_ID, "idle")
    mon.set_events(mon.DEBUGGER_ID, 0)          # registered but no events enabled
    idle = best(lambda: work(N))
    mon.free_tool_id(mon.DEBUGGER_ID)

    print(f"  baseline (no tools)        : {base * 1e3:7.1f} ms   1.00x")
    print(f"  sys.settrace line tracer   : {traced * 1e3:7.1f} ms   {traced / base:.2f}x")
    print(f"  sys.monitoring, no events  : {idle * 1e3:7.1f} ms   {idle / base:.2f}x")

    print()
    print("Reading this. A global settrace tracer costs a couple of times the")
    print("baseline on a tight loop, because it fires per line AND forces the")
    print("frame off the specialized fast path. sys.monitoring registered with no")
    print("events enabled costs nothing: the interpreter runs at full speed until")
    print("a subscribed event actually fires, and even then only for the code")
    print("objects a tool asked to watch. This is why 3.12+ debuggers, coverage")
    print("tools, and profilers moved to it.")


if __name__ == "__main__":
    main()
