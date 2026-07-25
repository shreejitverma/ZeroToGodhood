"""Benchmark 36.1 - fromisoformat vs strptime for ISO-8601 timestamps.

strptime interprets a format string at every call (it parses the format, then
the value); fromisoformat is a dedicated C parser for the ISO-8601 grammar. For
the common case of parsing ISO timestamps (logs, JSON, databases), the
difference is large. Since 3.11 fromisoformat also accepts the fuller ISO
grammar (Z suffix, space separator), so it covers most real timestamps.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from datetime import datetime
iso = "2026-07-24T12:34:56.789012+00:00"
fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
"""


def main() -> None:
    results = [
        measure("fromisoformat", "datetime.fromisoformat(iso)", SETUP, number=50000),
        measure("strptime", "datetime.strptime(iso, fmt)", SETUP, number=50000),
    ]
    report("36.1  parsing an ISO-8601 timestamp",
           results, baseline="fromisoformat")

    print()
    print("Reading this. fromisoformat is a dedicated C parser for the ISO-8601")
    print("grammar; strptime interprets a format string on every call. For the")
    print("common case of ISO timestamps from logs, JSON, or a database, prefer")
    print("fromisoformat: it is far faster and, since 3.11, accepts the Z suffix")
    print("and a space separator. Reserve strptime for genuinely non-ISO formats")
    print("(e.g. '24/07/2026 12:34 PM'), where you must describe the layout.")


if __name__ == "__main__":
    main()
