"""Listing 55.1 - traceback: capturing and chaining errors for good diagnostics.

The traceback module turns a live exception into inspectable data and formatted
text: the frames that led to it, the exception chain, and the source context.
Two things matter for correct error reporting. Capturing the full traceback
(format_exc) is expensive because it walks every frame and reads source, so it
belongs in the error path, not the hot path. And exception CHAINING preserves
causation: `raise New from original` sets __cause__ ("this was caused by that"),
while re-raising during handling sets __context__ implicitly. This listing shows
the structured, DETERMINISTIC facts (frame counts, chain types), not the
formatted text (which contains environment-specific paths and line numbers).
"""

import traceback


def level_three():
    raise ValueError("root cause")


def level_two():
    level_three()


def level_one():
    level_two()


def main() -> None:
    print("--- structured access: the frames that led to the error ---")
    try:
        level_one()
    except ValueError as e:
        frames = traceback.extract_tb(e.__traceback__)
        print(f"  exception type      : {type(e).__name__}")
        print(f"  message             : {e}")
        print(f"  frames in traceback : {len(frames)}")
        print(f"  innermost function  : {frames[-1].name}")

    print("--- explicit chaining: raise New from original sets __cause__ ---")
    try:
        try:
            level_three()
        except ValueError as e:
            raise RuntimeError("wrapping the error") from e
    except RuntimeError as e:
        print(f"  outer               : {type(e).__name__}")
        print(f"  __cause__ (explicit): {type(e.__cause__).__name__}")
        print(f"  __context__ set     : {e.__context__ is e.__cause__}")

    print("--- implicit chaining: an error DURING handling sets __context__ ---")
    try:
        try:
            level_three()
        except ValueError:
            raise RuntimeError("failure while handling")   # no 'from'
    except RuntimeError as e:
        print(f"  __cause__ (none)    : {e.__cause__}")
        print(f"  __context__ (implicit): {type(e.__context__).__name__}")


if __name__ == "__main__":
    main()
