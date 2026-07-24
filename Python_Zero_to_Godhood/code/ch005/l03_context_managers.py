"""Listing 5.3 - the context-manager protocol: guaranteed cleanup, and the
power to suppress.

__enter__ acquires and returns the `as` target; __exit__ releases and runs on
every exit path. __exit__ sees the exception (or three Nones on a clean exit)
and can suppress it by returning a truthy value. This is Python's deterministic-
cleanup primitive: RAII built on a guaranteed try/finally.
"""


class Ctx:
    def __enter__(self):
        print("  __enter__")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("  __exit__ exc_type =", exc_type.__name__ if exc_type else None)
        return exc_type is ValueError      # suppress only ValueError


print("--- clean exit: __exit__ sees three Nones ---")
with Ctx() as c:
    print("  body (clean)")
print("clean exit done")

print()
print("--- exception exit: __exit__ sees it and suppresses ValueError ---")
with Ctx():
    print("  body raising ValueError")
    raise ValueError("boom")
print("ValueError was suppressed by __exit__ returning truthy")

print()
print("--- a generator-based context manager: before yield is enter, finally is exit ---")
import contextlib


@contextlib.contextmanager
def managed():
    print("  acquire")
    try:
        yield 42
    finally:
        print("  release")


with managed() as v:
    print("  using", v)
