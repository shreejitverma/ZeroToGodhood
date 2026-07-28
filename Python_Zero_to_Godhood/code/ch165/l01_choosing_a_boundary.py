"""Listing 165.1 - the boundary decision as arithmetic, from this volume's measurements.

Every chapter in Deep M produced a constant. Put them together and the choice of where
to place the C boundary stops being a matter of taste.

  bytecode instruction    3.4 ns   Chapter 78, on this machine
  Python function call     11 ns   Chapter 81
  ctypes call             142 ns   Chapter 83 (undeclared; ~220 ns with py_object)
  callback into Python    283 ns   Chapter 83, derived from qsort per comparison

From those, four designs for the same per-element operation over n elements, each with a
cost that is a straight line in n:

  1. pure Python loop           n * k * 3.4          k = instructions per element
  2. one FFI call per element   n * 142
  3. one FFI call, whole buffer 142 + n * c          c = the C cost per element
  4. C loop with a Python
     callback per element       n * 283

Design 2 is the one people write first and it is never right: it is strictly worse than
design 1 for any k below about 42 instructions per element, and real loop bodies are
6 to 14 (Chapter 77). Design 4 is design 2 with extra steps. Design 3 is the only one
whose slope is C's rather than Python's, and its fixed cost is a single call.

This listing computes all four at several sizes and reports the break-even points. It is
pure arithmetic over measured constants, so it is identical on both interpreters; the
benchmark beside it checks the model against a real operation.
"""

BYTECODE_NS = 3.4        # Chapter 78
PY_CALL_NS = 11.0        # Chapter 81
FFI_CALL_NS = 142.0      # Chapter 83
CALLBACK_NS = 283.0      # Chapter 83
C_PER_ELEMENT_NS = 1.0   # a plausible cost for simple C work on one element

SIZES = (1, 10, 100, 10_000, 1_000_000)
BODY_INSTRUCTIONS = 8    # Chapter 78's explicit loop


def python_loop(n, k=BODY_INSTRUCTIONS):
    return n * k * BYTECODE_NS


def ffi_per_element(n):
    return n * FFI_CALL_NS


def ffi_whole_buffer(n, c=C_PER_ELEMENT_NS):
    return FFI_CALL_NS + n * c


def c_loop_with_callback(n):
    return n * CALLBACK_NS


DESIGNS = (
    ("1  pure Python loop", python_loop),
    ("2  FFI call per element", ffi_per_element),
    ("3  FFI once, whole buffer", ffi_whole_buffer),
    ("4  C loop, Python callback", c_loop_with_callback),
)


def human(ns):
    if ns < 1_000:
        return f"{ns:8.0f} ns"
    if ns < 1_000_000:
        return f"{ns / 1_000:8.1f} us"
    return f"{ns / 1_000_000:8.1f} ms"


def main() -> None:
    print("--- the constants this volume measured, on this machine ---")
    print(f"  one bytecode instruction : {BYTECODE_NS:6.1f} ns")
    print(f"  one Python call          : {PY_CALL_NS:6.1f} ns")
    print(f"  one ctypes call          : {FFI_CALL_NS:6.1f} ns")
    print(f"  one callback into Python : {CALLBACK_NS:6.1f} ns")

    print(f"--- four designs, modelled at k = {BODY_INSTRUCTIONS} instructions per element ---")
    header = "  design                        " + "".join(f"{f'n={n:,}':>13}" for n in SIZES)
    print(header)
    for label, fn in DESIGNS:
        row = f"  {label:<28}" + "".join(f"{human(fn(n)):>13}" for n in SIZES)
        print(row)

    print("--- the break-even points that matter ---")
    # Design 2 beats design 1 only when the Python body is more expensive than a call.
    k_break = FFI_CALL_NS / BYTECODE_NS
    print(f"  FFI-per-element beats a Python loop only above "
          f"{k_break:.0f} instructions per element")
    print(f"  real loop bodies measured in this book : 6 to 14")
    print(f"  so FFI-per-element is never the answer : {14 < k_break}")

    # Design 3 beats design 1 once the fixed call is amortised.
    n_break = FFI_CALL_NS / (BODY_INSTRUCTIONS * BYTECODE_NS - C_PER_ELEMENT_NS)
    print(f"  one whole-buffer call beats a Python loop above n = {n_break:.0f}")
    print(f"  and its advantage grows without limit, because the slopes differ")

    print("--- the same conclusion, as a decision procedure ---")
    print("  is the per-element work expressible as one C operation over a buffer?")
    print("    yes -> design 3: cross once, pass a memoryview, release the GIL")
    print("    no, it needs a Python callable per element -> stay in Python (design 1)")
    print("    no, and it must be fast -> write the per-element code in C too")

    print("--- the rule ---")
    print("  the boundary is worth crossing exactly once per batch; if your design")
    print("  crosses per element, the boundary is in the wrong place")


if __name__ == "__main__":
    main()
