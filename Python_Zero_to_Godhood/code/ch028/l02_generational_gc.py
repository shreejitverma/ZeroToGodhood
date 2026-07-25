"""Listing 28.2 - the generational collector: survivors are promoted, and older
generations are scanned rarely.

Reference counting (Chapter 19) reclaims most garbage instantly; the cyclic
collector (Chapter 3) handles what refcounting cannot. This listing shows the
generational structure: a tracked object starts in generation 0, and each
collection it survives promotes it to an older generation that is scanned less
often. This is the weak generational hypothesis in action: most objects die
young, so scanning the young generation frequently and old generations rarely
keeps most collections cheap.
"""

import gc


class Node:
    def __init__(self):
        self.ref = None


gc.collect()          # clean slate
obj = Node()


def generation_of(o):
    for g in range(3):
        if o in gc.get_objects(generation=g):
            return g
    return None


print("--- a survivor is promoted through the generations ---")
print(f"  freshly created: generation {generation_of(obj)}")
gc.collect(0)
print(f"  after a gen-0 collection: generation {generation_of(obj)}")
gc.collect(1)
print(f"  after a gen-1 collection: generation {generation_of(obj)}")

print()
print("--- the thresholds that trigger each generation ---")
t0, t1, t2 = gc.get_threshold()
print(f"  gen-0 collected when (allocations - deallocations) exceeds {t0}")
print(f"  gen-1 collected after {t1} gen-0 collections")
print(f"  gen-2 collected after {t2} gen-1 collections")
print()
print("So gen-0 is scanned often and cheaply (few young objects), gen-2 rarely")
print("(the long-lived heap). An object that keeps surviving lands in gen-2 and")
print("is thereafter almost never rescanned, which is why gc.freeze() (Chapter 3)")
print("can move startup state out of collection entirely.")
