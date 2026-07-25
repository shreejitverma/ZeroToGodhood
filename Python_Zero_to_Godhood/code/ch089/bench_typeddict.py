"""Benchmark 89.1 - TypedDict types dicts in place; a dataclass costs a conversion.

When data arrives as dicts (from JSON, a DB, kwargs), a TypedDict lets you use it
AS IS, with static typing, no conversion, no per-record object. To get the same
static typing from a dataclass, you must build an instance per dict, which
allocates an object and runs __init__ for every record. This measures reading a
field from 1000 records both ways: as TypedDicts in place, and by converting each
to a dataclass first.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from typing import TypedDict
from dataclasses import dataclass

class UserTD(TypedDict):
    id: int
    name: str

@dataclass
class UserDC:
    id: int
    name: str

raw = [{"id": i, "name": f"u{i}"} for i in range(1000)]   # e.g. json.loads output

def use_typeddict():
    total = 0
    for r in raw:              # each r is a UserTD (a dict): no conversion
        total += r["id"]
    return total

def convert_to_dataclass():
    total = 0
    for r in raw:
        total += UserDC(**r).id   # build a dataclass per record
    return total
"""


def main() -> None:
    results = [
        measure("TypedDict in place", "use_typeddict()", SETUP, number=5000),
        measure("convert to dataclass", "convert_to_dataclass()", SETUP, number=5000),
    ]
    report("89.1  reading 1000 dict records: TypedDict vs convert-to-dataclass",
           results, baseline="TypedDict in place")

    print()
    print("Reading this. Using the dicts as TypedDicts reads a field with no")
    print("conversion, they are already dicts. Converting each to a dataclass")
    print("allocates an object and runs __init__ per record, so it costs several")
    print("times more. For large volumes of dict-shaped data you only need to read")
    print("with static safety, TypedDict is far cheaper (zero conversion) and keeps")
    print("the data a plain dict (JSON-serializable, no unwrapping). Convert to a")
    print("dataclass when you need a real object, attribute access, methods,")
    print("validation, defaults, and the per-record cost is worth it.")


if __name__ == "__main__":
    main()
