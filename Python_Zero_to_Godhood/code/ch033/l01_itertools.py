"""Listing 33.1 - itertools: composable, lazy, C-speed iterator building blocks.

Chapter 9 established that iterators are lazy and O(1) in memory. itertools is the
toolkit built on that: functions that consume and produce iterators, composed
into pipelines that never materialize the intermediate data. Each is implemented
in C, so a pipeline of itertools calls is both memory-flat and fast.
"""

import itertools as it

print("--- infinite and slicing: count is unbounded, islice bounds it ---")
print("  islice(count(10, 2), 4):", list(it.islice(it.count(10, 2), 4)))

print()
print("--- chaining and flattening ---")
print("  chain([1,2],[3,4])      :", list(it.chain([1, 2], [3, 4])))
print("  chain.from_iterable     :", list(it.chain.from_iterable([[1], [2, 3], [4]])))

print()
print("--- grouping runs of equal keys (input must be sorted by the key) ---")
print("  groupby('aabbbc')       :", [(k, len(list(g))) for k, g in it.groupby("aabbbc")])

print()
print("--- running results and windows ---")
print("  accumulate([1,2,3,4])   :", list(it.accumulate([1, 2, 3, 4])))
print("  pairwise([1,2,3,4])     :", list(it.pairwise([1, 2, 3, 4])))

print()
print("--- combinatorics ---")
print("  product([1,2],['a','b']):", list(it.product([1, 2], ["a", "b"])))
print("  combinations([1,2,3], 2):", list(it.combinations([1, 2, 3], 2)))

print()
print("--- tee: the fix for the two-passes-over-one-iterator problem (Ch 9) ---")
first, second = it.tee([10, 20, 30])
print("  tee gives two independent iterators:", list(first), list(second))
