"""Listing 155.1 - immutability and accumulation: build in a mutable buffer, convert once.

Strings are IMMUTABLE: s += x cannot grow s in place; it conceptually builds a NEW string
of length len(s)+len(x). Repeating that in a loop does escalating work (CPython has a
fragile in-place optimization that softens it, but it is not guaranteed and not portable).
The idiomatic, reliably fast pattern is to ACCUMULATE in a mutable container (a list) and
CONVERT ONCE at the end: ''.join(parts). join computes the total size and allocates the
result a SINGLE time. This pattern generalizes: build with a mutable type, materialize the
immutable result once. This listing shows string immutability and the join pattern,
deterministically (the speed difference is the benchmark).
"""


def main() -> None:
    print("--- strings are IMMUTABLE: concatenation makes a NEW object ---")
    s = "abc"
    s2 = s + "d"
    print(f"  s + 'd' is a different object : {id(s) != id(s2)}")
    print(f"  the original is unchanged      : {s}")

    print("--- the reliably fast pattern: accumulate in a list, join once ---")
    parts = []
    for i in range(5):
        parts.append(str(i))            # append to a MUTABLE list (cheap)
    result = "".join(parts)             # allocate the final string ONCE
    print(f"  ''.join(['0','1','2','3','4']) : {result!r}")

    print("--- compare: the += loop (works, but does escalating allocation) ---")
    built = ""
    for i in range(5):
        built += str(i)                 # each += conceptually a new string
    print(f"  += loop result (same value)   : {built!r}")
    print(f"  same result, but join scales better (the benchmark)")

    print("--- the pattern generalizes to bytes: bytearray (mutable) -> bytes ---")
    buf = bytearray()
    for b in (65, 66, 67):
        buf.append(b)                   # bytearray is mutable, append is cheap
    frozen = bytes(buf)                 # convert to immutable bytes once
    print(f"  bytearray built then frozen   : {frozen!r}")

    print("--- and to any immutable result: build in a list, convert at the end ---")
    print(f"  list (mutable, append cheap) -> tuple/str/bytes (immutable) once")

    print("--- the rule ---")
    print(f"  do not grow an immutable object incrementally (s += x in a loop); build")
    print(f"  in a mutable container and materialize the immutable result once (join)")


if __name__ == "__main__":
    main()
