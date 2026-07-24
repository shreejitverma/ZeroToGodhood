"""Report the verification matrix, and refuse to let builds be compared silently.

This exists because of a specific finding during the Book II audit. The two
interpreters on the author's machine are:

    CPython 3.13.5   OPT='-O2'      computed gotos ON
    CPython 3.14.6   OPT='-O3 -g'   computed gotos OFF

Computed gotos are the interpreter's dispatch mechanism. A build without them
is materially slower at exactly the thing this book measures. So a timing
comparison across those two builds measures the *build*, not the interpreter,
and any "3.14 is slower than 3.13" conclusion drawn from them is an artifact.

`bench.py` refuses to rank rows from different interpreters. This module is the
diagnostic that tells you *why* two interpreters are not comparable, and what
you would have to do to make them so.

Usage:
    python3 -m _harness.interpreters
"""

from __future__ import annotations

import platform
import sys
import sysconfig

# Config vars that actually move interpreter dispatch speed. A difference in
# any of these invalidates a cross-build timing comparison.
DISPATCH_CRITICAL = ("OPT", "USE_COMPUTED_GOTOS", "Py_GIL_DISABLED", "Py_DEBUG")


def fingerprint() -> dict[str, str]:
    cfg = sysconfig.get_config_var
    args = cfg("CONFIG_ARGS") or ""
    fp = {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "machine": platform.machine(),
        "pgo": str("--enable-optimizations" in args),
        "lto": str("--with-lto" in args),
    }
    for key in DISPATCH_CRITICAL:
        fp[key] = str(cfg(key))
    if hasattr(sys, "_is_gil_enabled"):
        fp["gil_enabled"] = str(sys._is_gil_enabled())
    return fp


def comparable(a: dict[str, str], b: dict[str, str]) -> tuple[bool, list[str]]:
    """Two builds are timing-comparable only if every dispatch-critical var matches."""
    diffs = [k for k in DISPATCH_CRITICAL + ("pgo", "lto")
             if a.get(k) != b.get(k)]
    return (not diffs), diffs


def main() -> int:
    fp = fingerprint()
    print(f"=== CPython {fp['version']} ({fp['machine']}) ===")
    for k, v in fp.items():
        if k not in ("version", "machine"):
            print(f"  {k:20} {v}")
    print()
    print("  Timing results from this build may be compared only against builds")
    print("  with identical OPT, USE_COMPUTED_GOTOS, Py_GIL_DISABLED, pgo, and lto.")
    print("  To compare CPython versions, build both from source with the same flags.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
