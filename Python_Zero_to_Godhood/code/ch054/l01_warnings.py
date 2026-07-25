"""Listing 54.1 - warnings: filters decide what is shown, raised, or silenced.

warnings.warn emits a warning; a filter decides what happens to it: shown once,
shown always, silenced, or turned into an exception. Two facts surprise people.
First, DeprecationWarning is IGNORED by default in normal execution, so a
library's deprecations are invisible to end users (they show only under -W or in
test runners). Second, simplefilter('error') turns warnings into raised
exceptions, which is how you make deprecations FAIL a test suite. This listing
demonstrates the filter actions deterministically with catch_warnings(record=True).
"""

import warnings


def emit_twice(category):
    warnings.warn("something", category)
    warnings.warn("something", category)     # identical warning, same location


def main() -> None:
    print("--- 'always': every warning is recorded ---")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        emit_twice(UserWarning)
    print(f"  two identical warns -> recorded: {len(caught)}")

    print("--- 'once': duplicates are deduplicated ---")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("once")
        emit_twice(UserWarning)
    print(f"  two identical warns -> recorded: {len(caught)}")

    print("--- 'ignore': silenced entirely ---")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("ignore")
        emit_twice(UserWarning)
    print(f"  two identical warns -> recorded: {len(caught)}")

    print("--- 'error': a warning becomes a raised exception ---")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            warnings.warn("deprecated!", DeprecationWarning)
            raised = None
        except DeprecationWarning as e:
            raised = type(e).__name__
    print(f"  warn under 'error' -> raised: {raised}")
    print(f"  (run tests with -W error to make silent deprecations fail)")


if __name__ == "__main__":
    main()
