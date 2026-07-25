# Chapter 21: Attribute Access

Chapter 20 was about the attribute accesses the interpreter makes *implicitly*, `len(x)` reaching for `__len__`, `x + y` reaching for `__add__`, and how those bypass the normal machinery.
This chapter is about the accesses you write *explicitly*: `x.foo`, `x.foo = v`, `del x.foo`.
Every one of those is a call into a small, precise algorithm, and "it checks the instance, then the class" is not that algorithm.
The real order has a data descriptor beating the instance dict, a plain class attribute losing to it, and a fallback hook that fires only on failure, and getting that order wrong is behind a large fraction of "why is this attribute the value I did not set" bugs.

The dominant practical fact is a performance one, and it decides an API choice you will make repeatedly.
There are two hooks you can override to customise access: `__getattr__`, which runs **only when normal lookup fails**, and `__getattribute__`, which runs on **every access**.
Overriding the first is free for the attributes that already exist; overriding the second taxes every read by roughly **4.5x**.
Most "dynamic attribute" designs want the first and reach mistakenly for the second.

**This is the canonical home for ordinary attribute lookup.**
Chapter 20 owns special-method (implicit) dispatch; this chapter owns explicit `x.foo` access and its four hooks.
The **descriptor protocol itself**, what `__get__`/`__set__` do, how `property` and methods are built on it, and the C3 linearisation that orders the MRO the search walks, is **Deep C**; this chapter uses descriptors only to place them in the lookup order, it does not derive them.

## Section index

- **21.1** The two hooks: `__getattribute__` and `__getattr__`
- **21.2** The instance `__dict__`, shadowing, and the write hooks
- **21.3** The full lookup order `object.__getattribute__` implements
- **21.4** Measurement: the cost of each hook
- **21.5** Edges and failure modes
- **21.6** Connections
- **21.7** Exercises
- **21.8** Summary and cross-references

Listings live under `code/ch106/` and are re-executed by `make verify` on both verification interpreters.

---

## 21.1 The two hooks: `__getattribute__` and `__getattr__`

The names are one character apart and the behaviours could not be more different.
`__getattribute__` **is** the lookup algorithm, called unconditionally for every `x.foo`.
`__getattr__` is a **fallback**, called only when the algorithm fails to find the name.

```python
# code/ch106/l01_two_hooks.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- normal lookup resolves existing names; __getattr__ not consulted ---
  t.x  (class attribute)    : class-x
  t.y  (instance attribute) : instance-y
--- a MISSING name falls through to __getattr__ ---
  t.z  (no such attribute)  : __getattr__ fallback for 'z'
--- __getattr__ fires only on failure, so it is free for hits ---
  c.a (exists) : 1   (no __getattr__ line printed)
    __getattr__ called for 'missing'
  c.missing    : raised AttributeError (after the __getattr__ line)
```

`t.x` and `t.y` resolve normally, `__getattr__` is never consulted, because the name was found.
`t.z` does not exist, so the algorithm fails and `__getattr__` runs, synthesising a value.
The `Count` class makes the timing explicit: `c.a` prints no `__getattr__` line (the attribute exists, the fallback is skipped), while `c.missing` prints the line and then raises, because *this* `__getattr__` chose to raise `AttributeError` rather than invent a value.

That "only on failure" timing is the entire reason to prefer `__getattr__`.
A lazy attribute, a value fetched on first access, a compatibility shim for a renamed field, all of these want to run *only when the attribute is not already there*, which is exactly `__getattr__`'s contract.
`__getattribute__`, by contrast, is the sledgehammer: it intercepts *everything*, so it can implement a transparent proxy or an access log, but it pays for that reach on every single read (§21.4), and any bug in it breaks all attribute access on the object, including the internal accesses the object makes on itself.

---

## 21.2 The instance `__dict__`, shadowing, and the write hooks

Where do instance attributes live, and what happens when an instance and its class both define a name?

