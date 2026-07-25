"""Listing 52.1 - a disabled log call still evaluates its arguments.

Chapter 12 showed the lazy-% form log.debug("x=%s", x) avoids FORMATTING the
message when the level is disabled. But it does NOT avoid EVALUATING the
arguments: Python computes every argument before calling log.debug, so if an
argument is expensive to build, that cost is paid even when the message is
discarded. The fix for an expensive argument is to guard the whole call with
log.isEnabledFor(level). This listing proves the point with a side-effect
counter (deterministic), the benchmark shows what it costs.
"""

import logging

CALLS = {"expensive": 0}


def expensive():
    CALLS["expensive"] += 1          # a visible side effect: was this evaluated?
    return sum(i for i in range(1000))


def main() -> None:
    log = logging.getLogger("ch052")
    log.setLevel(logging.WARNING)    # DEBUG is DISABLED

    print("--- lazy-% form: message not formatted, but the ARGUMENT is evaluated ---")
    CALLS["expensive"] = 0
    for _ in range(5):
        log.debug("value=%s", expensive())     # nothing is logged (DEBUG off)...
    print(f"  expensive() called       : {CALLS['expensive']} times (though nothing was logged)")

    print("--- isEnabledFor guard: the argument is not evaluated at all ---")
    CALLS["expensive"] = 0
    for _ in range(5):
        if log.isEnabledFor(logging.DEBUG):
            log.debug("value=%s", expensive())
    print(f"  expensive() called       : {CALLS['expensive']} times (guard skipped it)")

    print("--- the guard only matters when the argument is EXPENSIVE ---")
    print(f"  cheap literal args need no guard (log.debug('hello') is already near-free)")
    print(f"  guard expensive-to-compute args; leave cheap ones to lazy-% (Chapter 12)")


if __name__ == "__main__":
    main()
