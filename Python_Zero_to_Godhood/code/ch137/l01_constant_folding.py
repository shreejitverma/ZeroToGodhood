"""Listing 137.1 - constant folding: the compiler pre-computes constant expressions.

Before it emits bytecode, CPython's compiler evaluates expressions made entirely of
CONSTANTS and stores the RESULT, so at runtime there is nothing to compute, just a
LOAD_CONST. `60 * 60 * 24` becomes the constant 86400; `"ab" * 3` becomes "ababab";
`(1, 2, 3)` becomes one constant tuple. This is a COMPILE-time optimization (distinct
from the runtime specializing interpreter): it happens once, when the function is
compiled. The practical payoff is that you can write a readable constant expression
(60 * 60 * 24, not the magic number 86400) for FREE. But it applies only to constants:
an expression involving a VARIABLE is computed at runtime. This listing shows both,
via version-stable co_consts membership.
"""


def seconds_per_day():
    return 60 * 60 * 24                   # folded to 86400 at compile time


def repeated_str():
    return "ab" * 3                       # folded to "ababab"


def const_tuple():
    return (1, 2, 3)                      # folded to a single constant tuple


def with_variable(x):
    return x * 60 * 60                    # x is a variable -> the x* part runs at runtime


def main() -> None:
    print("--- arithmetic on constants is folded to the result ---")
    print(f"  86400 is in seconds_per_day's co_consts : {86400 in seconds_per_day.__code__.co_consts}")
    print(f"  seconds_per_day() == 86400              : {seconds_per_day() == 86400}")

    print("--- string and tuple constants are folded too ---")
    print(f"  'ababab' in repeated_str's co_consts    : {'ababab' in repeated_str.__code__.co_consts}")
    print(f"  (1, 2, 3) in const_tuple's co_consts    : {(1, 2, 3) in const_tuple.__code__.co_consts}")

    print("--- but an expression with a VARIABLE is not fully folded ---")
    print(f"  with_variable still references 60 (runtime multiply) : "
          f"{60 in with_variable.__code__.co_consts or 3600 in with_variable.__code__.co_consts}")
    print(f"  with_variable(2) == 7200                : {with_variable(2) == 7200}")

    print("--- the rule ---")
    print(f"  the compiler folds constant expressions to their result (free at")
    print(f"  runtime); write readable constant expressions, only variables run live")


if __name__ == "__main__":
    main()
