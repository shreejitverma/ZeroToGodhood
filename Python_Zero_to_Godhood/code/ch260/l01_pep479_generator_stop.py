"""Listing 260.1 - Python 3.5/3.7 (PEP 479): a StopIteration inside a generator is a bug, not an exit.

A generator signals 'I am done' by raising StopIteration - normally implicitly,
when it falls off the end. The old danger: if StopIteration was raised INSIDE
the generator's body for some OTHER reason - a next() on an already-exhausted
iterator, a helper that raised it - it looked identical to 'done', so the
generator SILENTLY stopped early. A real bug (running an iterator dry) became
invisible truncation, one of the nastiest failure modes there is. PEP 479 fixed
it: a StopIteration that escapes a generator's body is now converted to
RuntimeError, so the bug surfaces loudly instead of hiding. It was opt-in in 3.5
(from __future__ import generator_stop) and became the default in 3.7. Deep F
owns the generator/iterator protocol; this is the release that made accidental
StopIteration a visible error. Verified on current interpreters.
"""


def main() -> None:
    print("--- a generator ending normally: StopIteration is implicit and fine ---")
    def counts_to_three():
        yield 1
        yield 2
        yield 3
    print(f"  list(counts_to_three()) : {list(counts_to_three())}")
    print("  falling off the end raises StopIteration internally - the correct,")
    print("  intended way to say 'done'. that path is unchanged by PEP 479")

    print("--- the trap: next() on an exhausted iterator INSIDE a generator ---")
    def broken(numbers):
        it = iter(numbers)
        while True:
            yield next(it)                       # when `it` runs dry, next() raises StopIteration
    print("  broken() loops forever calling next(it); when it exhausts, next()")
    print("  raises StopIteration from INSIDE the generator body")
    try:
        result = list(broken([10, 20]))
        print(f"  list(broken([10, 20])) : {result}  (silently stopped - the OLD bug)")
    except RuntimeError as exc:
        print(f"  list(broken([10, 20])) -> RuntimeError: {exc}")
    print("  since 3.7 the escaping StopIteration becomes a RuntimeError, so the")
    print("  bug is LOUD. before PEP 479 this returned [10, 20] silently, hiding")
    print("  that next() had run off the end - the invisible-truncation failure")

    print("--- the correct version: catch StopIteration or use a for-loop ---")
    def fixed(numbers):
        for n in numbers:                        # for-loop handles exhaustion correctly
            yield n
    print(f"  list(fixed([10, 20])) : {list(fixed([10, 20]))}")
    print("  a for-loop consumes the iterator and stops cleanly at the end -")
    print("  StopIteration never escapes the body. this is the right way to")
    print("  delegate iteration; raw next() in a generator needs a guard")

    print("--- why the old behaviour was so dangerous ---")
    print("  'silently produced fewer items than intended' is nearly impossible")
    print("  to debug: no error, no traceback, just wrong output somewhere")
    print("  downstream. PEP 479 converts the accidental StopIteration into a")
    print("  RuntimeError with a traceback pointing AT the bug - turning a silent")
    print("  data-corruption failure into an ordinary, findable exception")

    print("--- confirming the modern default is active ---")
    def raises_stopiteration():
        raise StopIteration                       # deliberately, inside a generator
        yield                                     # (makes this a generator)
    try:
        list(raises_stopiteration())
        print("  no error - PEP 479 NOT active (pre-3.7 behaviour)")
    except RuntimeError:
        print("  a bare `raise StopIteration` in a generator -> RuntimeError")
    print("  on this interpreter the PEP 479 behaviour is the default (3.7+):")
    print("  StopIteration cannot leak out of a generator to fake an early exit")

    print("--- the constraint answered ---")
    print("  a StopIteration raised inside a generator was indistinguishable")
    print("  from a normal finish, so an accidental one (next() on a dry")
    print("  iterator) silently truncated output - a hidden, brutal bug. PEP 479")
    print("  converts an escaping StopIteration to RuntimeError (opt-in 3.5,")
    print("  default 3.7), making the mistake a loud, traceable error")


if __name__ == "__main__":
    main()
