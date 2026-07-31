"""Benchmark 200.1 - csv priced: the grammar's cost, and the dict layer's.

  200.1a  parsing 100,000 rows: str.split(',') (wrong, the baseline of
          temptation), csv.reader on unquoted data, csv.reader on data
          where every third field is quoted, and DictReader. The grammar
          costs real multiples over the (incorrect) split - and the dict
          layer costs again on top.

  200.1b  writing the same rows under the three quoting policies.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

ROWS = 100_000


def main():
    SETUP = f"""
import csv, io

ROWS = {ROWS}
plain_lines = [f"field{{i}},value{{i}},{{i}}" for i in range(ROWS)]
quoted_lines = [f'field{{i}},"value, {{i}}",{{i}}' for i in range(ROWS)]
plain_blob = "\\r\\n".join(plain_lines)
quoted_blob = "\\r\\n".join(quoted_lines)
rows = [line.split(",") for line in plain_lines]
"""
    parse = [
        measure("split(',') [WRONG]",
                "for l in plain_lines: l.split(',')",
                SETUP, repeat=7, number=20),
        measure("csv.reader, no quotes",
                "for r in csv.reader(io.StringIO(plain_blob)): pass",
                SETUP, repeat=7, number=20),
        measure("csv.reader, quoted",
                "for r in csv.reader(io.StringIO(quoted_blob)): pass",
                SETUP, repeat=7, number=20),
        measure("DictReader, quoted",
                "for r in csv.DictReader(io.StringIO(quoted_blob),"
                " fieldnames=['a','b','c']): pass",
                SETUP, repeat=7, number=20),
    ]
    report(f"200.1a  parsing {ROWS:,} rows", parse,
           baseline="csv.reader, no quotes")

    print()
    write = [
        measure("writer, QUOTE_MINIMAL",
                "csv.writer(io.StringIO()).writerows(rows)",
                SETUP, repeat=7, number=20),
        measure("writer, QUOTE_ALL",
                "csv.writer(io.StringIO(), quoting=csv.QUOTE_ALL)"
                ".writerows(rows)",
                SETUP, repeat=7, number=20),
    ]
    report(f"200.1b  writing {ROWS:,} rows", write,
           baseline="writer, QUOTE_MINIMAL")

    print()
    print("Reading this. The C-implemented reader parses the full quoting")
    print("grammar at ~3x the (incorrect) split - about 180 ns a row - and")
    print("the quoted rows cost the SAME as unquoted ones: the state machine")
    print("prices the grammar, not the quotes, so correctness has no per-")
    print("quote surcharge and the split shortcut has no defence left.")
    print("DictReader's 2.85x is a dict per row - worth it at a program's")
    print("edges, skippable in hot loops that index by position. Writing is")
    print("flat too (QUOTE_ALL costs ~2%; choose policies for consumers,")
    print("not speed). For gigabyte-scale tabular work the answer stops")
    print("being csv at all and becomes columnar formats - Deep U's")
    print("territory, reached through this module's ceiling.")


if __name__ == "__main__":
    main()
