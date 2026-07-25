"""Benchmark 63.1 - a cached import is a dict lookup; running the body is not.

importlib.import_module on an already-loaded module just returns it from
sys.modules (a dict lookup). importlib.reload forces the module BODY to run
again. This measures both, so the gap between "import the cached module" and
"actually execute its top-level code" is visible: the body cost is paid once at
first import, and every later import is essentially free.

The helper _importonce does a small amount of import-time work (building a list
of 1000 squares); a real module's body can be far heavier, widening the gap.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))   # for _harness
sys.path.insert(0, str(HERE))          # for _importonce

from _harness.bench import measure, report  # noqa: E402

SETUP = f"""
import importlib, sys
sys.path.insert(0, {str(HERE)!r})
import _importonce                      # ensure it is loaded once
"""


def main() -> None:
    results = [
        measure("cached import (sys.modules)", "importlib.import_module('_importonce')", SETUP, number=200000),
        measure("reload (re-runs the body)", "importlib.reload(_importonce)", SETUP, number=2000),
    ]
    report("63.1  cached import vs re-executing the module body",
           results, baseline="cached import (sys.modules)")

    print()
    print("Reading this. A cached import is a sys.modules dict lookup returning the")
    print("existing module object, so it costs nanoseconds no matter how heavy the")
    print("module was to load. Re-running the body (reload) pays the full import-")
    print("time cost again. The lesson: a module's top-level code runs ONCE per")
    print("interpreter, so expensive one-time setup (compiling regexes, loading")
    print("data, building tables) belongs at module level, it is paid once and")
    print("every importer shares the result. Do not fear a costly import; fear")
    print("doing that work per call.")


if __name__ == "__main__":
    main()
