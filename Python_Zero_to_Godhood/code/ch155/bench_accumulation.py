"""Benchmark 155.1 - join beats += for building strings, and reliably so.

Building a string of 50,000 pieces three ways: += in a loop (grows an immutable string
repeatedly), a list of pieces then ''.join, and ''.join over a generator. join computes
the total size and allocates the result once, so it is faster, and, unlike +=, it does
not rely on CPython's fragile in-place-concatenation optimization (which can degrade to
quadratic on other implementations or when the string has extra references).

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 50_000


def concat():
    s = ""
    for _ in range(N):
        s += "x"
    return s


def list_join():
    parts = []
    for _ in range(N):
        parts.append("x")
    return "".join(parts)


def genexpr_join():
    return "".join("x" for _ in range(N))


def main():
    print(f"=== 155.1  build a {N:,}-piece string: += vs list+join vs genexpr join ===")
    print(provenance())
    print()

    t_concat = min(timeit.repeat(concat, number=100, repeat=5)) / 100
    t_list = min(timeit.repeat(list_join, number=100, repeat=5)) / 100
    t_gen = min(timeit.repeat(genexpr_join, number=100, repeat=5)) / 100

    print(f"  += in a loop        : {t_concat * 1e3:5.2f} ms   {t_concat / t_list:.1f}x")
    print(f"  list + ''.join      : {t_list * 1e3:5.2f} ms   1.0x")
    print(f"  ''.join(genexpr)    : {t_gen * 1e3:5.2f} ms   {t_gen / t_list:.1f}x")

    print()
    print("Reading this. ''.join over a list is the fastest and the reliable choice.")
    print("It computes the total length up front and allocates the result string ONCE,")
    print("then copies each piece in. The += loop grows an immutable string repeatedly:")
    print("CPython softens this with an in-place-resize optimization (so it is not the")
    print("quadratic disaster it is on other implementations), but it is still slower")
    print("here and it is FRAGILE, it degrades to O(n^2) if the string has another")
    print("reference, and it does not exist on PyPy or in older Python. So the portable,")
    print("reliably-fast rule is: build strings with ''.join(list_of_pieces), never with")
    print("+= in a loop. This is the general immutability pattern: accumulate in a")
    print("MUTABLE container (a list, a bytearray) and materialize the IMMUTABLE result")
    print("(str, bytes, tuple) exactly once at the end, so you allocate once instead of")
    print("rebuilding on every step.")


if __name__ == "__main__":
    main()
