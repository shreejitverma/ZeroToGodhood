"""Benchmark 207.1 - the WSGI dispatch cost, and the synchronous ceiling.

  207.1a  the per-request framework overhead: calling a WSGI app (build
          environ, dispatch, collect body) against calling the handler
          function directly. This is the tax the contract imposes, and it
          is tiny - the contract's cost was never CPU.

  207.1b  the ceiling, modelled: a pool of W synchronous workers each
          serving requests that spend `io_ms` waiting (a database, an
          upstream). Throughput is W / io_time by Little's law, so a
          blocking worker's whole idle wait is capacity you paid for and
          cannot use - the number that sends I/O-bound web work to async
          (Chapter 127). Modelled arithmetic, not a live server, so it is
          deterministic; the live version is exercise 4.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, provenance, report  # noqa: E402


def main():
    SETUP = """
import io
from wsgiref.util import setup_testing_defaults

def handler(path):
    return b"pong" if path == "/ping" else b"not found"

def app(environ, start_response):
    body = handler(environ["PATH_INFO"])
    start_response("200 OK", [("Content-Length", str(len(body)))])
    return [body]

base = {}
setup_testing_defaults(base)

def call():
    environ = dict(base)
    environ["PATH_INFO"] = "/ping"
    captured = []
    def start_response(status, headers, exc_info=None):
        captured.append(status)
    return b"".join(app(environ, start_response))
"""
    rows = [
        measure("handler() direct", "handler('/ping')", SETUP),
        measure("through the WSGI app", "call()", SETUP),
    ]
    report("207.1a  the WSGI dispatch overhead", rows,
           baseline="handler() direct")

    print()
    print("=== 207.1b  the synchronous ceiling (Little's law) ===")
    print(provenance())
    print("method      : arithmetic model; throughput = workers / request_time")
    print()
    cpu_ms = 1.0
    print(f"  model: {cpu_ms:.0f} ms CPU per request, plus I/O wait")
    print(f"  {'workers':>8} {'io_wait':>9} {'req/s':>10} {'CPU used':>10}")
    for workers in (16, 64):
        for io_ms in (0, 10, 100):
            req_time_s = (cpu_ms + io_ms) / 1000
            throughput = workers / req_time_s
            cpu_frac = cpu_ms / (cpu_ms + io_ms)
            print(f"  {workers:>8} {io_ms:>7} ms {throughput:>10,.0f}"
                  f" {cpu_frac:>9.0%}")

    print()
    print("Reading this. The dispatch tax is real and tiny - a WSGI call is")
    print("a dict, a function call, and a list, measured in hundreds of")
    print("nanoseconds, which is why the contract's cost was never the")
    print("argument against it. The ceiling table is the argument: a")
    print("synchronous worker blocked in a 100 ms database call is holding a")
    print("whole worker to use 1% of a CPU, so 64 workers cap at a few")
    print("hundred req/s no matter how fast the code is. You buy throughput")
    print("by adding workers (memory and context-switch cost, Deep L) until")
    print("the machine is full of mostly-waiting processes - the C10k wall")
    print("WSGI cannot climb, and the exact reason ASGI (Chapter 127) moves")
    print("the waiting onto one event loop instead of one worker each.")


if __name__ == "__main__":
    main()
