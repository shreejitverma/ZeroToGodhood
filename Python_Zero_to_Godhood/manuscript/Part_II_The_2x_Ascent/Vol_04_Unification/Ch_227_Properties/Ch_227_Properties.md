# Chapter 17: Properties

Volume 4's unification brought new-style classes and, with them, the descriptor protocol (Deep C owns its mechanism). This chapter is that protocol's friendliest and most-used face: **Python 2.2 (2001) added `property`**, which lets a plain attribute *become* a computed or validated one with **no change to the calling code**. It is a small feature with a large cultural consequence, it is the reason idiomatic Python exposes public attributes freely where Java and C++ programmers write getters and setters defensively.

The problem `property` solves is classic object-oriented design. You expose `obj.price` as a plain attribute; code everywhere reads and writes `obj.price`; then you discover `price` needs *validation* (never negative) or *computation* (derived from other fields). In a language without properties, you must either have written `getPrice()`/`setPrice()` from the *start*, uglifying every access to preserve the option, or break every caller when you change the interface. Python's `property` dissolves the dilemma: `obj.price` can stay a plain attribute *today* and become a method-backed one *tomorrow*, and `obj.price` in the calling code never changes, because a property looks exactly like an attribute while running a method. This release chapter demonstrates it on the verification interpreters and reads why "just use a public attribute" is the correct Python default.

## Section index

- **17.1** The constraint: attributes you might need to upgrade
- **17.2** A property reads like an attribute, runs a method
- **17.3** Setters add validation without changing the interface
- **17.4** The payoff: start plain, upgrade later
- **17.5** Properties are descriptors on the class
- **17.6** Edges: property's subtleties
- **17.7** Connections
- **17.8** Exercises
- **17.9** Summary and cross-references

Listings live under `code/ch227/` and are re-executed by `make verify` on the verification interpreters.

---

## 17.1 The constraint: attributes you might need to upgrade

Consider the object-oriented dilemma that shaped a generation of Java code. You have a class with a `price` field. The simplest design exposes it as a public attribute: `order.price = 5`, `total = order.price * qty`. Clean, direct, readable. But then requirements change, prices must never be negative, or `price` should be computed from a base plus a markup, and now you need *behaviour* on attribute access. In Java, changing a public field to a method-backed one *breaks the interface*: `order.price` (field access) is syntactically different from `order.getPrice()` (method call), so every caller must change.

Java's answer was defensive: write `getPrice()`/`setPrice()` *from the start*, even for fields that need no behaviour, so that you *never* have to break the interface later. This is why Java code is full of trivial getters and setters that do nothing but return and assign a field, they exist not because the field needs behaviour, but because Java gives no way to *add* behaviour later without changing the interface. The cost is pervasive boilerplate and a reading experience where `order.getPrice()` obscures a plain field access. The constraint 2.2's `property` answered is that **you should be able to expose a plain attribute and add behaviour to it later without breaking callers**, removing the reason for defensive getters and setters.

---

## 17.2 A property reads like an attribute, runs a method

```python
# code/ch227/l01_properties.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- a property reads like a plain attribute but runs a method ---
  o.total is accessed like an attribute : 50
  but it is COMPUTED (10 * 5), not stored : True
  change qty, total recomputes on read    : 100
  o.total has no parentheses - it reads as an attribute - yet runs
  a method each access. the CALLER cannot tell it from a stored
  field, which is the whole point
```

**A property is accessed with attribute syntax (no parentheses) but runs a method each time, and the caller cannot tell it from a stored field.**
`o.total` reads like an attribute, but it is *computed* (`qty * unit_price`), not stored, which is why changing `qty` to 20 makes `o.total` recompute to 100 on the next read. The `@property` decorator makes `total` a computed attribute: accessing `o.total` runs the `total` method and returns its result, but the *syntax* is plain attribute access, `o.total`, not `o.total()`. This indistinguishability is the entire point: code that reads `o.total` works identically whether `total` is a stored field or a computed property, so you can *switch between them* without touching the caller. The property looks like an attribute and behaves like a method, and that duality is what preserves the interface.

