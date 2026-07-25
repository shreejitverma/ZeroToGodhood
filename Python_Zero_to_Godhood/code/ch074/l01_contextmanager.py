"""Listing 74.1 - @contextmanager: a generator IS a context manager.

contextlib.contextmanager turns a generator with exactly one yield into a context
manager. The code before the yield is __enter__ (setup); the yielded value is the
'as' target; the code after the yield is __exit__ (teardown). Crucially, if the
with-body raises, the exception is THROWN INTO the generator at the yield point, so
a try/finally runs cleanup, and a try/except can even SUPPRESS the exception by not
re-raising. This is generators used for control flow, not iteration. This listing
shows setup/teardown, exception cleanup, and suppression, recording events for
deterministic output.
"""

import contextlib


@contextlib.contextmanager
def managed(events, name):
    events.append(f"setup {name}")           # __enter__
    try:
        yield name                           # the 'as' value
    finally:
        events.append(f"teardown {name}")    # __exit__ (runs even on exception)


@contextlib.contextmanager
def suppressing(events):
    try:
        yield
    except ValueError:
        events.append("suppressed ValueError")   # swallow it: the with-block does not raise


def main() -> None:
    print("--- setup runs, body runs, teardown runs (the yield splits them) ---")
    ev = []
    with managed(ev, "db") as r:
        ev.append(f"body uses {r}")
    print(f"  events : {ev}")

    print("--- an exception in the body is thrown into the generator; finally runs ---")
    ev = []
    try:
        with managed(ev, "file"):
            ev.append("body raises")
            raise ValueError("boom")
    except ValueError:
        ev.append("caught outside")
    print(f"  events : {ev}")

    print("--- a context manager can SUPPRESS the exception (not re-raise) ---")
    ev = []
    with suppressing(ev):
        ev.append("body raises")
        raise ValueError("handled inside")
    ev.append("execution continued past the with")
    print(f"  events : {ev}")


if __name__ == "__main__":
    main()
