"""Listing 136.1 - every call creates a frame: recursion, independent locals, the limit.

Chapter 54 introduced the frame as one call's runtime state. This listing shows the
consequence: EVERY function call creates a NEW frame (pushed onto the call stack), and
each frame has its OWN local variables. That is why recursion works, each recursive
call gets an independent frame with its own copy of the parameters, and why the call
stack has a depth LIMIT (sys.getrecursionlimit), each frame consumes memory and C-stack,
so unbounded recursion raises RecursionError rather than crashing. Frame creation is
also why a function call is not free (the benchmark). This listing measures frame depth
directly, deterministically.
"""

import sys


def stack_depth():
    """Count frames from here up to the top (the length of the f_back chain)."""
    depth = 0
    frame = sys._getframe()
    while frame is not None:
        depth += 1
        frame = frame.f_back
    return depth


def recurse(n, base_depth):
    if n == 0:
        return stack_depth() - base_depth   # extra frames created by the recursion
    return recurse(n - 1, base_depth)


def factorial(n):
    # each call has its OWN n (independent frame locals); that is why recursion works
    return 1 if n <= 1 else n * factorial(n - 1)


def main() -> None:
    print("--- every call pushes a NEW frame; recursion stacks them ---")
    base = stack_depth()
    extra = recurse(5, base)                 # recurse(5) -> frames for n=5,4,3,2,1,0
    print(f"  recurse(5) created this many extra frames : {extra}   (n=5..0 plus the counter)")

    print("--- each frame has its OWN locals: recursion computes correctly ---")
    print(f"  factorial(5) : {factorial(5)}   (each call's n is independent)")

    print("--- the call stack has a depth LIMIT (frames cost memory + C stack) ---")
    print(f"  sys.getrecursionlimit() is positive : {sys.getrecursionlimit() > 0}")

    print("--- unbounded recursion raises RecursionError, not a crash ---")
    def forever(n):
        return forever(n + 1)
    try:
        forever(0)
    except RecursionError:
        print(f"  deep recursion raised RecursionError (caught, no crash) : True")

    print("--- the rule ---")
    print(f"  every call creates a frame with its own locals; that enables recursion")
    print(f"  and closures, bounds depth (RecursionError), and makes calls non-free")


if __name__ == "__main__":
    main()
