"""Listing 226.1 - Python 2.2 (2001): generators, iterators you can WRITE easily.

The iterator protocol (Chapter 15) made 'for' universal, but writing an
iterator by hand (__iter__/__next__ with explicit state) is verbose. Python
2.2's generators (PEP 255) fixed that: a function with `yield` becomes an
iterator automatically, where the function's LOCAL STATE is the iterator's
state and each `yield` is a __next__ that pauses and resumes. This made
laziness EASY - a generator produces values on demand, holding only its
current frame, so it can be infinite or stream gigabytes in constant memory
(Chapter 91). Deep F owns the coroutine machinery; this is the release that
made writing lazy iterators trivial. Verified on current interpreters.
"""


def countdown(n):
    """A generator: yield pauses, the next() resumes right after it."""
    while n > 0:
        yield n
        n -= 1


def main() -> None:
    print("--- a generator function returns an iterator, automatically ---")
    gen = countdown(3)
    print(f"  calling the function returns : {type(gen).__name__}")
    print(f"  it IS an iterator (has __next__) : {hasattr(gen, '__next__')}")
    print(f"  list(countdown(3)) : {list(countdown(3))}")
    print("  no __iter__/__next__ written by hand - `yield` generated them.")
    print("  the function's locals ARE the iterator's state (Chapter 15's")
    print("  hand-built CountdownIterator, in three lines)")

    print("--- yield PAUSES and RESUMES: the function runs between next()s ---")
    trace = []

    def traced():
        trace.append("before yield 1")
        yield 1
        trace.append("resumed, before yield 2")
        yield 2
        trace.append("resumed, function ends")

    g = traced()
    print(f"  after creating generator : trace={trace}  (nothing ran yet)")
    next(g)
    print(f"  after first next()       : trace={trace}")
    next(g)
    print(f"  after second next()      : trace={trace}")
    print("  the body runs LAZILY - only when next() asks. yield freezes the")
    print("  frame mid-function and next() thaws it. this suspend/resume is")
    print("  what Deep F elaborates into coroutines and async/await")

    print("--- laziness: a generator holds one frame, not the whole sequence ---")
    def naturals():
        n = 0
        while True:                              # INFINITE - impossible as a list
            yield n
            n += 1

    import itertools
    first_five = list(itertools.islice(naturals(), 5))
    print(f"  first 5 of an INFINITE generator : {first_five}")
    print("  naturals() never ends, yet costs one frame of memory. a list of")
    print("  all naturals is impossible; the generator is trivial. that is")
    print("  laziness (Chapter 91): produce on demand, hold only the present")

    print("--- generator expressions: laziness with comprehension syntax ---")
    squares_list = [x * x for x in range(5)]     # builds the whole list
    squares_gen = (x * x for x in range(5))      # builds nothing until asked
    print(f"  [x*x ...] materialises : {squares_list}")
    print(f"  (x*x ...) is lazy      : {type(squares_gen).__name__}, "
          f"summed = {sum(x * x for x in range(5))}")
    print("  parentheses instead of brackets make a generator expression -")
    print("  the comprehension's readability with the generator's laziness,")
    print("  the shape a streaming pipeline is built from (Chapter 91)")

    print("--- the constraint answered ---")
    print("  the iterator protocol (2.2) made 'for' universal but iterators")
    print("  tedious to write. generators (also 2.2) made them trivial - and")
    print("  by making lazy iterators easy, unlocked streaming, infinite")
    print("  sequences, and eventually coroutines and async (Deep F, Deep J).")
    print("  two 2.2 features, one abstraction: iteration you can write")


if __name__ == "__main__":
    main()
