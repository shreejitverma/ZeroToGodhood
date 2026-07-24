"""Listing 9.2 - a generator is an iterator written as a suspended heap frame.

Writing the Countdown class by hand is tedious: the state machine is
boilerplate. A generator function (any def containing yield) lets you write the
logic and have CPython synthesize the iterator. At each yield, CPython saves the
resume offset and stack depth in a frame that lives on the heap, marks the
generator suspended, and returns control. next() re-attaches the frame and
resumes. That is what makes generators lazy and O(1) in memory.
"""


def gen_squares(n):
    for i in range(n):
        yield i * i


g = gen_squares(4)
print("--- a generator wraps a live, suspended frame ---")
print("  type(g)              :", type(g).__name__)
print("  g.gi_frame is not None:", g.gi_frame is not None)
print("  list(g)              :", list(g))

print()
print("--- laziness means one frame, not N items, regardless of size ---")
huge = gen_squares(10**9)
print("  gen_squares(10**9) created:", type(huge).__name__)
print("  it allocated ONE frame, not a billion-element list.")
print("  taking the first 5 with next():", [next(huge) for _ in range(5)])
print()
print("A generator is a producer (next) and, via send/throw/close from")
print("Chapter 5, a consumer too. The frame suspension is the same mechanism")
print("yield from and async/await build on.")
