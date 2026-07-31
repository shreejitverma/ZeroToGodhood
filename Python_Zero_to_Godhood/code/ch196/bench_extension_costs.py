"""Benchmark 196.1 - the compiled module, priced: build, load, call.

  196.1a  compiling the twelve-line module: full ABI vs limited API. The
          absolute times are toy-sized; the point is that limited-API
          builds cost the same to MAKE - they are only narrower in what
          they may call (Chapter 82 measured the runtime cost).

  196.1b  first import of the .so against a same-purpose .py module: the
          dlopen path against the bytecode path (Chapter 109's install-
          shape table gains its native row).

  196.1c  calling answer() from the compiled module against an identical
          Python function - Chapter 76's boundary, certified on an artifact
          this volume built itself.

Requires a C compiler. Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402
from ch196.l01_compiled_for_this_abi import PLAIN_SRC, compile_module  # noqa: E402

CALLS = 1_000_000


def best(fn, repeat=5):
    return min(fn() for _ in range(repeat))


def timed(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def per_call_ns(fn):
    def run():
        t0 = time.perf_counter()
        for _ in range(CALLS):
            fn()
        return (time.perf_counter() - t0) * 1e9 / CALLS
    return best(run)


def main():
    print("=== 196.1a  compile time, full ABI vs limited API ===")
    print(provenance())
    print()
    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp)
        full_ms = best(lambda: timed(
            lambda: compile_module(build, "m1", PLAIN_SRC))) * 1000
        print(f"  full ABI    : {full_ms:6.1f} ms")
        if compile_module(build, "m2", PLAIN_SRC, limited=True):
            lim_ms = best(lambda: timed(lambda: compile_module(
                build, "m2", PLAIN_SRC, limited=True))) * 1000
            print(f"  limited API : {lim_ms:6.1f} ms")
        else:
            print("  limited API : refused on this build (free-threaded)")

        print()
        print("=== 196.1b  first import: native .so vs .py ===")
        (build / "pymod.py").write_text("def answer():\n    return 42\n")
        code_tpl = ("import sys, time; sys.path.insert(0, {p!r}); "
                    "t0 = time.perf_counter(); import {m}; "
                    "print((time.perf_counter() - t0) * 1e6)")

        def fresh_import(module):
            def run():
                out = subprocess.run(
                    [sys.executable, "-c",
                     code_tpl.format(p=str(build), m=module)],
                    capture_output=True, text=True, check=True)
                return float(out.stdout)
            return best(run, repeat=9)

        print(f"  import pymod (.py) : {fresh_import('pymod'):7,.0f} us")
        print(f"  import m1 (.so)    : {fresh_import('m1'):7,.0f} us")

        print()
        print("=== 196.1c  one call, both sides of the boundary ===")
        sys.path.insert(0, str(build))
        try:
            import m1
            c_answer = m1.answer
        finally:
            sys.path.remove(str(build))

        def py_answer():
            return 42

        py_ns = per_call_ns(py_answer)
        c_ns = per_call_ns(c_answer)
        print(f"  python function call : {py_ns:6.1f} ns")
        print(f"  C extension call     : {c_ns:6.1f} ns")

    print()
    print("Reading this. Compilation is sub-second for toy sources; the")
    print("matrix (versions x flavours x platforms) is what multiplies it")
    print("into hours, and why abi3 (one build, many versions) and")
    print("cibuildwheel-style automation exist. Loading a .so adds a dlopen")
    print("to the finder walk. And the call itself is CHEAPER than a Python")
    print("call - no frame, no bytecode - Chapter 76's lesson certified on")
    print("an artifact this chapter built. The expensive part of native")
    print("code is never calling it; it is building, tagging, and shipping")
    print("it compatibly - this chapter's actual subject.")


if __name__ == "__main__":
    main()
