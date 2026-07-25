"""Listing 108.1 - the __eq__/__hash__ contract.

Equality and hashing are one protocol, not two. The rules CPython enforces:
  - The DEFAULT __eq__ is identity (x == y iff x is y), and the default __hash__
    is derived from id(), so every object is hashable and compares by identity.
  - Defining __eq__ SETS __hash__ to None, making the class UNHASHABLE. Python
    does this because a custom equality almost always invalidates the identity-
    based hash, and an object in a dict/set with a stale hash is a silent bug.
  - To be both custom-equal AND hashable, you must define __hash__ too, and it
    MUST satisfy the invariant: a == b implies hash(a) == hash(b).
This listing shows each step.
"""


def main() -> None:
    print("--- default: __eq__ is identity, and objects are hashable ---")
    class Plain:
        pass
    p, q = Plain(), Plain()
    print(f"  p == q (two distinct objects) : {p == q}")
    print(f"  p == p                        : {p == p}")
    print(f"  hash(p) works                 : {isinstance(hash(p), int)}")

    print("--- defining __eq__ sets __hash__ to None: unhashable ---")
    class Eq:
        def __init__(self, v):
            self.v = v

        def __eq__(self, other):
            return isinstance(other, Eq) and self.v == other.v

    print(f"  Eq.__hash__ is None : {Eq.__hash__ is None}")
    try:
        {Eq(1)}
    except TypeError as e:
        # the exact message varies by version; report the stable facts
        print(f"  putting Eq(1) in a set raises {type(e).__name__} (unhashable): "
              f"{'unhashable' in str(e)}")

    print("--- define __hash__ too, honouring a == b => hash(a) == hash(b) ---")
    class EqHash:
        def __init__(self, v):
            self.v = v

        def __eq__(self, other):
            return isinstance(other, EqHash) and self.v == other.v

        def __hash__(self):
            return hash(self.v)          # equal .v => equal hash: invariant holds

    a, b = EqHash(1), EqHash(1)
    lookup = {a: "x"}[b]                  # store under a, retrieve with equal b
    print(f"  a == b                : {a == b}")
    print(f"  hash(a) == hash(b)    : {hash(a) == hash(b)}")
    print(f"  a set dedups them     : {len({a, b})}   (one element)")
    print(f"  dict[b] finds a's value : {lookup!r}   (equal key retrieves it)")

    print("--- the rule ---")
    print(f"  == and hash are one contract: custom __eq__ needs a custom __hash__")
    print(f"  that maps equal objects to equal hashes")


if __name__ == "__main__":
    main()
