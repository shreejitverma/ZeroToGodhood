"""Benchmark 66.1 - loading cached bytecode is far cheaper than compiling source.

The .pyc cache exists because compiling source (parse -> AST -> bytecode) is
expensive, and it only needs to happen when the source changes. This measures
compiling a chunky module's source versus marshal.loads of the already-compiled
code object (which is what loading a .pyc does after reading its header). The gap
is what the cache saves on every import after the first.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import marshal, textwrap
src = textwrap.dedent('''
def f(x):
    total = 0
    for i in range(x):
        total += i * i
    return total
class C:
    def __init__(self, a, b):
        self.a = a
        self.b = b
    def method(self):
        return self.a + self.b
''') * 50
code = compile(src, "<m>", "exec")
blob = marshal.dumps(code)
"""


def main() -> None:
    results = [
        measure("marshal.loads (.pyc)", "marshal.loads(blob)", SETUP, number=2000),
        measure("compile source", "compile(src, '<m>', 'exec')", SETUP, number=2000),
    ]
    report("66.1  loading cached bytecode vs compiling source",
           results, baseline="marshal.loads (.pyc)")

    print()
    print("Reading this. Compiling source into a code object parses the text,")
    print("builds an AST, and emits bytecode, expensive work. Loading the already-")
    print("compiled code (marshal.loads, what reading a .pyc does) skips all of")
    print("that and is far cheaper. That is why CPython caches bytecode in")
    print("__pycache__: the compile happens on the first import (or when the source")
    print("changes), and every later import in a fresh process loads the .pyc")
    print("instead. Ship .pyc files (or precompile with compileall) to avoid paying")
    print("first-import compilation in production; never edit a .pyc by hand.")


if __name__ == "__main__":
    main()
