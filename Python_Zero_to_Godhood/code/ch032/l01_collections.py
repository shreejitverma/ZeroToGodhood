"""Listing 32.1 - the collections module: the right container for the job.

The builtin list and dict are general-purpose; collections adds specialized
containers whose operations have better complexity or ergonomics for specific
jobs. deque gives O(1) insertion at BOTH ends; defaultdict removes the
missing-key boilerplate; Counter tallies; ChainMap layers namespaces without
merging; namedtuple gives a tuple named fields.
"""

from collections import deque, defaultdict, Counter, ChainMap, namedtuple

print("--- deque: O(1) at both ends (a list is O(n) at the left) ---")
dq = deque([2, 3])
dq.appendleft(1)          # O(1); list.insert(0, ...) is O(n)
dq.append(4)
print("  deque after appendleft/append:", list(dq))
dq2 = deque(maxlen=3)     # a bounded ring buffer
for x in range(6):
    dq2.append(x)
print("  deque(maxlen=3) keeps the last 3:", list(dq2))

print()
print("--- defaultdict: a missing key auto-creates its default ---")
groups = defaultdict(list)
for name, kind in [("cat", "animal"), ("rose", "plant"), ("dog", "animal")]:
    groups[kind].append(name)          # no 'if kind not in groups' boilerplate
print("  grouped:", dict(groups))

print()
print("--- Counter: tallying and multiset arithmetic ---")
c = Counter("mississippi")
print("  most_common(2):", c.most_common(2))
print("  addition     :", dict(Counter(a=3, b=1) + Counter(a=1, b=2)))

print()
print("--- ChainMap: layered lookup without merging (first mapping wins) ---")
defaults = {"color": "black", "size": "M"}
overrides = {"color": "red"}
cm = ChainMap(overrides, defaults)
print("  resolved color:", cm["color"], "| size:", cm["size"])

print()
print("--- namedtuple: a tuple with named fields, still a tuple ---")
Point = namedtuple("Point", ["x", "y"])
p = Point(3, 4)
print("  p.x, p.y:", p.x, p.y, "| is a tuple:", isinstance(p, tuple), "| unpacks:", tuple(p))
