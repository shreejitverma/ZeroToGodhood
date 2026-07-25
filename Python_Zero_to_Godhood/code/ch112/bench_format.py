"""Benchmark 112.1 - f-strings are the fastest way to build a string.

Building 'order-42' four ways: an f-string, str.format(), %-formatting, and manual
concatenation. The f-string compiles directly to formatting bytecode (no runtime
template parse, no method call), so it is the fastest; str.format() parses its
template and dispatches per call, so it is the slowest. This measures all four.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 5_000_000
SETUP = "name = 'order'; n = 42"


def main():
    print("=== 112.1  building 'order-42': f-string vs format vs % vs concat ===")
    print(provenance())
    print()

    t_f = min(timeit.repeat("f'{name}-{n}'", setup=SETUP, number=N, repeat=5)) / N
    t_fmt = min(timeit.repeat("'{}-{}'.format(name, n)", setup=SETUP, number=N, repeat=5)) / N
    t_pct = min(timeit.repeat("'%s-%s' % (name, n)", setup=SETUP, number=N, repeat=5)) / N
    t_cat = min(timeit.repeat("name + '-' + str(n)", setup=SETUP, number=N, repeat=5)) / N

    print(f"  f-string       f'{{name}}-{{n}}'      : {t_f * 1e9:5.1f} ns   1.0x")
    print(f"  str.format()   '{{}}-{{}}'.format(..) : {t_fmt * 1e9:5.1f} ns   {t_fmt / t_f:.1f}x")
    print(f"  %-formatting   '%s-%s' % (..)      : {t_pct * 1e9:5.1f} ns   {t_pct / t_f:.1f}x")
    print(f"  concatenation  name + '-' + str(n) : {t_cat * 1e9:5.1f} ns   {t_cat / t_f:.1f}x")

    print()
    print("Reading this. The f-string is fastest because the compiler turns it")
    print("directly into formatting bytecode: it parses the template ONCE, at")
    print("compile time, and emits the field conversions inline. str.format() carries")
    print("its template as a runtime string, parses it on every call, and dispatches")
    print("through a method, so it is the slowest here. %-formatting and manual")
    print("concatenation land in between. Prefer f-strings: they are the fastest and")
    print("the most readable. Reserve str.format() for templates chosen at runtime")
    print("(from config or i18n), where the template is not known at compile time.")


if __name__ == "__main__":
    main()
