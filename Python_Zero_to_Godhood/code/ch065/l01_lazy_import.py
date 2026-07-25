"""Listing 65.1 - lazy imports defer a module's load until it is actually used.

Every module imported at startup runs its body then (Chapter 63), so a program
that eagerly imports heavy modules pays their cost even when a given run never
uses them. A lazy import defers the load until first use. PEP 562 lets a PACKAGE
define module-level __getattr__, so `import pkg` is cheap and `pkg.heavy` triggers
the heavy submodule's import only on first access. This listing proves the heavy
submodule is NOT loaded until accessed, using a flag its body sets.
"""

import builtins
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def heavy_loaded():
    return getattr(builtins, "_lazypkg_heavy_loaded", False)


def main() -> None:
    print("--- importing the package does NOT load the heavy submodule ---")
    import _lazypkg
    print(f"  package imported     : {'_lazypkg' in sys.modules}")
    print(f"  heavy loaded yet?    : {heavy_loaded()}")
    print(f"  _lazypkg.heavy in sys.modules: {'_lazypkg.heavy' in sys.modules}")

    print("--- first access triggers the load (PEP 562 __getattr__) ---")
    data = _lazypkg.heavy.DATA
    print(f"  accessed _lazypkg.heavy.DATA[:1] : {data[:1]}")
    print(f"  heavy loaded now?    : {heavy_loaded()}")
    print(f"  _lazypkg.heavy in sys.modules    : {'_lazypkg.heavy' in sys.modules}")

    print("--- subsequent access is direct (cached; __getattr__ not called again) ---")
    print(f"  same module object   : {_lazypkg.heavy is sys.modules['_lazypkg.heavy']}")
    print(f"  a run that never touches .heavy pays nothing for it")


if __name__ == "__main__":
    main()
