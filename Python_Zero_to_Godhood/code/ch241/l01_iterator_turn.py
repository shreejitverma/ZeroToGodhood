"""Listing 241.1 - Python 3.0 (2008): the iterator turn - laziness becomes the default.

In Python 2, range(), zip(), map(), filter(), and dict.keys()/values()/items()
all built and returned a LIST. range(10_000_000) allocated ten million ints
before the loop even started; map() over a huge sequence materialised a second
huge sequence. Python 3.0 made all of them LAZY: range is a compact object,
zip/map/filter are iterators that produce on demand, and dict views reflect the
dict live. The eager list was the exception; laziness became the rule. The
consequence is constant memory for what used to be linear, and it is why
`for i in range(10**9)` is fine in 3.x and a MemoryError risk in 2.x. Deep F
owns the iterator protocol; this is the release that made producing-on-demand
the language's default posture. Verified on current interpreters.
"""

import sys


def main() -> None:
    print("--- range is a compact object, not a list of every value ---")
    r = range(10_000_000)
    print(f"  range(10_000_000) type : {type(r).__name__}")
    same_size = sys.getsizeof(range(10)) == sys.getsizeof(range(10_000_000))
    print(f"  size of range(10) == size of range(10_000_000) : {same_size}")
    print(f"  it still indexes and has a length : r[5]={r[5]}, len={len(r)}")
    print("  in 2.x this allocated ten million ints up front; in 3.x range")
    print("  stores start/stop/step and COMPUTES each value on demand. its size")
    print("  is CONSTANT regardless of the range - laziness as the default")

    print("--- zip/map/filter return iterators, produced on demand ---")
    z = zip([1, 2, 3], ["a", "b", "c"])
    m = map(lambda x: x * x, range(5))
    f = filter(lambda x: x % 2 == 0, range(10))
    print(f"  zip(...)    is a {type(z).__name__}")
    print(f"  map(...)    is a {type(m).__name__}")
    print(f"  filter(...) is a {type(f).__name__}")
    print(f"  materialise when you ask : list(map) -> {list(map(lambda x: x*x, range(5)))}")
    print("  each is a one-frame iterator, not a second list. chaining them -")
    print("  filter over map over range - streams values through without ever")
    print("  building the intermediate sequences (Chapter 91)")

    print("--- an iterator is single-use: it exhausts ---")
    it = map(str, range(3))
    print(f"  first list(it)  : {list(it)}")
    print(f"  second list(it) : {list(it)}  (empty - already consumed)")
    print("  the flip side of laziness: an iterator yields each value ONCE, then")
    print("  is spent. this is the 3.x gotcha - a range you can reuse, but a")
    print("  map/zip/filter result you cannot. wrap in list() if you need it twice")

    print("--- dict.keys()/values()/items() are live VIEWS ---")
    d = {"a": 1, "b": 2}
    keys = d.keys()
    print(f"  d.keys() type : {type(keys).__name__}")
    print(f"  keys now : {list(keys)}")
    d["c"] = 3                                   # mutate the dict AFTER taking the view
    print(f"  after d['c']=3, same view : {list(keys)}  (reflects the change)")
    print("  in 2.x keys() returned a fixed list snapshot; in 3.x it is a VIEW")
    print("  that tracks the dict live and costs no copy. views even support")
    print("  set operations: d.keys() & other_keys")

    print("--- the memory consequence, stated plainly ---")
    big_sum = sum(x for x in range(1_000_000))
    print(f"  sum over range(1_000_000) : {big_sum}  (never built a list)")
    print("  `for i in range(10**9)` is fine in 3.x - constant memory. the same")
    print("  code in 2.x tried to allocate a billion-element list and could")
    print("  MemoryError. the iterator turn changed what programs are feasible")

    print("--- the constraint answered ---")
    print("  Python 2 defaulted to building lists: range, zip, map, filter, and")
    print("  dict.keys all materialised. 3.0 made them lazy - iterators and")
    print("  views that produce on demand - so laziness is the default and")
    print("  eagerness the explicit choice (wrap in list()). constant memory")
    print("  replaced linear, and huge sequences became ordinary")


if __name__ == "__main__":
    main()
