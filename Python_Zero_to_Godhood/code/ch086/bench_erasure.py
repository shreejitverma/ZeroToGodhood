"""Benchmark 86.1 - annotations are free (unchecked); real validation costs.

Because the runtime ignores annotations, an annotated function does NO type
checking, so the annotation adds zero runtime cost. If you need a runtime
guarantee, you write an explicit check (isinstance), which does cost. This
measures an annotated-but-unchecked function against one that validates its
argument, so the difference between "documented type" (free, unenforced) and
"checked type" (costs, enforced) is visible.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
def annotated(x: int) -> int:      # annotation ignored at runtime
    return x + 1

def validated(x):                  # explicit runtime check
    if not isinstance(x, int):
        raise TypeError(f"expected int, got {type(x).__name__}")
    return x + 1
"""


def main() -> None:
    results = [
        measure("annotated (unchecked)", "annotated(5)", SETUP, number=2000000),
        measure("validated (isinstance)", "validated(5)", SETUP, number=2000000),
    ]
    report("86.1  annotated-but-unchecked vs explicit runtime validation",
           results, baseline="annotated (unchecked)")

    print()
    print("Reading this. The annotated function does no type checking at all, its")
    print("annotation is metadata the interpreter ignores, so it costs the same as")
    print("an unannotated function. The validated function pays for an isinstance")
    print("check on every call. So annotations are FREE precisely because they are")
    print("not enforced; a runtime guarantee is a separate, explicit cost. Use")
    print("static type checking (mypy/pyright in CI) to catch type errors before")
    print("running for free at runtime, and add explicit validation only at trust")
    print("boundaries (external input), where you actually need a runtime guarantee.")


if __name__ == "__main__":
    main()
