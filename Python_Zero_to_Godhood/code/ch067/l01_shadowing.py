"""Listing 67.1 - sys.path is searched in order; the first match wins.

To import X, Python asks each finder on sys.meta_path; the path-based finder walks
sys.path IN ORDER and imports the FIRST directory that has an X. Crucially,
sys.path[0] is the directory of the script being run (or '' for the cwd in the
REPL), so a local file named like a standard-library module SHADOWS it: a file
called random.py or queue.py next to your script is imported instead of the
stdlib one, a classic and baffling bug. This listing shows the first-match-wins
mechanism and, safely (via find_spec, which locates without importing), how a
local file shadows a stdlib name.
"""

import importlib
import importlib.util
import sys
from pathlib import Path

SHADOWDIR = str(Path(__file__).resolve().parent / "shadowdir")


def main() -> None:
    print("--- first match wins: a directory earlier on sys.path shadows a later one ---")
    sys.path.insert(0, SHADOWDIR)
    importlib.invalidate_caches()
    import mymath
    print(f"  imported mymath from shadowdir : {'shadowdir' in mymath.__file__}")

    print("--- the trap: a local file named like a stdlib module (shown via find_spec) ---")
    # shadowdir is first, so 'queue' resolves to the LOCAL queue.py, not the stdlib
    shadowed = importlib.util.find_spec("queue")
    print(f"  with shadowdir first, 'queue' is local : {'shadowdir' in (shadowed.origin or '')}")

    print("--- remove the shadow directory: 'queue' resolves to the stdlib again ---")
    sys.path.remove(SHADOWDIR)
    importlib.invalidate_caches()
    real = importlib.util.find_spec("queue")
    print(f"  without shadowdir, 'queue' is stdlib   : {'shadowdir' not in (real.origin or '')}")
    print(f"  lesson: never name your file after a stdlib module (random, queue, email, string, ...)")


if __name__ == "__main__":
    main()
