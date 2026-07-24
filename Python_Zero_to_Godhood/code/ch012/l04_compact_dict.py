"""Listing 12.4 - the compact dict is ordered, and the ordering is free.

Before 3.6 a dict was one sparse hash table of 24-byte entry slots kept at most
two-thirds full, so it held many empty 24-byte slots. Raymond Hettinger's compact
design (3.6) split it in two: dk_indices, a small sparse array of integer indices
(1/2/4/8 bytes each) that is the actual hash table, and dk_entries, a dense
contiguous array of (hash, key, value) appended in insertion order. Empty slots
now cost 1 to 8 bytes, not 24, cutting dict memory ~30-40%, and because entries
are dense and in-order, iteration order equals insertion order for free.
"""

print("--- iteration order equals insertion order ---")
d = {}
for k in ["z", "a", "m", "b"]:
    d[k] = 1
print("  inserted z, a, m, b -> list(d):", list(d))

print()
print("--- deleting and re-inserting moves a key to the end ---")
d2 = {"first": 1, "second": 2, "third": 3}
del d2["first"]
d2["first"] = 1
print("  after del+reinsert 'first' :", list(d2))

print()
print("Insertion order was an implementation detail in 3.6 and a LANGUAGE")
print("GUARANTEE since 3.7; code may rely on it. This is what Java provides only")
print("via a separate LinkedHashMap; in Python the default dict is ordered, and")
print("the ordering costs nothing because it falls out of the compact layout.")
print("Sets are still unordered: do not assume order survives a trip through one.")
