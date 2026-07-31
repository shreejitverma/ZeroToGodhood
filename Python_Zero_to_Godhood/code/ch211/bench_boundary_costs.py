"""Benchmark 211.1 - the boundary priced: parse, validate, serialize.

  211.1a  the round trip on one small order: json.loads, the hand-written
          schema check, and json.dumps, each timed separately, so the
          boundary's cost is attributed to its three jobs. json is C
          (Chapter 42); the validation is Python, and it is the part that
          scales with schema richness.

  211.1b  parse cost vs payload size: json.loads on 1 KB, 10 KB, and 100 KB
          bodies. Parsing is linear in bytes and fast, so the boundary is
          not the budget line for normal payloads - but a body-size limit
          is a security control (Chapter 125's bounded reads), because an
          attacker's 100 MB JSON is a memory-and-CPU denial of service the
          parser will faithfully perform.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402


def main():
    SETUP = """
import json
sys_path_ok = True
raw = b'{"symbol":"ACME","side":"buy","qty":100}'
obj = json.loads(raw)

def validate(data):
    errors = {}
    if not isinstance(data.get("symbol"), str) or not data["symbol"]:
        errors["symbol"] = "bad"
    if data.get("side") not in ("buy", "sell"):
        errors["side"] = "bad"
    q = data.get("qty")
    if not isinstance(q, int) or isinstance(q, bool) or q <= 0:
        errors["qty"] = "bad"
    return errors
"""
    rows = [
        measure("json.loads (parse)", "json.loads(raw)", SETUP),
        measure("validate (schema)", "validate(obj)", SETUP),
        measure("json.dumps (serialize)",
                "json.dumps(obj, separators=(',', ':'))", SETUP),
    ]
    report("211.1a  the round trip on a small order", rows,
           baseline="json.loads (parse)")

    print()
    SIZE_SETUP = """
import json
def make(n):
    return json.dumps([{"symbol": f"S{i}", "side": "buy", "qty": i}
                       for i in range(n)]).encode()
kb1 = make(20)
kb10 = make(200)
kb100 = make(2000)
"""
    rows = [
        measure("parse ~1 KB", "json.loads(kb1)", SIZE_SETUP,
                repeat=9, number=2000),
        measure("parse ~10 KB", "json.loads(kb10)", SIZE_SETUP,
                repeat=9, number=500),
        measure("parse ~100 KB", "json.loads(kb100)", SIZE_SETUP,
                repeat=9, number=50),
    ]
    report("211.1b  parse cost vs payload size", rows, baseline="parse ~1 KB")

    print()
    print("Reading this. The C json parser and serializer are microseconds")
    print("on a small object; the hand-written validation is comparable, and")
    print("in real schemas (nested objects, many fields, cross-field rules)")
    print("validation becomes the boundary's dominant cost - which is why")
    print("schema libraries (pydantic, and its Rust core) exist and why they")
    print("compile schemas rather than interpret them per request. Parsing is")
    print("linear in size and cheap, so a normal body is free; but that same")
    print("faithfulness is the attack - the parser will happily allocate a")
    print("gigabyte for a gigabyte of JSON, so a body-SIZE limit at the")
    print("boundary (Chapter 125) is a security control, not an optimisation.")


if __name__ == "__main__":
    main()
