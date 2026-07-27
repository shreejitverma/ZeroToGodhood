"""Listing 154.1 - zero-cost exceptions: a try block is free when nothing is raised.

Since Python 3.11, exception handling is 'zero-cost': a try block that does NOT raise adds
essentially no runtime overhead (the benchmark measures ~1.0x). The mechanism is visible
in the code object: the exception-handling information lives in a separate, OUT-OF-LINE
table (co_exceptiontable), NOT as inline setup/teardown bytecode. So on the happy path
(no exception), the interpreter runs the try body's bytecode with no extra work; the
table is consulted ONLY when an exception actually propagates. This validates the
Pythonic EAFP style (Easier to Ask Forgiveness than Permission): wrap the normal case in
try/except freely. But RAISING is still costly, so exceptions are for exceptional cases,
not hot-loop control flow. This listing shows the out-of-line table, deterministically.
"""


def with_try():
    try:
        return 1
    except ValueError:
        return 2


def plain():
    return 1


def main() -> None:
    print("--- the exception info is OUT-OF-LINE, not inline bytecode ---")
    print(f"  a try function has a co_exceptiontable : {len(with_try.__code__.co_exceptiontable) > 0}")
    print(f"  a plain function's is empty            : {len(plain.__code__.co_exceptiontable) == 0}")
    print(f"  so the try body runs with no inline setup/teardown overhead")

    print("--- the try body runs normally when nothing is raised ---")
    print(f"  with_try() returns : {with_try()}   (the try path, no exception)")

    print("--- EAFP: try the operation, handle the rare failure ---")
    d = {"a": 1}
    def eafp_get(key):
        try:
            return d[key]                # assume it is there (the common case)
        except KeyError:
            return None                  # handle the rare miss
    print(f"  eafp_get('a') (hit)  : {eafp_get('a')}")
    print(f"  eafp_get('z') (miss) : {eafp_get('z')}")
    print(f"  the try/except is free on the hit path (zero-cost)")

    print("--- but RAISING is costly: exceptions are for exceptional cases ---")
    print(f"  raising + catching does real work (unwind, build the exception),")
    print(f"  so do NOT use exceptions as control flow in a hot loop (the benchmark)")

    print("--- the rule ---")
    print(f"  a try block is free when nothing raises (out-of-line table), so use EAFP")
    print(f"  freely; but raising is costly, reserve exceptions for the exceptional")


if __name__ == "__main__":
    main()
