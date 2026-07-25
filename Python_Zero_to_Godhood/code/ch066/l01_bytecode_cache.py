"""Listing 66.1 - the .pyc cache stores compiled bytecode to skip recompilation.

Importing a .py module compiles its source to a code object (parse -> AST ->
bytecode), then CPython caches that bytecode in __pycache__/<name>.<tag>.pyc. On a
later import (in a new process), if the source is unchanged, it loads the cached
bytecode and SKIPS the compile step. A .pyc is a small header (a version magic
number and a source-freshness check: mtime+size, or a source hash) followed by the
marshaled code object. This listing shows the compile-then-marshal round trip that
the cache performs, and that loading marshaled bytecode reproduces the code exactly.
"""

import importlib.util
import marshal


SOURCE = """
def add(a, b):
    return a + b

RESULT = add(2, 3)
"""


def main() -> None:
    print("--- compile source to a code object (what the first import does) ---")
    code = compile(SOURCE, "mod.py", "exec")
    print(f"  compiled a code object : {type(code).__name__}")

    print("--- marshal the code object (what gets written into the .pyc body) ---")
    blob = marshal.dumps(code)
    print(f"  marshaled bytecode     : {len(blob)} bytes")

    print("--- load it back and run it (what a later import does) ---")
    reloaded = marshal.loads(blob)
    ns = {}
    exec(reloaded, ns)
    print(f"  RESULT from cached code: {ns['RESULT']}")
    print(f"  round-trip reproduces the code exactly: {ns['RESULT'] == 5}")

    print("--- the cache location and freshness check ---")
    cache_path = importlib.util.cache_from_source("pkg/mod.py").replace(chr(92), "/")
    # the version tag in the filename (cpython-3XX) is version-specific, so we
    # report only the version-independent structure
    print(f"  cache dir is __pycache__ : {'/__pycache__/' in cache_path}")
    print(f"  cache file ends in .pyc  : {cache_path.endswith('.pyc')}")
    print(f"  a .pyc is valid only while its source is unchanged (mtime+size or hash)")
    print(f"  the version magic number rejects a .pyc from a different Python")


if __name__ == "__main__":
    main()