```python
# code/ch106/l02_instance_dict.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- instance attributes live in obj.__dict__ ---
  b.__dict__            : {'value': 10}
  b.label (from class)  : class-default
--- assigning an instance attribute SHADOWS the class attribute ---
  after b.label = ...   : instance-override   (instance dict wins)
  Box.label (unchanged) : class-default   (the class attr is untouched)
  b.__dict__            : {'value': 10, 'label': 'instance-override'}
--- del removes the instance attribute; the class attr re-emerges ---
  after del b.label     : class-default   (class attr visible again)
--- __setattr__ intercepts EVERY assignment ---
    __setattr__ 'count' = 1
  a.count : 1
--- the rule ---
  instance attrs live in __dict__ and shadow class attrs; writes go
  through __setattr__, deletes through __delattr__
```

By default an instance keeps its attributes in a per-object dict, `b.__dict__`.
`value` is there because `__init__` assigned it; `label` is not, so `b.label` reads the *class* attribute.
Assigning `b.label` puts `label` into the instance dict, and now `b.label` reads that, **shadowing** the class attribute, while `Box.label` itself is untouched (the class dict and the instance dict are different objects; the write only ever touched the instance's).
`del b.label` removes the instance entry, and the class attribute becomes visible again, it was never gone, only hidden.

Writes and deletes have their own hooks, symmetric to the read hooks: `__setattr__(self, name, value)` runs on *every* assignment (`b.label = ...` and `a.count = 1` both go through it), and `__delattr__` on every `del`.
The `Audited` class shows the pattern for a write interceptor: do your work, then call `object.__setattr__` to perform the actual store, forgetting that last step is the classic infinite-recursion bug (an `__setattr__` that assigns `self.name = value` calls itself forever).
There is no `__setattr__`-that-fires-only-on-new-names counterpart to `__getattr__`; writes always go through `__setattr__`.

---

## 21.3 The full lookup order `object.__getattribute__` implements

Now the algorithm itself, the ranked precedence that `object.__getattribute__` runs, and the two places intuition gets it wrong.

```python
# code/ch106/l03_lookup_order.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a DATA descriptor on the type beats the instance dict ---
  d.__dict__['attr']    : from-instance-dict
  d.attr                : from-data-descriptor   (data descriptor wins, rank 1 > 2)
--- a plain CLASS attribute does NOT beat the instance dict ---
  p.attr                : from-instance-dict   (instance dict wins, rank 2 > 3)
--- so the same 'shadowing' question has OPPOSITE answers ---
  data descriptor vs instance dict : descriptor wins
  plain class attr vs instance dict: instance wins
--- the rule ---
  order: data descriptor > instance __dict__ > class attr/non-data
  > __getattr__; this is what object.__getattribute__ does
```

The precedence, top to bottom:

1. **A data descriptor on the type** (a class attribute whose *type* defines `__set__` or `__delete__`), searched along the MRO.
2. **The instance `__dict__`.**
3. **A non-data descriptor or a plain class attribute** (searched along the MRO).
4. **`__getattr__`**, or, if there is none, `AttributeError`.

The two lines in the output are the counterintuitive corners.
In `D`, `attr` is a *data* descriptor and there is *also* an `attr` in the instance dict, and the descriptor wins: rank 1 beats rank 2.
In `P`, `attr` is a *plain* class attribute and there is an `attr` in the instance dict, and the instance dict wins: rank 2 beats rank 3.
So "does the instance dict shadow the class attribute?" has **opposite answers** depending on whether the class attribute is a data descriptor.
This is not a curiosity: it is exactly why a `@property` (a data descriptor) cannot be accidentally overwritten by `self.x = ...` inside `__init__` (the property intercepts the write), while a plain class-level default *is* silently shadowed by an instance assignment.
The mechanism, what makes something a data descriptor and how its `__get__`/`__set__` are invoked, is **Deep C**; the *position in the order* is what this chapter fixes.

The whole algorithm is `object.__getattribute__`.
When you override `__getattribute__`, you are replacing this entire procedure, which is why the safe idiom is to do your extra work and then delegate to `object.__getattribute__(self, name)` (as §21.1's proxy did) rather than reimplement four ranked lookups by hand.

---

## 21.4 Measurement: the cost of each hook

**Methodology.** `code/ch106/bench_access.py`.
Reading an *existing* attribute (`obj.x`) on three classes: a plain class, one adding `__getattr__`, and one overriding `__getattribute__`.
Because the attribute exists, `__getattr__` is never reached and `__getattribute__` always is, that is the comparison.
`min` of 5 runs, 10,000,000 reads each.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| reading an existing `obj.x` | ns/read | vs plain |
|---|---|---|
| plain class | 13.4 | 1.0x |
| `+ __getattr__` | 13.4 | 1.0x |
| `+ __getattribute__` | 59.9 | **4.5x** |

The result is the design rule in numbers.
Adding `__getattr__` costs **nothing** for existing attributes, 1.0x, identical within noise, because the fallback is never entered on a hit; it runs only on the misses, which by definition are the accesses that were going to fail anyway.
Overriding `__getattribute__` costs **4.5x** (the same direction on 3.14.6, ~4.1x), because a Python-level function now executes on every read before the real lookup happens, and the specializing interpreter can no longer take its fast `LOAD_ATTR` path (**Deep H**).

So: **to add lazy, synthesized, or fallback attributes, implement `__getattr__`.**
It is free for the common case and only pays on the names that were missing.
**Reach for `__getattribute__` only when you must observe or redirect *every* access**, a transparent proxy, an access audit, an attribute firewall, and accept that you have made every read on that object several times slower and disabled its attribute-access specialization.
The frequency with which the two are confused (because the names look alike) is why this measurement is worth carrying: the cheaper hook is also the one you almost always want.

---

## 21.5 Edges and failure modes

**`__getattr__` versus `__getattribute__` is a substitution error with a 4.5x price.** §21.4.
Want a fallback for missing names? `__getattr__`. Want to intercept every access? `__getattribute__`, knowingly.

**`__getattr__` that raises the wrong exception hides bugs.**
It must raise `AttributeError` for names it does not handle. Raising `KeyError` or returning `None` for everything breaks `hasattr`, `getattr(obj, x, default)`, and pickling (which probes `__reduce_ex__`, `__getstate__`, and others via attribute access).

**Recursion in `__setattr__`/`__getattribute__`.** §21.2.
Inside these hooks, use `object.__setattr__(self, ...)` / `object.__getattribute__(self, ...)` (or `super().`) to touch attributes. A plain `self.x = v` inside `__setattr__` calls `__setattr__` again, forever.

**Data descriptor versus instance dict is the shadowing gotcha.** §21.3.
A `@property` (or any data descriptor) is *not* shadowed by an instance attribute of the same name; a plain class default *is*. Mixing them silently produces the "I set `self.x` but reads still hit the property" confusion, and its inverse.

**`hasattr(x, name)` is not "the attribute is defined".**
`hasattr` returns `True` if access *succeeds*, which includes a value synthesized by `__getattr__` and excludes a real attribute whose descriptor raises. It answers "can I read this", not "is this stored".

**`__slots__` removes `__dict__`.**
A class with `__slots__` has no per-instance dict, so instance attributes live in fixed slot descriptors (data descriptors, hence rank 1) and arbitrary new attributes cannot be assigned. That is the subject of the next chapter; note here only that it changes §21.2's "attributes live in `__dict__`", they no longer do.

**Overriding access breaks introspection tools.**
A `__getattribute__` that redirects or a `__getattr__` that fabricates names can mislead `dir()`, debuggers, and serialization. Keep the fabricated surface small and honest.

---

## 21.6 Connections

**Backward.**
Chapter 20 covered *implicit* dispatch, which deliberately skips this entire algorithm; this chapter is the algorithm it skips. The `__dict__` that §21.2 reads and writes is the same `dict` object whose header cost Chapter 19 measured. `AttributeError`, the signal that drives the `__getattr__` fallback, is exceptions-as-control-flow (the language's founding choice).

**Forward.**
`__slots__`, which replaces the instance `__dict__` with fixed slot descriptors and changes both the memory profile and the lookup, is the next chapter. The descriptor protocol (`__get__`/`__set__`, data versus non-data, how `property`, `classmethod`, `staticmethod`, and bound methods are all descriptors) and the C3 MRO the search walks are **Deep C**. The specializing interpreter's `LOAD_ATTR` fast paths, and why overriding `__getattribute__` defeats them, are **Deep H**.

**Across books.**
`__getattr__` is how **Book I**'s dynamic wrappers stay ergonomic: a thin object that forwards missing names to an underlying handle (a C resource, a remote service, a data frame's columns) reads like a plain object at every call site while costing nothing for the names it defines directly. The order-book system's configuration and message objects lean on exactly this, defined fields are real attributes at full speed, and `__getattr__` supplies the long tail of optional fields without a dict lookup in the hot path, the payoff §21.4 measures.

---

## 21.7 Exercises

**1. Predict the winner.** For each pair, say which value `obj.attr` returns and why, using the §21.3 ranking:

```python
# (a) property on the class, assignment in __init__
class A:
    @property
    def attr(self): return "prop"
    def __init__(self): 
        try: self.attr = "inst"
        except AttributeError as e: self.err = str(e)
# (b) plain class default, assignment in __init__
class B:
    attr = "cls"
    def __init__(self): self.attr = "inst"
```

Then run it. Explain why (a) and (b) differ, and which rank each assignment landed in.

**2. Build a lazy attribute two ways.** Implement an attribute `expensive` that is computed on first access and cached, once with `__getattr__` and once with `__getattribute__`. Measure both against a plain precomputed attribute using §21.4's method. Explain why the `__getattr__` version is free after the first access and the `__getattribute__` version is not.

**3. The recursion trap.** Write a `__setattr__` that logs every assignment, using `self.log.append(...)`, and watch it recurse. Fix it. Then explain precisely which line re-entered the hook and why `object.__setattr__` (or `super().__setattr__`) breaks the cycle.

**4. Honest `__getattr__`.** Write a wrapper whose `__getattr__` forwards to an inner object. Make `hasattr(wrapper, "nope")` return `False` for a name the inner object also lacks, and explain what your `__getattr__` must do (which exception, when) to keep `hasattr`, `getattr(..., default)`, and `pickle` working.

**5. The design question.** Python could have made attribute access a single hook (`__getattr__` on every access, no separate `__getattribute__`). Argue, from §21.4 and the data-descriptor precedence of §21.3, what that would cost in performance and in the ability to have `property` coexist with instance state. Then argue the one thing it would simplify, and whether the two-hook split earns its complexity.

---

## 21.8 Summary and cross-references

- Explicit attribute access has two read hooks: **`__getattribute__`** runs on *every* access (it *is* the algorithm), **`__getattr__`** runs *only when lookup fails* (the fallback). Writes go through **`__setattr__`**, deletes through **`__delattr__`**, both on every operation.
- Instance attributes live in **`obj.__dict__`** and **shadow class attributes**; assigning does not touch the class, deleting reveals the class attribute again.
- The lookup order is **data descriptor > instance `__dict__` > non-data descriptor / class attribute > `__getattr__`**. So an instance attribute shadows a plain class attribute but *not* a data descriptor (a `property`), the source of a common shadowing surprise.
- **Measured:** adding `__getattr__` costs **1.0x** for existing attributes (free, never reached on a hit); overriding `__getattribute__` costs **4.5x** (a Python function on every read, and no `LOAD_ATTR` specialization). Prefer `__getattr__`; reach for `__getattribute__` only to intercept every access.
- **Recursion trap:** inside the hooks, touch attributes via `object.__…__`/`super()`, never `self.x = ...`.

**Cross-references.** Implicit dispatch that skips this algorithm → Chapter 20. The `__dict__` object's cost → Chapter 19. `__slots__` (no instance dict) → Chapter 22. Descriptors, `property`, and the C3 MRO → Deep C. `LOAD_ATTR` specialization → Deep H.
