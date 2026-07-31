"""Listing 283.1 - Python 3.12 (2023): PEP 683, immortal objects.

Every Python object carries a reference count, bumped up on each new reference and
down on each release; at zero it is freed. For the objects used EVERYWHERE - None,
True, False, small ints - this churns constantly: reading None a million times
touches its refcount a million times. That churn is pure overhead, and it is
actively harmful in two modern settings: under free-threading every bump needs an
ATOMIC operation (contention on a shared cache line), and after os.fork() the
refcount writes DIRTY copy-on-write pages that were meant to stay shared. Python
3.12's PEP 683 made these ubiquitous objects IMMORTAL: a fixed, saturated refcount
that is never changed, so they are never touched and never freed. Deep L owns the
free-threading story this enables; this is the release that stopped the churn on
the objects that matter most. This listing tests refcount BEHAVIOUR with
thresholds, never a raw count. Verified on current interpreters.
"""

import sys

_HUGE = 2 ** 30                                  # far above any real refcount


def main() -> None:
    print("--- the ubiquitous singletons are immortal: a saturated refcount ---")
    for obj, label in [(None, "None"), (True, "True"), (False, "False"),
                       (0, "int 0"), (1, "int 1")]:
        print(f"  {label:>6} refcount is saturated (immortal) : "
              f"{sys.getrefcount(obj) > _HUGE}")
    print("  None/True/False and small ints report an enormous, fixed refcount -")
    print("  the 'immortal' marker. it means the count is pinned and will never")
    print("  reach zero, so these objects are never touched and never freed")

    print("--- a normal object has a modest, LIVE refcount ---")
    obj = [1, 2, 3]
    print(f"  a fresh list's refcount is immortal? : "
          f"{sys.getrefcount(obj) > _HUGE}   (no - it is a normal, counted object)")
    print("  ordinary objects still use real reference counting: their count is")
    print("  small and reflects how many references exist. immortality is only")
    print("  for the handful of objects that live for the whole program anyway")

    print("--- adding a reference does NOT change an immortal's count ---")
    before = sys.getrefcount(None)
    another = None                               # a new reference to None
    after = sys.getrefcount(None)
    print(f"  getrefcount(None) unchanged after a new reference : {before == after}")
    print("  binding another name to None left its refcount untouched - because")
    print("  immortal objects skip the increment entirely. that skipped write is")
    print("  the whole point")

    print("--- but a normal object's count DOES move with references ---")
    data = [10, 20]
    base = sys.getrefcount(data)
    alias = data                                 # one more reference
    with_alias = sys.getrefcount(data)
    del alias
    after_del = sys.getrefcount(data)
    print(f"  refcount rose when aliased : {with_alias > base}")
    print(f"  and fell when the alias was deleted : {after_del < with_alias}")
    print("  the contrast is the point: mortal objects pay the bump-and-drop")
    print("  cost (and get freed at zero); immortal ones opt out of it")

    print("--- why immortality matters: free-threading and fork ---")
    print("  under free-threading (Deep L, Part VII), every refcount bump on a")
    print("  SHARED object needs an ATOMIC write - and None is shared by every")
    print("  thread, so its count would be a contention hotspot. immortal = no")
    print("  writes = no contention. and after os.fork(), refcount writes dirty")
    print("  copy-on-write pages; immortal objects keep those pages shared. PEP")
    print("  683 is groundwork the no-GIL work (Part VII) needed")

    print("--- the constraint answered ---")
    print("  reference counting churned constantly on None/True/False/small ints -")
    print("  wasted work normally, and actively harmful under free-threading")
    print("  (atomic contention) and fork (copy-on-write page dirtying). PEP 683")
    print("  (3.12) made those objects immortal: a fixed refcount that is never")
    print("  touched. the most-used objects stopped paying the counting tax")


if __name__ == "__main__":
    main()
