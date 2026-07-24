"""Listing 9.1 - the iterator protocol, and the bytecode every for-loop speaks.

Python decouples consuming a sequence from being one, so the same for-loop
drives a list, a file, a cursor, or an infinite counter. An iterable implements
__iter__ (returns a fresh iterator); an iterator implements __next__ (next item
or raise StopIteration) and __iter__ returning self. A for-loop is GET_ITER
once, then FOR_ITER repeatedly until StopIteration.
"""

import dis


class Countdown:
    def __init__(self, n):
        self.n = n

    def __iter__(self):
        return self

    def __next__(self):
        if self.n <= 0:
            raise StopIteration
        self.n -= 1
        return self.n + 1


print("--- a hand-written iterator; for-loops speak exactly this protocol ---")
print("  list(Countdown(3)):", list(Countdown(3)))


def loop(xs):
    for x in xs:
        pass


print()
print("--- the core opcodes of any for-loop ---")
core = {"GET_ITER", "FOR_ITER", "STORE_FAST", "JUMP_BACKWARD", "END_FOR"}
for ins in dis.get_instructions(loop):
    if ins.opname in core:
        print("  ", ins.opname)
print()
print("GET_ITER calls __iter__ once; FOR_ITER calls __next__ and jumps out on")
print("StopIteration. StopIteration is control flow, not an error: FOR_ITER")
print("catches it internally to end the loop. This is why a stray StopIteration")
print("raised inside a generator body is a bug (PEP 479 turns it into")
print("RuntimeError).")
