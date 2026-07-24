"""Benchmark 12.1 - f-strings are fast, but the folklore has two holes.

Two claims get tested. First, that f-strings are "the fastest interpolation":
true for plain substitution, less clear-cut with a numeric format spec. Second,
the logging anti-pattern: an f-string formats EAGERLY, so logging an f-string at
a suppressed level does the formatting work and throws it away, while the %-args
form defers formatting until the level check passes.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402


def main() -> None:
    plain = [
        measure("f-string  ", "for _ in range(1000): f'{x} {y}'", "x, y = 'a', 42", number=1000),
        measure("%-format  ", "for _ in range(1000): '%s %s' % (x, y)", "x, y = 'a', 42", number=1000),
        measure(".format   ", "for _ in range(1000): '{} {}'.format(x, y)", "x, y = 'a', 42", number=1000),
    ]
    report("12.1a  plain substitution: f-string wins", plain, baseline="f-string  ")

    print()
    spec = [
        measure("f-string  ", "for _ in range(1000): f'{x:.2f}'", "x = 3.14159", number=1000),
        measure("%-format  ", "for _ in range(1000): '%.2f' % x", "x = 3.14159", number=1000),
    ]
    report("12.1b  with a numeric spec: the gap closes, %-format edges ahead",
           spec, baseline="f-string  ")

    print()
    # The interpolation is a repr() of a large structure: expensive, and under the
    # f-string it runs unconditionally even though the message is discarded.
    log_setup = ("import logging; logging.disable(logging.CRITICAL);"
                 " log = logging.getLogger(); big = list(range(1000))")
    logging_cases = [
        measure("lazy %-args    ", "for _ in range(100): log.info('data=%r', big)", log_setup, number=1000),
        measure("eager f-string ", "for _ in range(100): log.info(f'data={big!r}')", log_setup, number=1000),
    ]
    report("12.1c  logging a suppressed message with EXPENSIVE interpolation",
           logging_cases, baseline="lazy %-args    ")

    print()
    print("Reading all three. For plain substitution the f-string is fastest, as")
    print("advertised (12.1a). With a numeric format spec the spec application")
    print("dominates and the syntaxes converge (12.1b), so 'f-strings are always")
    print("fastest' is overstated. 12.1c is the one that matters in production:")
    print("logging an f-string at a disabled level runs the interpolation and")
    print("throws it away. For a trivial value that is a few percent; for an")
    print("expensive repr() of a large object it is the full cost, done for")
    print("nothing, because the %-args form defers formatting until the level")
    print("check passes. Use logging('...%s', x), never logging(f'...').")


if __name__ == "__main__":
    main()
