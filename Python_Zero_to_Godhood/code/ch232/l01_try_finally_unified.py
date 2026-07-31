"""Listing 232.1 - Python 2.5 (2006): try/except/finally unified into one statement.

Before 2.5 a single `try` could have `except` clauses OR a `finally`, but NOT
both. To do both - handle some errors AND guarantee cleanup - you nested one
try inside another, an awkward two-level shape everyone wrote and no one liked.
Python 2.5 unified them: one try may carry except, else, and finally together.
This chapter shows the unified statement and the exact guarantee each clause
gives - especially finally, which runs whether the try succeeds, raises, is
handled, or even returns. That guarantee is what `with` (Chapter 5) automates,
and why cleanup you must not skip goes in finally, not after the block. Deep B
owns exception unwinding; this is the release that made the four-part try one
statement. Verified on current interpreters.
"""


def divide(a, b):
    """One try with except + else + finally - impossible before 2.5."""
    log = []
    try:
        result = a / b
    except ZeroDivisionError:
        log.append("except: caught division by zero")
        result = None
    else:
        log.append("else: ran because no exception was raised")
    finally:
        log.append("finally: always runs (cleanup goes here)")
    return result, log


def main() -> None:
    print("--- one try, all four clauses: the 2.5 unification ---")
    ok, ok_log = divide(10, 2)
    print(f"  divide(10, 2) -> {ok}")
    for line in ok_log:
        print(f"    {line}")
    print("  except + else + finally in ONE try - before 2.5 you nested a")
    print("  try/except inside a try/finally to get both. now it is one")
    print("  statement with four roles, each with a precise trigger")

    print("--- the error path: except fires, else is skipped, finally still runs ---")
    bad, bad_log = divide(10, 0)
    print(f"  divide(10, 0) -> {bad}")
    for line in bad_log:
        print(f"    {line}")
    print("  raise -> except runs, else is SKIPPED, finally runs anyway. `else`")
    print("  is the 'only if no exception' clause; `finally` is the 'no matter")
    print("  what' clause. the two are not redundant - they trigger oppositely")

    print("--- finally runs even when the try RETURNS or RE-RAISES ---")
    def with_return():
        try:
            return "returned from try"          # finally still runs first
        finally:
            print("    finally: ran before the return completed")
    print(f"  return inside try: {with_return()}")

    def reraises():
        try:
            raise ValueError("boom")
        finally:
            print("    finally: ran while the exception was propagating")
    try:
        reraises()
    except ValueError as exc:
        print(f"  uncaught error still propagated after finally : {exc}")
    print("  finally is the strongest guarantee in the language: it runs on")
    print("  success, on a handled error, on an UNhandled error, and even as a")
    print("  return or raise leaves the block. that is why cleanup lives there")

    print("--- why it matters: cleanup after the block is NOT safe ---")
    print("  f = open(...); work(); f.close()   # close SKIPPED if work() raises")
    print("  try: work() finally: f.close()      # close ALWAYS runs")
    print("  putting f.close() after the block skips it on any error; putting")
    print("  it in finally guarantees it. `with` (Chapter 5) is exactly this")
    print("  finally-guarantee packaged so you cannot forget it")

    print("--- the constraint answered ---")
    print("  pre-2.5, a try had except OR finally, never both, so 'handle some")
    print("  errors AND always clean up' meant nesting two trys. 2.5 unified")
    print("  them into one four-clause statement: try/except/else/finally, each")
    print("  clause a precise guarantee - the foundation `with` builds on")


if __name__ == "__main__":
    main()
