"""Benchmark 49.1 - inspect.signature is rich and expensive; cache it.

Three ways to learn about a function's parameters, at three costs:
  raw __code__.co_varnames : reading a tuple attribute (cheap, unstructured)
  cached signature access  : reading .parameters off a Signature built once
  inspect.signature(f)     : building a fresh Signature object every call

inspect.signature builds a full Signature/Parameter object model (kinds,
defaults, annotations) each call, so calling it per request in a framework is
far more expensive than caching it once. This measures the gap.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import inspect
def f(a, b, c=3, *args, **kwargs):
    pass
cached_sig = inspect.signature(f)
"""


def main() -> None:
    results = [
        measure("raw __code__.co_varnames", "f.__code__.co_varnames", SETUP, number=100000),
        measure("cached signature .parameters", "cached_sig.parameters", SETUP, number=100000),
        measure("inspect.signature(f)", "inspect.signature(f)", SETUP, number=20000),
    ]
    report("49.1  three ways to introspect a function's parameters",
           results, baseline="raw __code__.co_varnames")

    print()
    print("Reading this. Reading __code__.co_varnames is a tuple attribute access,")
    print("the cheapest. inspect.signature builds a fresh Signature object every")
    print("call, parsing kinds, defaults, and annotations into Parameter objects,")
    print("so it is orders of magnitude more expensive. A cached Signature's")
    print(".parameters is cheap again. If a framework reflects a function on every")
    print("request (dependency injection, validation, CLI dispatch), build the")
    print("Signature once and cache it; never call inspect.signature in a hot loop.")


if __name__ == "__main__":
    main()
