"""Listing 72.1 - a generator expression is lazy; adding [] makes it eager.

(x for x in data) is a generator expression: a lazy iterator that produces values
on demand. [x for x in data] is a list comprehension: it builds the WHOLE list
first. The difference is invisible in the syntax (just two brackets) but enormous
in behavior. Passed to any()/all()/next(), a genexp SHORT-CIRCUITS, it stops at
the first item that decides the answer, while a listcomp materializes every
element before the function even runs. This listing counts how many items each
form examines, proving the short-circuit.
"""

COUNT = {"examined": 0}


def check(x):
    COUNT["examined"] += 1        # count every item actually looked at
    return x == 5


def main() -> None:
    data = range(1_000_000)

    print("--- any() over a generator expression: short-circuits ---")
    COUNT["examined"] = 0
    found = any(check(x) for x in data)          # no brackets: lazy
    print(f"  result: {found}, items examined: {COUNT['examined']} (stopped at x==5)")

    print("--- any() over a list comprehension: examines everything first ---")
    COUNT["examined"] = 0
    found = any([check(x) for x in data])        # brackets: builds the whole list
    print(f"  result: {found}, items examined: {COUNT['examined']:,} (built the full list)")

    print("--- next() on a genexp takes just the first matching value ---")
    COUNT["examined"] = 0
    first_even_over_10 = next(x for x in data if x > 10 and x % 2 == 0)
    print(f"  first even > 10 : {first_even_over_10}")

    print("--- a genexp is a one-shot iterator; a listcomp is a reusable list ---")
    gen = (x * x for x in range(3))
    print(f"  genexp first pass : {list(gen)}")
    print(f"  genexp again      : {list(gen)}  (exhausted)")
    squares = [x * x for x in range(3)]
    print(f"  listcomp reusable : {squares} {squares}")


if __name__ == "__main__":
    main()
