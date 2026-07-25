# Chapter 32: The Descriptor Protocol

Deep A kept deferring one mechanism.
The lookup order in Chapter 21 ranked "data descriptor" above the instance dict without saying what a descriptor is.
`__slots__` in Chapter 22 turned out to be "member descriptors" and left it there.
`property` was named in three chapters as "a data descriptor" with a promise to explain later.
This is later.
A **descriptor** is an object that customizes what happens when an attribute *on a class* is read, assigned, or deleted, and it is one of the most load-bearing mechanisms in Python: `property`, `classmethod`, `staticmethod`, `__slots__`, and, most surprisingly, **ordinary methods** are all descriptors.
Understanding the protocol turns all of those from separate features into one idea.

The idea is small.
An object placed as a class attribute becomes a descriptor if its *type* defines `__get__`, `__set__`, or `__delete__`.
When you access that attribute, Python does not return the descriptor object; it calls the descriptor's `__get__` and returns *that*.
The whole of `property`, and the entire mechanism by which `self` gets bound into a method call, is this one redirection.

**This is the canonical home for descriptors.**
It pays off the promissory notes from Chapters 21 (the lookup ranking), 22 (`__slots__` as member descriptors), and 20 (methods living on the type).
It sits in Deep C alongside metaclasses (Chapter 31) and hands `property`/`classmethod`/`staticmethod` as *applications* to the next chapter; here we build the protocol they are built on.

## Section index

- **32.1** The protocol: `__get__`, `__set__`, `__delete__`, `__set_name__`
- **32.2** Data versus non-data descriptors, and methods as descriptors
- **32.3** Measurement: the cost of the descriptor indirection
- **32.4** Edges and failure modes
- **32.5** Connections
- **32.6** Exercises
- **32.7** Summary and cross-references

Listings live under `code/ch113/` and are re-executed by `make verify` on both verification interpreters.

---

## 32.1 The protocol: `__get__`, `__set__`, `__delete__`, `__set_name__`

```python
# code/ch113/l01_descriptor_protocol.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
  __set_name__: this descriptor is 'balance' on Account
--- (the __set_name__ line above ran during class creation) ---
--- read: __get__ ---
  a.balance : <unset>
--- assign: __set__ ---
  __set__: balance = 100
  a.balance : 100
--- delete: __delete__ ---
  __delete__: balance
  a.balance after delete : <unset>
--- access on the CLASS (obj is None) returns the descriptor ---
  type(Account.balance) : Logged
--- the rule ---
  a descriptor on a class intercepts get/set/delete of that attribute;
  __set_name__ tells it its own name at class-creation time
```

A descriptor is a class attribute whose *type* implements the protocol methods.
`Logged` implements all four:

- **`__get__(self, obj, objtype)`** runs when the attribute is read. It receives the *instance* (`obj`) and the class (`objtype`), and returns whatever the attribute should be. `a.balance` calls it and returns `<unset>` (the stored default).
- **`__set__(self, obj, value)`** runs on assignment. `a.balance = 100` calls it; here it stores into the instance's `__dict__` under the descriptor's own name.
- **`__delete__(self, obj)`** runs on `del`. `del a.balance` calls it.
- **`__set_name__(self, owner, name)`** runs *once*, at class-creation time, and tells the descriptor the attribute name it was assigned to. The output shows it firing during `class Account:` execution, before any instance exists. This is why a modern descriptor does not need to be told its name; it learns it (`self.name = "balance"`).

Two structural facts matter.
The descriptor is stored **on the class**, once, and shared by all instances, so its methods receive the instance as an argument rather than being bound to one, that is why `__get__` takes `obj`.
And when accessed **on the class itself** rather than an instance (`Account.balance`), `obj` is `None`, and the convention (which `Logged` follows) is to return the descriptor object, so that `Account.balance` gives you the descriptor to introspect while `a.balance` gives you the value.
This is the pattern `property` uses so that `SomeClass.some_property` returns the property object.

---

## 32.2 Data versus non-data descriptors, and methods as descriptors

The protocol methods a descriptor implements determine its *precedence*, and this is the piece that completes Chapter 21's lookup order and explains method binding.

```python
# code/ch113/l02_data_and_methods.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a NON-data descriptor is shadowed by the instance dict ---
  a.attr : from instance dict   (instance dict wins over non-data descriptor)
--- a DATA descriptor outranks the instance dict ---
  b.attr : from data descriptor   (data descriptor wins; instance dict ignored)
--- a plain function IS a non-data descriptor ---
  M.greet has __get__     : True
  M.greet (on class)      : function   (plain function)
--- accessing it on an instance calls __get__ -> a BOUND METHOD ---
  m.greet (on instance)   : method   (bound method)
  m.greet.__self__ is m   : True   (self is bound in)
  m.greet()               : hello
--- the rule ---
  __set__/__delete__ => data descriptor (outranks instance dict);
  __get__ only => non-data (shadowable). Functions bind self via __get__
```

