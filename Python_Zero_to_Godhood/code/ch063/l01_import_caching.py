"""Listing 63.1 - import runs a module's body once; after that it is a cache hit.

`import X` does not "run X.py"; it ensures X is in sys.modules, executing its body
ONLY if it is not already there. So a module's top-level code is a one-time
initializer: expensive import-time work (building tables, loading data) is paid
once, and every later `import` of the same module is a dict lookup returning the
same module object. importlib.reload is the only way to re-run the body. This
listing proves it with a load counter that the helper increments each time its
body actually runs.
"""

import builtins
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    print("--- first import runs the body ---")
    import _importonce
    print(f"  body executions so far : {builtins._importonce_loads}")
    print(f"  in sys.modules         : {'_importonce' in sys.modules}")
    print(f"  TOTAL computed at import: {_importonce.TOTAL}")

    print("--- repeated imports are cache hits: the body does NOT re-run ---")
    import _importonce as again
    mod = importlib.import_module("_importonce")
    print(f"  same module object     : {again is _importonce is mod}")
    print(f"  body executions so far : {builtins._importonce_loads} (still 1)")

    print("--- reload is the only way to re-run the body ---")
    importlib.reload(_importonce)
    print(f"  body executions so far : {builtins._importonce_loads} (now 2)")
    print(f"  a cached import is a sys.modules lookup; the body cost is paid once")


if __name__ == "__main__":
    main()
