"""Listing 135.1 - the interpreter's two core objects: the code object and the frame.

CPython runs your program in two layers:
  - A CODE OBJECT is the COMPILED form of a function (or module/class body). `def`
    compiles the source ONCE into a code object, func.__code__, holding the bytecode
    plus tables: the argument count, the local variable names, the literal constants,
    the global/attribute names referenced. Every call reuses this one compiled artifact.
  - A FRAME is the RUNTIME state of one active call: its local variables, its position
    in the bytecode, and a link (f_back) to the frame that called it. The chain of
    f_back links IS the call stack you see in a traceback.
This listing inspects a code object and walks the frame stack, using version-stable
attributes (a function's exact bytecode and constant table vary across releases).
"""

import sys


def greet(name, count=1):
    prefix = "hi"                        # a local; 'hi' is a constant
    return prefix + name * count


def main() -> None:
    print("--- a code object: what `def greet` compiled to (once) ---")
    c = greet.__code__
    print(f"  co_argcount : {c.co_argcount}   (name, count)")
    print(f"  co_varnames : {c.co_varnames}   (locals incl. args, in order)")
    print(f"  co_nlocals  : {c.co_nlocals}")
    print(f"  'hi' is in co_consts (a literal constant) : {'hi' in c.co_consts}")
    print(f"  co_names (globals/attrs referenced)       : {c.co_names}   (none here)")
    print(f"  co_code is compiled bytecode (bytes)      : {isinstance(c.co_code, bytes)}")
    print(f"  the SAME code object is reused every call : {greet.__code__ is c}")

    print("--- a frame: the runtime state of one call, with f_back = its caller ---")
    def inner():
        frame = sys._getframe()
        return (frame.f_code.co_name, frame.f_back.f_code.co_name)

    def outer():
        return inner()

    this_func, caller = outer()
    print(f"  inner's frame f_code.co_name        : {this_func!r}")
    print(f"  its caller via f_back.f_code.co_name : {caller!r}   (the call stack)")

    print("--- a frame carries its own local variables ---")
    def with_locals():
        x, y = 10, 20
        return sorted(sys._getframe().f_locals.keys())
    print(f"  f_locals of a frame with x, y : {with_locals()}")

    print("--- the rule ---")
    print(f"  a code object is the compiled function (made once, reused per call);")
    print(f"  a frame is one call's live state; f_back chains frames into the call stack")


if __name__ == "__main__":
    main()