**The two kinds.**
A descriptor that defines `__set__` or `__delete__` is a **data descriptor**; one that defines only `__get__` is a **non-data descriptor**.
The distinction sets precedence, exactly Chapter 21's ranking:

- A **data** descriptor **outranks the instance `__dict__`**: `b.attr` returns the descriptor's value even though `b.__dict__["attr"]` exists. This is why a `property` cannot be accidentally overwritten by `self.attr = ...`, the property's `__set__` intercepts the write.
- A **non-data** descriptor is **shadowed by the instance `__dict__`**: `a.attr` returns the instance value, not the descriptor's. This is deliberate, it lets an instance override a class-level default.

**Methods are descriptors.**
The revelation that ties the object model together: a plain function is a **non-data descriptor** (`M.greet` has `__get__`).
Accessed on the class, `M.greet` is just the function.
Accessed on an *instance*, `m.greet` triggers the function's `__get__`, which returns a **bound method**, an object that packages the function with `m` as `self` (`m.greet.__self__ is m`), so calling `m.greet()` invokes `greet(m)`.
Method binding is not special machinery; it is the descriptor protocol applied to functions.
And because functions are *non-data* descriptors, you can shadow a method on a single instance by assigning `m.greet = something` (the instance dict outranks the non-data descriptor), a rarely-wanted but occasionally-useful capability that falls straight out of the precedence rule.

So the whole of Chapter 21's lookup order is now explained: `object.__getattribute__` checks data descriptors first (they win), then the instance dict, then non-data descriptors and plain class attributes, and the ranking *is* the data/non-data distinction.

---

## 32.3 Measurement: the cost of the descriptor indirection

A descriptor turns an attribute access into a function call, and that has a price worth knowing before you reach for `property`.

**Methodology.** `code/ch113/bench_property.py`.
A trivial `property` (getter returns a stored value) versus a plain stored attribute, read 10,000,000 times, `min` of 5 runs.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| attribute read | ns | vs plain |
|---|---|---|
| plain attribute | 13.5 | 1.0x |
| `property` (getter) | 23.0 | **1.7x** |

A `property` read costs **1.7x** a plain attribute read (1.8x on 3.14.6), because reading it runs the descriptor's `__get__`, which calls your getter function, where a plain attribute is a direct dict-or-slot fetch.
That is the correct price *when the property earns it*: computing a derived value, validating on set, making an attribute read-only, presenting a stored value under a different name.
It is *wasted* when the property merely returns a stored value unchanged.

The design guidance is specific and is one of Python's genuine advantages over languages that force it.
In Java or C#, the convention is to wrap every field in a getter/setter *up front*, because exposing a public field and later needing accessors is a binary-incompatible API change.
Python has no such tax: `obj.x` is the same syntax whether `x` is a plain attribute or a property, so you can **start with a plain attribute and convert it to a property later without changing a single call site.**
Therefore: do not pre-emptively wrap stored values in pass-through properties "for future-proofing", that doubles every read for a flexibility you can add for free the day you need it.
Use `property` when there is *actual* computation, validation, or protection to do, and use a plain attribute otherwise.
This is the same Deep-A-and-C refrain: the mechanism has a real cost, spend it where it buys something.

---

## 32.4 Edges and failure modes

**Descriptors only work on the class, not the instance.** §32.1.
A descriptor must be a *class* attribute. Putting a descriptor object in an instance's `__dict__` does nothing, the protocol is only invoked for class attributes (this mirrors special methods, Chapter 20).

**Data versus non-data is decided by `__set__`/`__delete__` presence.** §32.2.
Defining `__set__` (even one that raises) makes a descriptor a *data* descriptor and changes its precedence. A read-only property still defines `__set__` (to raise `AttributeError`), which is what keeps the instance dict from shadowing it.

**Storing state on the descriptor is a shared-state bug.**
A descriptor is one object shared by all instances of the class. Storing per-instance data as `self.value` *on the descriptor* means every instance overwrites the same slot. Store per-instance state in the *instance's* `__dict__` (keyed by the name `__set_name__` gave you), as §32.1 does, not on the descriptor.

**`__set_name__` is 3.6+ and fires only at class creation.**
It does not fire if you attach a descriptor to a class *after* creation (`SomeClass.attr = Descriptor()`); then you must set the name yourself. It also does not fire for descriptors created dynamically outside a class body.

**A non-data descriptor is shadowable; a data descriptor is not.** §32.2.
If you need an attribute that an instance can override, use a non-data descriptor (only `__get__`). If you need one that always intercepts, make it a data descriptor.

