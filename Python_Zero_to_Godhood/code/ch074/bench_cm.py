"""Benchmark 74.1 - @contextmanager is more concise but slower than a class.

Both wrap a with-block with setup/teardown. The class implements __enter__/__exit__
directly; @contextmanager wraps a generator in a _GeneratorContextManager and drives
it with next()/throw() on enter/exit. So the generator form pays generator-machinery
overhead per use. This measures entering and exiting each form (empty body).

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import contextlib

@contextlib.contextmanager
def gen_cm():
    yield "r"

class ClassCM:
    def __enter__(self):
        return "r"
    def __exit__(self, *exc):
        return False

def use_gen():
    with gen_cm() as r:
        pass

def use_class():
    with ClassCM() as r:
        pass
"""


def main() -> None:
    results = [
        measure("class __enter__/__exit__", "use_class()", SETUP, number=200000),
        measure("@contextmanager generator", "use_gen()", SETUP, number=200000),
    ]
    report("74.1  entering/exiting a context manager: class vs @contextmanager",
           results, baseline="class __enter__/__exit__")

    print()
    print("Reading this. The class implements __enter__/__exit__ directly; the")
    print("@contextmanager form drives a generator (next() to enter, throw()/next()")
    print("to exit) wrapped in a helper object, so it costs more per use. The gap is")
    print("a few hundred nanoseconds, negligible when the with-block does real work")
    print("(open a file, hold a lock, start a transaction). Prefer @contextmanager")
    print("for its conciseness (setup/teardown in one readable function); reach for")
    print("a class only when entering the context is itself on a hot path, or the")
    print("context manager needs to be a rich reusable object.")


if __name__ == "__main__":
    main()
