# Chapter 23: Identity, Equality, and Hashing

Chapter 19 settled what `is` means: it compares addresses, and the small-integer cache and string interning make it *look* like it compares values until it suddenly does not.
This chapter is about the other two relations an object participates in, **equality** (`==`, via `__eq__`) and **hashing** (`hash()`, via `__hash__`), and the single contract that binds them.
They are not two independent methods you happen to define near each other.
They are one protocol, and every dictionary and set in your program depends on you honouring it.

The contract has three clauses, and CPython enforces the first two for you.
Defining `__eq__` **removes** the inherited `__hash__` (your class becomes unhashable), because a custom notion of equality almost always invalidates the identity-based hash.
The default `__eq__` **is** identity, so an object with no `__eq__` compares equal only to itself.
And the clause you must uphold yourself is the invariant: **if `a == b` then `hash(a) == hash(b)`**, violate it and a dict or set does not raise, it silently *loses* your object, returning "not found" for a key it contains.
That last failure mode, a wrong answer with no exception, is the reason this chapter exists.

**This is the canonical home for the equality and hashing protocol.**
Chapter 19 owns identity, interning, and the small-integer cache (`is`, `id()`); this chapter owns `__eq__`/`__hash__` and their contract.
Rich comparison (`<`, `<=`, ordering, `functools.total_ordering`) is the next chapter; the internals of the `dict`/`set` open-addressing table that make hashing pay off are **Deep Q**.

## Section index

- **23.1** The contract: `__eq__`, `__hash__`, and what defining one does to the other
- **23.2** Breaking the invariant, and `is` versus `==`
- **23.3** Measurement: hash quality is O(1) versus O(n)
- **23.4** Edges and failure modes
- **23.5** Connections
- **23.6** Exercises
- **23.7** Summary and cross-references

Listings live under `code/ch108/` and are re-executed by `make verify` on both verification interpreters.

---

## 23.1 The contract: `__eq__`, `__hash__`, and what defining one does to the other

```python
# code/ch108/l01_eq_hash_contract.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- default: __eq__ is identity, and objects are hashable ---
  p == q (two distinct objects) : False
  p == p                        : True
  hash(p) works                 : True
--- defining __eq__ sets __hash__ to None: unhashable ---
  Eq.__hash__ is None : True
  putting Eq(1) in a set raises TypeError (unhashable): True
--- define __hash__ too, honouring a == b => hash(a) == hash(b) ---
  a == b                : True
  hash(a) == hash(b)    : True
  a set dedups them     : 1   (one element)
  dict[b] finds a's value : 'x'   (equal key retrieves it)
--- the rule ---
  == and hash are one contract: custom __eq__ needs a custom __hash__
  that maps equal objects to equal hashes
```

