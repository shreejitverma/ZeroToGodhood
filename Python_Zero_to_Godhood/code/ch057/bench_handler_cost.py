"""Benchmark 57.1 - a non-strict error handler costs almost nothing on clean data.

A defensive concern: does decoding with errors='surrogateescape' (so undecodable
bytes never crash) slow down the common case of clean, valid UTF-8? It does not:
the error handler only engages when an error actually occurs, so on valid data
the non-strict decode is essentially as fast as strict. This measures decoding a
block of clean UTF-8 with strict, surrogateescape, and replace.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
clean = ("The quick brown fox jumps over the lazy dog. " * 50).encode("utf-8")
"""


def main() -> None:
    results = [
        measure("strict (default)", "clean.decode('utf-8')", SETUP, number=100000),
        measure("surrogateescape", "clean.decode('utf-8', errors='surrogateescape')", SETUP, number=100000),
        measure("replace", "clean.decode('utf-8', errors='replace')", SETUP, number=100000),
    ]
    report("57.1  decoding clean UTF-8 with different error handlers",
           results, baseline="strict (default)")

    print()
    print("Reading this. On valid data the non-strict handlers are within a few")
    print("percent of strict, because the handler is only invoked when a byte")
    print("actually fails to decode, which never happens for clean input. So you")
    print("can decode defensively (surrogateescape, so undecodable bytes round-trip")
    print("instead of crashing) without a meaningful cost on the common case. The")
    print("handler earns its keep on the rare malformed input and is nearly free")
    print("otherwise. Prefer surrogateescape for filesystem/CLI data, and NEVER")
    print("'ignore' (it silently deletes data).")


if __name__ == "__main__":
    main()