**Method binding creates a new bound-method object per access.**
`m.greet` builds a fresh bound-method object each time (the `__get__` call). In a hot loop, repeatedly accessing `obj.method` re-binds each iteration; hoist the bound method (`f = obj.method`) or the underlying function if it matters. The specializing interpreter (**Deep H**) optimizes the common `obj.method()` call pattern.

**`functools.cached_property` is a non-data descriptor with a subtlety.**
It computes once and stores the result in the instance `__dict__`, and because it is *non-data*, the stored value then shadows it on subsequent reads (that is how the caching works). This also means a class with `__slots__` and no `__dict__` cannot use `cached_property`.

---

## 32.5 Connections

**Backward.**
The descriptor protocol *is* the missing piece of Chapter 21's attribute-lookup ranking (data descriptor > instance dict > non-data/class attribute), now fully explained. `__slots__`'s member descriptors (Chapter 22) are data descriptors, which is why a slot cannot be shadowed by an instance attribute. Methods living on the type (Chapter 20) plus the descriptor protocol together explain how `self` is bound. `__set_name__` firing at class creation is a class-creation hook alongside `__init_subclass__` (Chapter 31).

**Forward.**
`property`, `classmethod`, and `staticmethod`, all descriptors, are the next chapter's subject, built directly on this protocol. The C3 MRO (which orders the class search a descriptor lookup walks) and `super()` are later in Deep C. How the specializing interpreter caches method loads (`LOAD_METHOD`) to avoid rebuilding bound methods is **Deep H**.

**Across books.**
Descriptors are how **Book I** builds reusable, validated attributes without boilerplate: a `Positive` or `Typed` descriptor written once enforces its invariant on every field that uses it, so a domain object declares `price = Positive()` and gets validation on every assignment, in one line, at the class level. The order-book system uses descriptors for its validated numeric fields (prices non-negative, quantities integral) so that an invalid value is rejected at assignment by the field's `__set__`, the §32.1 mechanism, rather than by scattered checks, and it keeps trivial fields as plain attributes for the §32.3 speed.

---

## 32.6 Exercises

**1. Implement the protocol.** Reproduce §32.1: a descriptor with all four methods that stores in the instance dict and logs. Confirm `__set_name__` fires at class creation, and that class-level access returns the descriptor. Explain why per-instance state goes in the instance dict, not on the descriptor.

**2. Data versus non-data.** Reproduce §32.2: show a non-data descriptor shadowed by an instance attribute and a data descriptor that is not. Then make a read-only data descriptor (a `__set__` that raises) and confirm an instance cannot shadow it. Explain the precedence.

**3. Watch a method bind.** Take a class method, access it on the class (a function) and on an instance (a bound method), and confirm `__self__`. Then bind it manually via `Class.method.__get__(instance)`. Explain how this is method binding.

**4. Measure and decide.** Reproduce §32.3. Then write a property that *computes* something (not a pass-through) and argue why its cost is justified where the pass-through's is not. State the rule for when to use `property`.

**5. The design question.** Python implements `property`, methods, `classmethod`, and `__slots__` all as descriptors rather than as four special-cased features. Argue what that unification buys (name a fifth thing you can build with the same protocol), and what it costs (the §32.4 shared-state and data/non-data subtleties). Would explicit getter/setter syntax have been simpler? Defend your answer using §32.3's "convert later for free".

---

## 32.7 Summary and cross-references

- A **descriptor** is a class attribute whose type defines **`__get__`**, **`__set__`**, or **`__delete__`**; accessing the attribute invokes those instead of returning the descriptor. **`__set_name__`** tells it its name once, at class creation.
- **Data descriptor** (defines `__set__`/`__delete__`) **outranks the instance `__dict__`**; **non-data descriptor** (only `__get__`) is **shadowed by it**. This *is* Chapter 21's lookup ranking.
- **Methods are descriptors:** a plain function is a non-data descriptor whose `__get__` returns a **bound method** with `self` supplied. Method binding is the descriptor protocol applied to functions.
- **Measured:** a trivial `property` read costs **1.7x** a plain attribute (23.0 vs 13.5 ns), because it runs a getter call. Spend that only for real computation/validation; start with a plain attribute and convert to a property later *for free* (same call syntax).
- **Edges:** descriptors work only as class attributes; store per-instance state in the instance dict (the descriptor is shared); `__set_name__` fires only at class-body creation; `cached_property` is non-data and needs a `__dict__`.

**Cross-references.** The attribute-lookup ranking this completes → Chapter 21. `__slots__` member descriptors → Chapter 22. Methods on the type, `self` binding → Chapter 20. `property`/`classmethod`/`staticmethod` built on this → next chapter (Deep C). MRO, `super()` → Deep C. `LOAD_METHOD` specialization → Deep H.