The default behaviour, `Plain`, is identity all the way through: `p == q` is `False` for two distinct objects, `p == p` is `True`, and `hash(p)` works (the default `__hash__` derives from the object's address, so every object is hashable and distinct by identity).
This is the sensible default for a class that has no *value*: two different bank-account objects are not equal just because their balances match.

Define `__eq__`, and CPython **sets `__hash__` to `None`**.
`Eq.__hash__ is None` is `True`, and putting an `Eq` in a set raises `TypeError`.
This looks harsh but it is protective: you have just told Python "these two distinct objects can be *equal*", and the inherited identity-hash would give those two equal objects *different* hashes, which is exactly the invariant violation that corrupts dicts (§23.2).
Rather than let you build that bug, Python makes the class unhashable until you supply a `__hash__` that is consistent with your `__eq__`.

`EqHash` supplies it.
Its `__hash__` returns `hash(self.v)`, derived from the same field its `__eq__` compares, so two `EqHash(1)` objects are equal *and* hash equal.
Now they behave as a value type: a set of them deduplicates (`len` is 1), and a dict stores under one and retrieves with an equal other (`dict[b]` finds `a`'s value).
The recipe generalises: **derive `__hash__` from the same fields `__eq__` uses**, and the idiomatic form is `return hash((self.field1, self.field2, ...))`, hashing a tuple of the identifying fields, which satisfies the invariant automatically and distributes well (§23.3).

---

## 23.2 Breaking the invariant, and `is` versus `==`

The invariant is a *you* responsibility, and its violation is uniquely nasty because nothing complains.

```python
# code/ch108/l02_broken_invariant.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a __hash__ that violates 'equal => same hash' breaks containers ---
  x == y            : True   (they are equal)
  hash(x) == hash(y): False   (but hash differently)
  y in d            : False   (container cannot find the equal key)
  no exception was raised: the wrong answer is returned silently
--- is compares identity; == compares value ---
  m == n (value)   : True
  m is n (identity): False
  [] == []         : True   (equal contents)
  [] is []         : False   (distinct objects)
--- the rule ---
  equal objects MUST hash equal, or dict/set lose them silently;
  use == to compare values, is only for identity (None, sentinels)
```

`Broken` defines `__eq__` by value but `__hash__` by `id()`, so `x == y` is `True` while `hash(x) != hash(y)`.
Store `x` in a dict, look up the equal `y`, and the answer is `False`: **the container cannot find a key it contains.**
The mechanism is mechanical, not mysterious.
A dict finds a key by hashing it to choose a bucket and then comparing within that bucket.
`y` hashes to a *different* bucket than `x` did, so the lookup checks the wrong bucket, finds nothing, and reports absence, no exception, just a wrong answer that will surface as a mysterious cache miss or a duplicate that should have deduplicated, hours away from the class that caused it.
This is why Python removes `__hash__` when you define `__eq__`: to make you provide a consistent one rather than inherit an inconsistent one.

The second block separates the two relations `is` and `==` conflate.
`m == n` is `True` (equal values) while `m is n` is `False` (distinct objects); `[] == []` is `True` while `[] is []` is `False`.
`==` asks "do these mean the same value", routed through `__eq__`; `is` asks "are these the same object", an address comparison that no method can override.
The rule from Chapter 19 stands and is now precise: **use `==` to compare values; reserve `is` for identity against singletons you control**, `None`, `True`, `False`, and sentinels you created, never for comparing values, where the small-integer cache and interning make `is` an unreliable coincidence.

---

## 23.3 Measurement: hash quality is O(1) versus O(n)

A `__hash__` can satisfy the invariant and still be *bad*, and the cost is asymptotic, not constant.

**Methodology.** `code/ch108/bench_hash.py`.
Two classes identical but for `__hash__`: `Good` returns `hash(self.v)` (distributes), `Bad` returns a constant `0` (every element collides).
Both are *correct*, equal objects still hash equal, so the invariant holds.
Membership (`target in s`) is timed on a set of 2,000 elements, `min`-style over 2,000 repetitions.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| `in` on a 2,000-element set | ns/lookup | vs good |
|---|---|---|
| good `__hash__` (distributes) | 79 | 1x |
| constant `__hash__` (collides) | 17,767 | **226x** |

A correct-but-constant hash makes membership **226x** slower at 2,000 elements (229x on 3.14.6), and the multiplier *grows with the set*, because it is the difference between O(1) and O(n).
A set finds an element by hashing it to a bucket and scanning only that bucket.
`Good` scatters 2,000 elements across ~2,000 buckets, so each bucket holds roughly one element and membership is a hash plus one comparison, O(1).
`Bad` funnels all 2,000 into a *single* bucket, so membership degrades to a linear scan of the whole set, O(n), and at 20,000 elements the gap would be ten times worse again.

The lesson completes the contract.
A `__hash__` must be **correct** (equal objects hash equal, §23.1) *and* **distributing** (unequal objects usually hash differently), and the second is not automatic, a constant hash is perfectly correct and catastrophically slow.
Both properties come for free from the idiomatic recipe: `return hash((self.field1, self.field2, ...))`.
Hashing a tuple of the identifying fields is consistent with a `__eq__` over those same fields (correctness) and inherits Python's well-distributed tuple hash (distribution).
Writing `__hash__` by hand, especially returning a constant "to be safe", is how you turn every dict and set keyed on your type into a linked list.

---

## 23.4 Edges and failure modes

**Defining `__eq__` makes the class unhashable.** §23.1.
It is not a bug; supply a `__hash__` derived from the same fields. If instances should never go in dicts/sets, leave it unhashable deliberately.

**Violating "equal implies equal hash" corrupts dicts and sets silently.** §23.2.
No exception, just lost keys and failed lookups. Always derive `__hash__` from the fields `__eq__` compares.

**A correct hash can still be O(n).** §23.3.
A constant (or low-entropy) hash satisfies the invariant but destroys performance. Use `hash((fields...))`; do not hand-roll.

**Hashable implies effectively immutable on the hashed fields.**
If you mutate a field that `__hash__` depends on *after* putting the object in a set/dict, its stored hash no longer matches, and it is lost exactly as in §23.2. Only hash on fields that do not change while the object is a key; value objects used as keys should be immutable.

**`__eq__` should return `NotImplemented`, not `False`, for unknown types.**
Returning `NotImplemented` (Chapter 20) lets the other operand's `__eq__` try, so `MyType(1) == SomeOtherType(...)` can still succeed if the other side knows how. Returning `False` denies that and can make `==` asymmetric.

**`hash()` is salted per process for `str`/`bytes`.**
Since Python 3.3, string and bytes hashing is randomised per interpreter run (PEP 456, hash-DoS defence), so `hash("x")` differs between runs. Never persist or compare hashes across processes; within a run the invariant still holds.

**`float('nan')` breaks reflexivity.**
`nan != nan`, so a `nan` in a container may be unfindable by value (though findable by identity, since containers check `is` before `==` as a fast path). Equality is not always reflexive when floats are involved.

**Mutable containers are unhashable by design.**
`list`, `dict`, `set` have `__hash__ = None` because their value can change; that is why you cannot use a list as a dict key. Use a `tuple` or `frozenset` for a hashable snapshot.

---

## 23.5 Connections

**Backward.**
Identity, `is`, `id()`, interning, and the small-integer cache are Chapter 19; this chapter is the value-equality counterpart it deferred. `__eq__` returning `NotImplemented` to let the other operand try is the operator protocol of Chapter 20. `__hash__` and `__eq__` being looked up on the type (so an instance-level `__hash__` is ignored) is Chapter 20's dispatch rule.

**Forward.**
Ordering (`__lt__`, `__le__`, and `functools.total_ordering`, which builds the other comparisons from `__eq__` plus one), is the next chapter. The open-addressing hash table that turns a good `__hash__` into O(1) membership, and the per-process hash salting of §23.4, are **Deep Q**. `@dataclass` and `@dataclass(frozen=True)`, which generate a consistent `__eq__`/`__hash__` pair for you, are an ergonomics topic (**Deep C**/dataclasses).

**Across books.**
The eq/hash contract is why **Book I**'s value types, money, prices, symbols, timestamps, can be dict keys and set members without surprises: each derives `__hash__` from its identifying fields and gets O(1) lookup for free. The order-book system keys orders and price levels on such value types, and the §23.2 failure mode is precisely the class of bug that would let a cancel silently miss a resting order, which is why the system's key types are immutable and hash on exactly the fields they compare, the discipline this chapter formalises.

---

## 23.6 Exercises

**1. Walk the contract.** Reproduce §23.1: show that a bare class is hashable and identity-equal, that adding `__eq__` makes it unhashable, and that adding a field-derived `__hash__` restores value semantics (set dedup, dict retrieval by equal key). Explain why Python removes `__hash__` in the middle step.

**2. Build the silent bug.** Reproduce §23.2's `Broken`: equal by value, hashed by `id()`. Put ten objects in a set, then test membership with fresh equal objects and show how many are "not found". Explain, in terms of buckets, why no exception is raised.

**3. Measure your hash.** Reproduce §23.3 for a value type of your own, comparing `hash((fields...))` against a constant hash, at set sizes 1,000, 4,000, and 16,000. Confirm the slowdown grows with n and explain the O(1)-versus-O(n) mechanism.

**4. Mutate a key.** Put an object in a set, then mutate a field its `__hash__` depends on, then test membership. Show it is lost. Explain why "hashable implies immutable-while-a-key", and how `frozen=True` dataclasses enforce it.

**5. The design question.** Python auto-removes `__hash__` when you define `__eq__`, but does *not* auto-generate a consistent `__hash__` from your `__eq__`. Argue why it makes the conservative choice (unhashable) rather than guessing a hash, addressing the invariant, mutability, and the fact that it cannot know which fields your `__eq__` used. Then explain how `@dataclass` resolves the tension.

---

## 23.7 Summary and cross-references

- **`__eq__` and `__hash__` are one contract.** The default `__eq__` is identity and every object is hashable by address; **defining `__eq__` sets `__hash__` to `None`** (the class becomes unhashable) until you supply a consistent `__hash__`.
- **The invariant: `a == b` implies `hash(a) == hash(b)`.** Violating it makes dicts and sets **silently lose keys**, a wrong answer with no exception, because the equal key hashes to the wrong bucket.
- **A correct hash must also distribute.** Measured: a constant `__hash__` (correct but colliding) makes 2,000-element set membership **226x** slower, O(n) instead of O(1), and worse as the set grows. Use `hash((identifying_fields...))`.
- **`is` versus `==`:** `is` compares identity (address), `==` compares value (`__eq__`). Use `==` for values, `is` only for singletons.
- **Edges:** hash only on fields that do not change while the object is a key; return `NotImplemented` (not `False`) from `__eq__` for unknown types; string hashing is per-process salted; `nan` breaks reflexivity; mutable containers are unhashable by design.

**Cross-references.** Identity, `is`, `id()`, interning → Chapter 19. `NotImplemented` and type-level dispatch → Chapter 20. Ordering and `total_ordering` → Chapter 24. The hash table, open addressing, and hash salting → Deep Q. `@dataclass`/`frozen` eq-hash generation → Deep C.
