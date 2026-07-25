"""Benchmark 52.1 - guarding an expensive log argument with isEnabledFor.

The logging level is set so DEBUG is disabled (nothing is emitted). Three forms:
  A: log.debug("v=%s", expensive())  -> expensive() runs anyway (eager args)
  B: guarded by isEnabledFor(DEBUG)  -> expensive() is skipped
  C: log.debug("literal")            -> cheap arg, no guard needed

Lazy-% (Chapter 12) saves the FORMATTING; only the guard saves the argument
EVALUATION. So the guard matters exactly when an argument is costly to build.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import logging
log = logging.getLogger("ch052bench")
log.setLevel(logging.WARNING)   # DEBUG disabled

def expensive():
    return sum(i for i in range(1000))

def unguarded():
    log.debug("value=%s", expensive())

def guarded():
    if log.isEnabledFor(logging.DEBUG):
        log.debug("value=%s", expensive())
"""


def main() -> None:
    results = [
        measure("guarded (isEnabledFor)", "guarded()", SETUP, number=50000),
        measure("cheap literal debug", "log.debug('hello')", SETUP, number=50000),
        measure("unguarded, expensive arg", "unguarded()", SETUP, number=50000),
    ]
    report("52.1  a disabled DEBUG call: guarded vs expensive-argument",
           results, baseline="guarded (isEnabledFor)")

    print()
    print("Reading this. The unguarded call is far more expensive than the guarded")
    print("one, even though NOTHING is logged, because Python evaluates expensive()")
    print("before calling log.debug. isEnabledFor skips the evaluation entirely. A")
    print("cheap literal argument needs no guard (it is already near-free with the")
    print("lazy-% form of Chapter 12). The rule: use lazy-% everywhere, and add an")
    print("isEnabledFor guard only around log calls whose ARGUMENTS are expensive")
    print("to compute.")


if __name__ == "__main__":
    main()
