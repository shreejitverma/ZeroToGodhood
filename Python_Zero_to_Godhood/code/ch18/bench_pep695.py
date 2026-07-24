"""Benchmark 18.1 - what PEP 695 syntax costs at definition time.

The interesting result here is counterintuitive and worth stating plainly: the
PEP 695 generic class is *slower* to define than the legacy `Generic[T]` form,
because `class Box[T]` runs an extra compiler-generated function scope (the
`<generic parameters of Box>` scope in `l04_typeparam_scope.py`) before the
class body executes.

That is a real cost and the chapter should not hide it. It is also almost
always irrelevant: it is paid once per class definition, at import time, not
per instantiation. The measurement exists to size it, not to argue against the
syntax.

All comparisons are within a single interpreter. See `_harness/bench.py` for
why cross-build comparison is refused.

Run:  python3 ch18/bench_pep695.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP_695 = "src = compile('class Box[T]:\\n    pass\\n', '<b>', 'exec')"
SETUP_LEGACY = (
    "from typing import Generic, TypeVar\n"
    "T = TypeVar('T')\n"
    "src = compile('class Box(Generic[T]):\\n    pass\\n', '<b>', 'exec')"
)
SETUP_PLAIN = "src = compile('class Box:\\n    pass\\n', '<b>', 'exec')"

SETUP_ALIAS_695 = "src = compile('type A = list[int]', '<b>', 'exec')"
SETUP_ALIAS_EAGER = "src = compile('A = list[int]', '<b>', 'exec')"


def main() -> None:
    class_results = [
        measure("class Box:              (no generics)", "exec(src)", SETUP_PLAIN),
        measure("class Box(Generic[T]):  (legacy)     ", "exec(src)", SETUP_LEGACY),
        measure("class Box[T]:           (PEP 695)    ", "exec(src)", SETUP_695),
    ]
    report("18.1a  Generic class definition cost", class_results,
           baseline="class Box:              (no generics)")

    print()
    alias_results = [
        measure("A = list[int]      (eager assignment)", "exec(src)", SETUP_ALIAS_EAGER),
        measure("type A = list[int] (PEP 695, lazy)   ", "exec(src)", SETUP_ALIAS_695),
    ]
    report("18.1b  Type alias definition cost", alias_results,
           baseline="A = list[int]      (eager assignment)")

    print()
    print("Reading these numbers")
    print("---------------------")
    print("18.1a: the PEP 695 form costs more at definition time than Generic[T],")
    print("       because it runs an extra function scope to build the type params.")
    print("       Paid once per class, at import. Not per instantiation.")
    print("18.1b: for a trivial value the two alias forms are close, because the")
    print("       lazy scope's saving is proportional to how expensive the value is.")
    print("       The `type` statement wins when the value is costly or unresolvable")
    print("       at definition time, not when it is `list[int]`.")


if __name__ == "__main__":
    main()
