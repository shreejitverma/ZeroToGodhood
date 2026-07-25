"""Benchmark 42.1 - pickle is faster and smaller than json for Python data.

The folklore is that json is the "fast, standard" choice. Measured on a nested
structure of 1000 records, pickle (binary) is faster to both dump and load AND
produces a smaller byte string than json (verbose text). So speed and size are
not reasons to prefer json; json's value is safety (it never executes code) and
interop (every language reads it). Choose on those axes, not on performance.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import json, pickle
data = {"users": [
    {"id": i, "name": f"user{i}", "active": i % 2 == 0, "score": i * 1.5}
    for i in range(1000)
]}
js = json.dumps(data)
pk = pickle.dumps(data)
"""


def sizes() -> None:
    import json
    import pickle
    data = {"users": [
        {"id": i, "name": f"user{i}", "active": i % 2 == 0, "score": i * 1.5}
        for i in range(1000)
    ]}
    js = len(json.dumps(data))
    pk = len(pickle.dumps(data))
    print(f"  serialized size: json {js:,} bytes  vs  pickle {pk:,} bytes "
          f"(json is {js / pk:.2f}x larger)")


def main() -> None:
    results = [
        measure("json.dumps", "json.dumps(data)", SETUP, number=2000),
        measure("pickle.dumps", "pickle.dumps(data)", SETUP, number=2000),
        measure("json.loads", "json.loads(js)", SETUP, number=2000),
        measure("pickle.loads", "pickle.loads(pk)", SETUP, number=2000),
    ]
    report("42.1  json vs pickle: dump and load a 1000-record structure",
           results, baseline="json.dumps")
    print()
    sizes()

    print()
    print("Reading this. pickle is faster to dump and to load, and its binary")
    print("form is smaller than json's verbose text. So performance is NOT the")
    print("reason to choose json. json's reasons are safety (json.loads never")
    print("runs code; pickle.loads does) and interoperability (json is universal;")
    print("pickle is Python-only). Use json for anything crossing a trust or")
    print("language boundary; use pickle only for trusted, Python-to-Python data")
    print("where its speed, size, and full type coverage are worth the lock-in.")


if __name__ == "__main__":
    main()
