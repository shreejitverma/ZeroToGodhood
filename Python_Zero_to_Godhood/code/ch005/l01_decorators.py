"""Listing 5.1 - decorators are compile-time sugar for f = d(f), applied
bottom-up, and functools.wraps is not optional.

@d above def f means "after building f, replace it with d(f)." Stacked
decorators apply nearest-the-def first. A naive wrapper silently replaces the
function's identity; functools.wraps copies it back, which is what keeps
tracebacks, documentation tools, and framework introspection working.
"""

import functools


def dec1(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return "dec1(" + f(*args, **kwargs) + ")"
    return wrapper


def dec2(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return "dec2(" + f(*args, **kwargs) + ")"
    return wrapper


@dec1
@dec2
def target():
    return "target"


print("--- stacked decorators compose bottom-up ---")
print("  result:", target())               # dec1(dec2(target))
print("  __name__ preserved:", target.__name__)

print()
print("--- the bug functools.wraps prevents ---")


def naive(f):
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper


@naive
def endpoint():
    "the real docstring"
    return "ok"


print("  without wraps -> __name__:", endpoint.__name__, "| __doc__:", endpoint.__doc__)
print("  a framework that routes by __name__, or a doc tool reading __doc__,")
print("  now sees 'wrapper' and None for every decorated function.")

print()
print("--- a parameterized decorator is a factory: a function returning a decorator ---")


def repeat(n):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return [f(*args, **kwargs) for _ in range(n)]
        return wrapper
    return decorator


@repeat(3)
def greet(name):
    return f"hi {name}"


print("  greet('ada'):", greet("ada"))
