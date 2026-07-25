"""Benchmark 135.1 - the code object is compiled once and reused; recompiling is costly.

`def` compiles a function to a code object ONCE, and every call reuses that compiled
artifact, it does not re-parse or re-compile the source. This measures the cost of
that reuse: executing a pre-compiled code object many times versus recompiling the
same source on every execution (what you pay if you do NOT keep the code object). The
pre-compiled version is much faster, which is why CPython caches the compiled form.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 100_000
SRC = "total = 0\nfor i in range(100):\n    total += i * i"


def main():
    print("=== 135.1  exec a pre-compiled code object vs recompiling the source ===")
    print(provenance())
    print()

    code = compile(SRC, "<bench>", "exec")            # compiled ONCE

    t_precompiled = min(timeit.repeat(lambda: exec(code, {}), number=N, repeat=5)) / N
    t_recompile = min(
        timeit.repeat(lambda: exec(compile(SRC, "<bench>", "exec"), {}), number=N, repeat=5)
    ) / N

    print(f"  exec(pre-compiled code object) : {t_precompiled * 1e6:5.1f} us   1.0x")
    print(f"  exec(compile(src) each time)   : {t_recompile * 1e6:5.1f} us   {t_recompile / t_precompiled:.1f}x")

    print()
    print("Reading this. Executing a code object that was compiled once is several")
    print("times faster than recompiling the source on every run, because compilation")
    print("(lex, parse, build the AST, emit bytecode) is real work. This is exactly")
    print("what `def` does for you: it compiles the function body ONCE into a code")
    print("object (func.__code__) and every call reuses it, so you pay compilation at")
    print("import time, not per call. The .pyc bytecode cache (the import system)")
    print("extends this across runs, caching the compiled module so even the first")
    print("call of the next process skips compilation. The lesson: compilation is")
    print("amortized. Never compile in a hot loop (a needless compile() or exec of a")
    print("source string per iteration); compile once, run many.")


if __name__ == "__main__":
    main()
