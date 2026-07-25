"""Benchmark 68.1 - namespace package resolution costs more than a regular one.

Resolving a submodule of a namespace package requires considering ALL the
directories that contribute to the package's __path__ (it may be split across
roots), whereas a regular package has a single __path__ root. This measures
find_spec for a namespace-package submodule versus a regular-package submodule, so
the extra resolution work of the split package is visible.

Does its own timing (it prepares sys.path), guarded by __main__. See
_harness/bench.py.
"""

import importlib
import importlib.util
import sys
import timeit
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))   # for _harness

from _harness.bench import provenance  # noqa: E402


def main():
    print("=== 68.1  namespace vs regular package submodule resolution ===")
    print(provenance())
    print()

    sys.path.insert(0, str(HERE / "rootA"))
    sys.path.insert(0, str(HERE / "rootB"))
    sys.path.insert(0, str(HERE))
    importlib.invalidate_caches()

    n = 50000
    ns = min(timeit.timeit(lambda: importlib.util.find_spec("nspkg.part_a"), number=n) for _ in range(3)) / n * 1e9
    reg = min(timeit.timeit(lambda: importlib.util.find_spec("regpkg.sub"), number=n) for _ in range(3)) / n * 1e9

    print(f"  regular   submodule find_spec : {reg:>8,.0f} ns")
    print(f"  namespace submodule find_spec : {ns:>8,.0f} ns")
    print(f"  ratio                         : {ns / reg:>8.1f}x")

    print()
    print("Reading this. A regular package has one __path__ root, so resolving a")
    print("submodule checks one directory. A namespace package can be split across")
    print("roots, so resolving a submodule must consider all contributing")
    print("directories, which costs more. The difference is small in absolute terms")
    print("but real. Use a regular package (with __init__.py) as the default, it")
    print("also gives you a place for package setup; use a namespace package only")
    print("when you genuinely need one import name assembled from independently-")
    print("installed pieces (plugin namespaces, split distributions).")


if __name__ == "__main__":
    main()
