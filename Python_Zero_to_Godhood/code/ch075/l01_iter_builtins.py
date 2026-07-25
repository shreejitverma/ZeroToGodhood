"""Listing 75.1 - the iteration builtins: two-arg iter() and next(it, default).

Two under-used forms complete the iterator protocol and let you avoid hand-written
loops and StopIteration handling. iter(callable, sentinel) builds an iterator that
calls callable() repeatedly, stopping when it returns sentinel, the clean way to
"read until EOF" or "poll until a stop value". next(it, default) returns the next
value or, if the iterator is exhausted, the default, so you never write
try/except StopIteration for the common "next or a fallback". This listing shows
both, and their equivalence to the loops they replace.
"""

import io


def main() -> None:
    print("--- iter(callable, sentinel): call until the sentinel is returned ---")
    buf = io.BytesIO(b"x" * 5000)
    # read 1000-byte chunks until read() returns b'' (EOF)
    chunks = list(iter(lambda: buf.read(1000), b""))
    print(f"  chunks : {len(chunks)} of sizes {[len(c) for c in chunks]}")
    print(f"  replaces a while-True/read/if-not-break loop")

    print("--- a sentinel that is not EOF: poll a source until a stop value ---")
    values = iter([3, 1, 4, 1, 5, 0, 9])   # stand-in for a callable source
    got = list(iter(lambda: next(values), 0))   # stop at the first 0
    print(f"  polled until 0 : {got}")

    print("--- next(it, default): next value or a fallback, no exception ---")
    it = iter([10, 20])
    print(f"  next(it, -1) : {next(it, -1)}")   # 10
    print(f"  next(it, -1) : {next(it, -1)}")   # 20
    print(f"  next(it, -1) : {next(it, -1)}")   # exhausted -> -1 (no StopIteration)

    print("--- the equivalent it replaces ---")
    it2 = iter([10, 20])
    def next_or(it, default):
        try:
            return next(it)
        except StopIteration:
            return default
    print(f"  next_or(it, -1) three times : {next_or(it2, -1)} {next_or(it2, -1)} {next_or(it2, -1)}")


if __name__ == "__main__":
    main()
