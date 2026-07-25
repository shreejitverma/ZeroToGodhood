"""Benchmark 54.1 - warnings.warn is not free even when the warning is ignored.

warnings.warn inspects the call stack to find the source location (module and
line) so filters can match and deduplicate by location. That stack inspection
happens even when the applicable filter is 'ignore' and nothing is shown, so
emitting a warning in a hot loop costs far more than a no-op, even in production
where the warning is silenced. This measures warn() under an 'ignore' filter
against a plain call.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import warnings
warnings.simplefilter("ignore")   # the warning is silenced...

def noop():
    pass
"""


def main() -> None:
    results = [
        measure("no-op call", "noop()", SETUP, number=100000),
        measure("warnings.warn (ignored)", "warnings.warn('x', UserWarning)", SETUP, number=100000),
    ]
    report("54.1  warnings.warn under an 'ignore' filter vs a no-op",
           results, baseline="no-op call")

    print()
    print("Reading this. Even though the warning is ignored and nothing is shown,")
    print("warnings.warn still inspects the call stack to find the source location")
    print("for filter matching and deduplication, so it costs far more than a plain")
    print("call. Do not emit warnings inside a hot loop: warn once at the API entry")
    print("(e.g. the first call of a deprecated function), not per iteration. The")
    print("filter silences the OUTPUT, not the cost of producing the warning.")


if __name__ == "__main__":
    main()
