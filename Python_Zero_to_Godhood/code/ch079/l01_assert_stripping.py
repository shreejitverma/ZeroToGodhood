"""Listing 79.1 - assert is stripped under -O: never use it for validation.

An assert statement is compiled to a check only when __debug__ is True, which is
the default but is FALSE when Python runs with -O (optimized mode, common in
production). Under -O, every assert is removed entirely, so a validation or
security check written as `assert ...` silently vanishes, and the bad input sails
through. assert is for INTERNAL INVARIANTS you check while developing (documenting
"this can't happen"), not for validating inputs or enforcing security. Those must
be explicit `if ...: raise`, which runs in every mode. This listing runs a check
both normally and under -O to show the difference.
"""

import subprocess
import sys

CHECK = """
def validate(age):
    assert age >= 0, "assert-based check"      # stripped under -O
    return age

def validate_ok(age):
    if age < 0:                                # explicit check, always runs
        raise ValueError("if-based check")
    return age

import sys
try:
    validate(-5)
    print("  assert check: NOT triggered (age -5 accepted!)")
except AssertionError:
    print("  assert check: triggered (AssertionError)")

try:
    validate_ok(-5)
    print("  if check: NOT triggered")
except ValueError:
    print("  if check: triggered (ValueError)")

print(f"  __debug__ = {__debug__}")
"""


def run(flag):
    args = [sys.executable] + flag + ["-c", CHECK]
    return subprocess.run(args, capture_output=True, text=True).stdout


def main() -> None:
    print("--- normal mode (__debug__ True): both checks run ---")
    print(run([]), end="")

    print("--- optimized mode (python -O): the assert is STRIPPED ---")
    print(run(["-O"]), end="")

    print("--- the rule ---")
    print("  assert: internal invariants / debugging assumptions (may be stripped)")
    print("  if ...: raise: input validation and security checks (always run)")


if __name__ == "__main__":
    main()
