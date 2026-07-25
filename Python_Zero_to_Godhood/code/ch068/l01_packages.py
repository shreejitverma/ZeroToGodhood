"""Listing 68.1 - regular packages vs namespace packages (PEP 420).

A regular package is a directory with an __init__.py: it has a single root, its
__init__ runs on import (a place for package-level setup), and __path__ is one
directory. A namespace package (PEP 420) is a directory WITHOUT __init__.py, and
it can be SPLIT across several sys.path roots: Python merges all the matching
directories into one package whose __path__ spans them. Namespace packages are how
a single import name (e.g. a plugin namespace) is assembled from independently-
installed pieces. This listing shows both, assembled from prepared directories.

rootA/nspkg/part_a.py and rootB/nspkg/part_b.py: one namespace package, two roots.
regpkg/__init__.py + regpkg/sub.py: one regular package, one root.
"""

import builtins
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "rootA"))
sys.path.insert(0, str(HERE / "rootB"))
sys.path.insert(0, str(HERE))


def main() -> None:
    print("--- namespace package: one name, split across two sys.path roots ---")
    import nspkg.part_a
    import nspkg.part_b
    print(f"  part from rootA        : {nspkg.part_a.PART}")
    print(f"  part from rootB        : {nspkg.part_b.PART}")
    print(f"  __path__ spans N roots : {len(list(nspkg.__path__))}")
    print(f"  no __init__.py (__file__ is None): {nspkg.__file__ is None}")

    print("--- regular package: single root, __init__.py runs on import ---")
    import regpkg
    import regpkg.sub  # noqa: F401
    print(f"  __init__ ran           : {getattr(builtins, '_regpkg_init_ran', False)}")
    print(f"  __file__ is the __init__.py : {regpkg.__file__.endswith('__init__.py')}")
    print(f"  __path__ is a plain list    : {type(regpkg.__path__).__name__ == 'list'}")

    print("--- the difference ---")
    print(f"  namespace: no __init__, spans roots (plugins/split distributions)")
    print(f"  regular:   __init__ runs setup, single root (the normal default)")


if __name__ == "__main__":
    main()
