"""Listing 237.1 - Python 2.7 (2010): collections.Counter, counting as a data type.

Counting occurrences is one of the most common things a program does - word
frequencies, event tallies, inventory. The manual idiom was a dict plus a guard:
`if k in d: d[k] += 1 else: d[k] = 1`, or the slightly better d.get(k, 0) + 1,
or defaultdict(int). All work; all are ceremony around one idea. Python 2.7's
collections.Counter is that idea as a type: a dict subclass where a missing key
counts as zero, so `c[k] += 1` always works, plus counting-specific operations
- most_common(), summing counters, subtracting them. Deep Q owns the dict it is
built on; this is the release that made 'tally things' a named, complete tool
rather than a re-derived pattern. Verified on current interpreters.
"""

from collections import Counter


def main() -> None:
    print("--- Counter: a missing key counts as zero ---")
    votes = ["yes", "no", "yes", "yes", "no", "abstain"]
    c = Counter(votes)                            # count an iterable directly
    print(f"  Counter(votes) : {dict(c)}")
    print(f"  c['yes']    : {c['yes']}")
    print(f"  c['missing'] : {c['missing']}  (absent key -> 0, no KeyError)")
    print("  the pre-2.7 tally was `if k in d: d[k]+=1 else: d[k]=1`. Counter")
    print("  makes a missing key read as 0, so counting is just c[k] += 1 -")
    print("  and Counter(iterable) tallies a whole sequence in one call")

    print("--- most_common(): the counting-specific operation ---")
    text = "the quick brown fox the lazy dog the end"
    freq = Counter(text.split())
    print(f"  word counts : {dict(freq)}")
    print(f"  most_common(2) : {freq.most_common(2)}")
    print("  most_common(n) returns the n highest-count items, already sorted -")
    print("  the exact operation a plain dict makes you write sorted(...,")
    print("  key=..., reverse=True) for. it is the point of counting")

    print("--- counters do arithmetic: add and subtract tallies ---")
    monday = Counter(apples=3, bananas=2)
    tuesday = Counter(apples=1, bananas=4, cherries=5)
    print(f"  monday + tuesday : {dict(monday + tuesday)}")
    print(f"  tuesday - monday : {dict(tuesday - monday)}")
    print("  adding counters sums per-key counts; subtracting removes them")
    print("  (dropping non-positive results). combining tallies from two")
    print("  sources is one operator, not a merge loop")

    print("--- update(): accumulate more counts into an existing Counter ---")
    running = Counter()
    for batch in [["a", "b"], ["a", "c"], ["a"]]:
        running.update(batch)                     # add counts, do not replace
    print(f"  after streaming 3 batches : {dict(running)}")
    print("  update() ADDS to the counts (unlike dict.update which REPLACES),")
    print("  so a Counter accumulates naturally across a stream of batches -")
    print("  the streaming-tally shape (Chapter 91) with counting built in")

    print("--- elements(): expand a Counter back to items ---")
    inventory = Counter(red=2, blue=1, green=3)
    expanded = sorted(inventory.elements())
    print(f"  sorted(elements()) : {expanded}")
    print("  elements() yields each key as many times as its count - the")
    print("  inverse of Counter(iterable). a Counter is really a MULTISET:")
    print("  a set where membership has a multiplicity")

    print("--- the constraint answered ---")
    print("  counting was a dict wrapped in a presence guard, re-derived in")
    print("  every codebase. 2.7's Counter made it a type: zero-default lookup")
    print("  so c[k]+=1 always works, most_common() for ranking, +/- to combine")
    print("  tallies, update() to stream. 'count things' stopped being a")
    print("  pattern and became a tool")


if __name__ == "__main__":
    main()
