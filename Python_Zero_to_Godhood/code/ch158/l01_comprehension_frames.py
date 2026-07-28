"""Listing 158.1 - a comprehension has no frame of its own; a generator expression does.

Until 3.11, `[f(x) for x in xs]` compiled to a hidden one-shot FUNCTION: the compiler
emitted a nested code object named <listcomp>, built a function object from it at
runtime, and CALLED it. Every comprehension therefore paid a function call and a frame
allocation, and the call showed up in tracebacks and profiles.

PEP 709 (3.12) INLINES list, dict, and set comprehensions into the enclosing code
object. There is no nested code object, no function to build, and no frame to push. The
iteration variable becomes a hidden local of the ENCLOSING function, saved and restored
around the comprehension (LOAD_FAST_AND_CLEAR) so that it still does not leak.

Generator expressions are NOT inlined and cannot be: a generator must own a frame,
because the frame is what gets suspended and resumed. So the two constructs that look
almost identical in source are now structurally different at runtime, and this listing
shows the four places that difference is observable.
"""

import sys
import traceback
import types


def which_frame():
    """sys._getframe() inside each construct names the frame the body runs in."""
    listcomp = [sys._getframe().f_code.co_name for _ in range(1)]
    setcomp = {sys._getframe().f_code.co_name for _ in range(1)}
    dictcomp = {sys._getframe().f_code.co_name: 1 for _ in range(1)}
    genexpr = list(sys._getframe().f_code.co_name for _ in range(1))
    return listcomp[0], setcomp.pop(), next(iter(dictcomp)), genexpr[0]


def with_listcomp(xs):
    return [x * 2 for x in xs]


def with_genexpr(xs):
    return (x * 2 for x in xs)


def nested_code_objects(fn):
    return [c.co_name for c in fn.__code__.co_consts if isinstance(c, types.CodeType)]


def no_leak():
    """The iteration variable is a hidden local, saved and restored around the body."""
    x = "outer"
    squares = [x for x in range(3)]
    return x, squares


def boom():
    return [1 / 0 for _ in range(1)]


def failing_frames():
    """Function names on the traceback, innermost last. A <listcomp> frame would show."""
    try:
        boom()
    except ZeroDivisionError:
        return [f.name for f in traceback.extract_tb(sys.exc_info()[2])]
    return []


class ClassScope:
    """The first iterable is evaluated in the enclosing (class) scope; the rest are not."""
    vals = [1, 2, 3]
    try:
        first_iterable = [v * 2 for v in vals]
    except NameError as exc:
        first_iterable = f"NameError: {exc}"
    try:
        second_iterable = [(a, b) for a in vals for b in vals]
    except NameError as exc:
        second_iterable = f"NameError: {exc}"


def main() -> None:
    lc, sc, dc, ge = which_frame()
    print("--- which frame does the body run in? ---")
    print(f"  list comprehension   : {lc}")
    print(f"  set comprehension    : {sc}")
    print(f"  dict comprehension   : {dc}")
    print(f"  generator expression : {ge}")

    print("--- an inlined comprehension leaves no nested code object behind ---")
    print(f"  code objects in with_listcomp.co_consts : {nested_code_objects(with_listcomp)}")
    print(f"  code objects in with_genexpr.co_consts  : {nested_code_objects(with_genexpr)}")

    print("--- the iteration variable is a hidden local of the ENCLOSING function ---")
    print(f"  with_listcomp.co_varnames : {with_listcomp.__code__.co_varnames}")
    print(f"  with_genexpr.co_varnames  : {with_genexpr.__code__.co_varnames}")

    print("--- and it still does not leak: the outer binding is restored ---")
    outer, squares = no_leak()
    print(f"  x after [x for x in range(3)] : {outer!r}")
    print(f"  the comprehension's result    : {squares}")

    print("--- no <listcomp> frame on the traceback ---")
    print(f"  frames raising from inside a comprehension : {failing_frames()}")

    print("--- in a class body, only the FIRST iterable sees class scope ---")
    print(f"  [v * 2 for v in vals]              : {ClassScope.first_iterable}")
    print(f"  [(a, b) for a in vals for b in vals] : {ClassScope.second_iterable}")

    print("--- the rule ---")
    print("  list/set/dict comprehensions are inlined into the enclosing frame (PEP 709);")
    print("  a generator expression keeps its own frame, because a frame is what suspends")


if __name__ == "__main__":
    main()