**The "no parentheses" syntax is deliberate and load-bearing.**
`o.total` (property) and `o.total` (field) are *identical* in the source; only `o.total()` (a method call) would differ. Because a property is accessed without parentheses, it is *syntactically an attribute*, which is exactly what makes it a drop-in replacement for a field. If properties required `o.total()`, they would be just methods, and switching a field to a method *would* break callers (the Java problem). The genius is that `property` hooks attribute *access* (the `.total` dot) rather than requiring a call, so the field-to-computed upgrade is invisible in the calling syntax. Deep C owns *how* this works (the descriptor protocol intercepting attribute access); this chapter's point is *that* it works, and that its working is why the interface survives the upgrade.

---

## 17.3 Setters add validation without changing the interface

```text
--- a setter adds validation without changing the interface ---
  o.unit_price reads normally : 5
  o.unit_price = 7 (via setter): 7
  o.unit_price = -1 rejected  : ValueError(price cannot be negative)
  assignment (o.unit_price = 7) runs the setter method - so you can
  validate, log, or convert on assignment, and the caller still
  writes plain 'o.unit_price = 7'. the interface never changed
```

**A property setter runs a method on *assignment*, so you can validate without changing how the caller writes the assignment.**
`o.unit_price = 7` looks like a plain field assignment but runs the `unit_price.setter` method, which validates (rejecting `-1` with `ValueError`). The caller still writes `o.unit_price = 7`, plain assignment syntax, but now that assignment is *intercepted* by the setter, which can validate, log, convert, or compute. This is the write-side of §17.2's read-side: just as `@property` hooks attribute *reads*, the setter hooks attribute *writes*, and both preserve the syntax (`o.x` for read, `o.x = v` for write) while adding behaviour. The interface, how the caller reads and writes the attribute, never changes; only what happens *behind* it does.

**Validation on assignment is the killer use, and it enforces invariants.**
Without properties, an invariant like "price is never negative" can only be checked by convention (hope callers behave) or by wrapping every assignment in a method (Java's setter, breaking the interface). With a property setter, the invariant is *enforced at the point of assignment*, `o.unit_price = -1` raises, always, no matter where the assignment is, and the caller still uses natural syntax. This makes objects *self-protecting*: the class guarantees its invariants regardless of how callers use it, which is a real correctness gain (the order book's fixed-point prices, Chapter 131, use exactly this to reject invalid prices at assignment). And it costs the caller nothing, plain assignment, validated behind the scenes.

---

## 17.4 The payoff: start plain, upgrade later

```text
--- the payoff: start with a plain attribute, upgrade later ---
  V1().value (plain field)   : 21
  V2().value (now a property): 42
  code doing obj.value works UNCHANGED on both - the plain field
  became a property with zero caller impact. this is why Python
  exposes public attributes: you never lose the option to add
  behaviour, so getters/setters up front (Java-style) are needless
```

**The plain field and the property are interchangeable to callers, which is why Python exposes public attributes freely.**
`V1.value` is a plain field; `V2.value` is a property (computed as `_value * 2`). Code doing `obj.value` works *unchanged* on both, the field became a property with *zero* caller impact. This is the payoff that reshaped Python's design culture: because you can *always* upgrade a plain attribute to a property later, you *never lose the option* to add behaviour, so there is no reason to write defensive getters and setters up front. Java writes `getValue()`/`setValue()` for every field to preserve the upgrade option; Python writes a public attribute and upgrades to a property *only if and when* behaviour is needed. The result is that idiomatic Python is dramatically less cluttered, public attributes everywhere, properties only where behaviour is actually required.

