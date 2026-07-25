"""Benchmark 137.1 - a folded constant is a single load; a runtime computation is not.

Because the compiler folds `60 * 60 * 24` to the constant 86400 (Listing 137.1), a loop
containing that expression does one LOAD_CONST per iteration. The same value computed
from VARIABLES (a * b * c) cannot be folded, so it does the multiplications every
iteration. This measures both, to show that folding makes readable constant expressions
free, while variable computations in a loop run live (and should be hoisted if invariant).

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 20_000
LOOP = 1000


def folded():
    s = 0
    for _ in range(LOOP):
        s += 60 * 60 * 24          # compile-time folded to LOAD_CONST 86400
    return s


def runtime_compute():
    a, b, c = 60, 60, 24
    s = 0
    for _ in range(LOOP):
        s += a * b * c             # variables: two multiplies every iteration
    return s


def main():
    print("=== 137.1  folded constant vs runtime computation in a loop ===")
    print(provenance())
    print()

    t_folded = min(timeit.repeat(folded, number=N, repeat=5)) / N
    t_runtime = min(timeit.repeat(runtime_compute, number=N, repeat=5)) / N

    print(f"  folded constant (60*60*24)  : {t_folded * 1e6:5.1f} us   1.0x")
    print(f"  runtime compute (a*b*c)     : {t_runtime * 1e6:5.1f} us   {t_runtime / t_folded:.2f}x")

    print()
    print("Reading this. The folded loop just loads the pre-computed 86400 each")
    print("iteration; the variable loop does two multiplications each time, so it is")
    print("~1.7x slower. Two lessons. First, write CONSTANT expressions for clarity")
    print("without fear: 60 * 60 * 24 is exactly as fast as the opaque literal 86400,")
    print("the compiler folds it, so 'seconds per day' beats a magic number at no")
    print("cost. Second, folding only applies to constants; an invariant computation")
    print("involving VARIABLES is NOT folded and runs every iteration, so if it does")
    print("not change in the loop, HOIST it out yourself (compute once before the")
    print("loop). The compiler optimizes constants; loop-invariant variable code is")
    print("still your responsibility.")


if __name__ == "__main__":
    main()