**This is a genuine cultural difference, and `property` is its cause.**
"Just use a public attribute" is Python's default advice, and it is *safe* advice precisely because of `property`: the worst case (you later need behaviour) is handled by a transparent upgrade, not an interface break. A Python programmer who writes `self.x = value` in `__init__` and exposes `x` publicly has lost nothing, they can add a property later. A Java programmer who did the same would face a breaking change to add validation, so Java culture writes the getters and setters defensively. `property` removed the defensive tax, and Python's clean, attribute-heavy style is the result, one small 2.2 feature reshaping how an entire language is written. The Zen's "simple is better than complex" (Chapter 3) is served: the simple public attribute is safe because the complex option (a property) is available without an interface change.

---

## 17.5 Properties are descriptors on the class

```text
--- properties are descriptors on the CLASS, not the instance ---
  Order.total is a property object : property
  the instance has no 'total' in its dict : True
  a property lives on the CLASS as a descriptor (Deep C); accessing
  it on an instance triggers __get__/__set__. that is the mechanism
  behind the 'looks like an attribute, runs a method' magic
```

**A property is a descriptor stored on the class, not a value on the instance, and that is the mechanism behind the magic.**
`Order.total` is a `property` object (a descriptor); the *instance* has no `total` in its `__dict__`. When you access `o.total`, Python's attribute lookup finds `total` on the *class*, sees it is a descriptor (has `__get__`), and calls `__get__` to produce the value, which runs the property's method. This is the descriptor protocol (Deep C's subject): a descriptor is a class attribute that intercepts access to it on instances, and `property` is a descriptor whose `__get__`/`__set__` run the getter/setter methods. The "looks like an attribute, runs a method" magic is the descriptor protocol, and `property` is its most user-friendly application, the raw protocol (writing `__get__`/`__set__` by hand) is Deep C, and `property` is the sugar that makes the common case (a computed/validated attribute) a two-line decorator.

**Understanding "on the class, not the instance" resolves property confusion.**
Because the property lives on the class, *all instances* share it, and it intercepts access uniformly. This is why you cannot "remove" a property from one instance (it is not in the instance dict), why `del o.total` behaves specially (it calls the deleter, if any, not deletes an instance attribute), and why property access always runs the method (there is no instance attribute to shadow it, unless you do something unusual). The class-level descriptor model is the mechanism, and Deep C owns its full depth (data vs non-data descriptors, the lookup precedence, `__set_name__`); the release-level takeaway is that `property` made the descriptor protocol *accessible*, turning a powerful-but-arcane mechanism into an everyday tool.

---

## 17.6 Edges: property's subtleties

**A property with only a getter is read-only, and assignment raises.**
`@property` with no setter makes the attribute read-only, `o.total = 5` raises `AttributeError`. This is often *desired* (a computed attribute like `total` should not be assignable), but it surprises code that expects to assign. Read-only-by-default (add a setter to allow writes) is the property's stance, and it enforces "this is computed, do not assign" as a real constraint.

**Properties run a method on every access, which has a cost.**
`o.total` runs the getter *each time*, so a property computing something expensive is recomputed on every read, unlike a stored field (read once, cached). For expensive computations, `functools.cached_property` (Chapter 34, Deep Q) caches the first result, but a plain `property` does not. The cost is usually negligible, but a property in a hot loop that recomputes an expensive value each iteration is a real performance trap (Chapter 90's caching, applied).

**Overusing properties reintroduces the boilerplate they removed.**
The lesson of §17.4 is "use plain attributes, upgrade to properties *when needed*", not "wrap every attribute in a property". A class where every attribute is a trivial property (getter returns the field, setter assigns it) has reinvented Java's boilerplate with Python syntax, missing the point. Properties are for attributes that *need* behaviour; plain attributes are for the rest, and the discipline is to add a property only when validation, computation, or logging is actually required.

**And a property that raises during `__init__` is a subtle bug.**
If `__init__` assigns to a validated property (`self.price = value`) and the value is invalid, the setter raises *during construction*, leaving a half-built object. This is usually correct (reject invalid construction), but the interaction, `__init__` assignments running setters, means construction can fail in the setter, and the object may be partially initialised when it does. Ordering `__init__` so that validated assignments come after the object is otherwise consistent avoids the half-built-object hazard.

---

## 17.7 Connections

**Backward.**
New-style classes and the descriptor protocol that `property` is built on are the type-class unification (this volume) and Deep C; the object model where attributes are dict entries and class lookups is Chapter 4; the values (simple public attributes, no defensive boilerplate) are Chapter 3.

**Forward.**
The full descriptor protocol, data vs non-data descriptors, `__get__`/`__set__`/`__set_name__`, is Deep C; `cached_property` for expensive computed attributes is Chapter 34 (Deep Q) and Chapter 90 (caching, Deep K); `dataclasses` (which generate `__init__` and work with properties) are Deep Q; the order book's price validation via properties is Chapter 131 (Deep V).

**Across books.**
Properties are Python's; **Book I**'s C++ has no direct equivalent (it uses getter/setter methods, the Java-style approach, or member functions), so the field-to-computed upgrade *does* break the interface in C++, which is why C++ APIs are more conservative about exposing data members. The shared trading system uses Python properties for validated, computed fields on its Python side (order totals, validated prices) and explicit accessor methods on its C++ side, the same intent, different mechanisms, meeting at the boundary (Deep M).

---

## 17.8 Exercises

**1. Upgrade a field.** Write a class with a plain public attribute; write code that uses it; then convert the attribute to a property (computed or validated) *without* changing the using code. Confirm zero caller impact.

**2. Enforce an invariant.** Add a property setter that enforces a real invariant (positive, in-range, a valid enum); show assignment rejecting invalid values; relate to Chapter 131's price validation.

**3. Measure the recomputation cost.** Make a property compute something expensive; call it in a loop; measure the cost; then convert to `cached_property` and re-measure. This is §17.6's trap and Chapter 90's caching.

**4. Read-only enforcement.** Make a computed property with no setter; show `AttributeError` on assignment; explain why read-only-by-default is correct for computed attributes.

**5. The design question.** `property` lets Python expose public attributes freely (upgrade later) where Java writes defensive getters/setters. Argue whether the Python approach (public attributes, upgrade on demand) or the Java approach (accessors always) is better for a *library* API (where you cannot see or change callers), and identify the risk each carries, using the interface-stability guarantee `property` provides.

---

## 17.9 Summary and cross-references

- **Python 2.2 (2001) added `property`**, which lets a plain attribute *become* computed or validated with **no change to calling code**: `o.total` reads like an attribute (no parentheses) but runs a method, and the caller cannot tell it from a stored field.
- **Setters add validation on assignment** (`o.unit_price = 7` runs a validating method), so invariants (never negative) are enforced at the point of assignment while the caller writes plain assignment syntax, the interface never changes.
- **The payoff reshaped Python's culture**: because a plain field can always be upgraded to a property later with zero caller impact, there is no reason for defensive getters and setters, so "just use a public attribute" is the safe, idiomatic default (where Java writes accessors defensively).
- **Properties are descriptors on the class**, not values on the instance: accessing `o.total` finds the descriptor on `Order` and calls its `__get__`, which is the mechanism (Deep C) behind the "looks like an attribute, runs a method" magic.
- **The edges**: read-only by default (no setter means assignment raises), recomputation cost per access (use `cached_property` for expensive ones), overuse reintroduces boilerplate, and setters running during `__init__` can half-build an object.

**Cross-references.** New-style classes and descriptors → this volume, Deep C. The object model → Chapter 4. The values → Chapter 3. `cached_property` and caching → Chapters 34, 90. `dataclasses` → Deep Q. Price validation in the order book → Chapter 131. C++ accessors → Book I, Deep M.
