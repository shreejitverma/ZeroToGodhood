# Chapter 26: Truthiness and the Singletons

`if x:` is the most common line in Python, and most people cannot say exactly what it does.
It does not test `x != 0` or `x is not None` or `len(x) > 0`; it computes `bool(x)`, and `bool` runs a small protocol that consults the object's `__bool__`, then its `__len__`, then a default.
Getting this protocol exact matters because its edges are where real bugs live: an empty container is falsy, so `if results:` silently skips work when `results` is `[]`, and a custom object with a `__len__` becomes falsy when its length hits zero, sometimes to your surprise.

Alongside truthiness sits a second small topic that belongs in the object model because it is *about identity*: the **singletons**.
Python guarantees exactly one `None`, one `True`, one `False`, one `Ellipsis`, one `NotImplemented`, and because there is exactly one of each, you test for them with `is`, not `==`.
This is not a style preference.
`x is None` is an unforgeable identity check; `x == None` dispatches `x`'s `__eq__`, which can be slower (measured: **3.8x**) and, worse, *wrong* if the class's equality is unusual.

**This is the canonical home for truthiness and the language singletons.**
It uses Chapter 19 (the singletons are the immortal objects, and `is` is the address comparison), Chapter 20 (`bool`, `len`, and `==` are special-method dispatch), and Chapter 23 (`is` versus `==`, here applied specifically to `None`).

## Section index

- **26.1** The `bool(x)` protocol: `__bool__`, then `__len__`, then `True`
- **26.2** The singletons, and why `is None` beats `== None`
- **26.3** Measurement: the cost of `== None`
- **26.4** Edges and failure modes
- **26.5** Connections
- **26.6** Exercises
- **26.7** Summary and cross-references

Listings live under `code/ch111/` and are re-executed by `make verify` on both verification interpreters.

---

## 26.1 The `bool(x)` protocol: `__bool__`, then `__len__`, then `True`

```python
# code/ch111/l01_truthiness.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- branch 1: __bool__ decides directly ---
  bool(HasBool()) : False
--- branch 2: no __bool__, so __len__ decides (falsy iff len == 0) ---
  bool(HasLen(0)) : False   bool(HasLen(3)) : True
--- branch 3: neither defined, so the object is always truthy ---
  bool(Neither()) : True
--- __bool__ takes precedence over __len__ ---
  bool(Both()) : True   (__bool__=True beats __len__=0)
--- the standard falsy values (all bool() to False) ---
  0, 0.0, '', [], {}, (), set(), None, False, range(0)
  all falsy : True
--- the rule ---
  bool(x): __bool__ if defined, else __len__==0 test, else True;
  'if x:' uses this, so define __bool__ or __len__ to be falsy
```

The protocol, in order:

1. **`__bool__`**, if the type defines it, decides directly and must return a `bool`. `HasBool` returns `False`.
2. **`__len__`**, if there is no `__bool__`, decides by length: the object is falsy exactly when `len(x) == 0`. `HasLen(0)` is falsy, `HasLen(3)` is truthy. This is why *every empty container is falsy*, `[]`, `{}`, `""`, `set()`, `()`, they all report `__len__` of 0.
3. **Default `True`**: an object with neither is always truthy. `Neither()` is `True`, and so is every plain object, a function, a module, a class instance without these methods.

`Both` shows the precedence: with both defined, `__bool__` wins, so `bool(Both())` is `True` even though `__len__` is 0.
The order is not arbitrary, it lets a type that *has* a length still declare a truthiness independent of it (a one-element "empty sentinel", say).

The falsy set is worth memorising because `if x:` tests membership in it: `0`, `0.0`, `0j`, `""`, `[]`, `{}`, `()`, `set()`, `range(0)`, `None`, and `False` are falsy; **everything else is truthy**.
The practical consequence, and the bug this section exists to prevent, is that `if x:` and `if x is not None:` are *different tests*.
For a value that might legitimately be `0`, `""`, or `[]`, `if x:` treats those as "absent" when you may have meant "present but empty".
When you mean "is this `None`", write `if x is not None:`; reserve `if x:` for genuine emptiness/zero tests where the falsy values all mean the same thing.

---

## 26.2 The singletons, and why `is None` beats `== None`

```python
# code/ch111/l02_singletons.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the singletons: exactly one object each ---
  None is None       : True
  Ellipsis is ...    : True
  NotImplemented is NotImplemented : True
  type(None) : NoneType   type(...) : ellipsis
--- 'is None' is correct even when __eq__ lies ---
  b == None : True   (wrong: __eq__ returns True for anything)
  b is None : False   (correct: b is not the None object)
--- so a None check must use identity ---
  '== None' would say None : True
  'is None' says None      : False
--- the rule ---
  test singletons (None, True, False, ..., NotImplemented) with 'is',
  never '=='; 'is None' cannot be fooled by __eq__ and is faster
```

Python guarantees a single instance of each of these objects: `None` (of type `NoneType`), `True`/`False`, `Ellipsis` (spelled `...`, of type `ellipsis`), and `NotImplemented`.
They are immortal (Chapter 19) and process-global, so identity is a total test: `None is None` is trivially `True`, and *nothing else in the program is `None`*.
That guarantee is what makes `is` the right operator, `x is None` asks "is `x` literally the one `None` object", which is exactly the question, and it is a pointer comparison that no code can intercept.

`== None` asks a different, weaker question: "does `x.__eq__(None)` say they are equal", and `__eq__` is user-defined.
`BrokenEq` has an `__eq__` that returns `True` for everything, so `b == None` is `True` even though `b` is plainly not `None`, and any `if value == None:` guarded by such an object takes the wrong branch.
`b is None` stays `False`, correct, because identity cannot be overridden.
The broken case is pathological, but the principle is not: a class only has to handle `None` carelessly in its `__eq__` (or return `NotImplemented` in a way that flips the result) for `== None` to mislead, and you rarely control every type that flows through a `None` check.

So the rule is unconditional: **test singletons with `is`.**
`x is None`, `x is True`, `x is not None`, `result is NotImplemented`, never the `==` forms.
It is correct by construction (identity cannot be forged) and, as the next section measures, faster.
Linters enforce this (`E711`/`E712` flag `== None` and `== True`) precisely because the `==` form is a latent correctness bug, not merely slow.

---

## 26.3 Measurement: the cost of `== None`

**Methodology.** `code/ch111/bench_none.py`.
Testing an object with a custom `__eq__` against `None`, two ways: `x is None` (identity) and `x == None` (dispatch `__eq__`).
`min` of 5 runs, 10,000,000 tests.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| test against `None` | ns/test | vs `is` |
|---|---|---|
| `x is None` (identity) | 13.9 | 1.0x |
| `x == None` (dispatch `__eq__`) | 52.3 | **3.8x** |

`== None` is **3.8x** slower (4.2x on 3.14.6) for an object with a Python-level `__eq__`.
The reason is the whole point of the object model: `is` is a single pointer comparison the interpreter does inline, while `==` runs the operator protocol of Chapter 20, look up `__eq__` on the type, call it (a Python function here), inspect for `NotImplemented`, possibly try `None`'s reflected `__eq__`.
That is a method call and a protocol where `is` is one machine comparison.

The measurement reinforces a rule that was *already* justified on correctness grounds alone (§26.2), and that combination is the point: `is None` is not a micro-optimization you trade against readability, it is simultaneously the **correct** test (identity cannot be overridden), the **faster** test (3.8x here), and the **clearer** test (it says "is this the None object", which is what you mean).
There is no axis on which `== None` wins.
This is the cleanest kind of rule, one where correctness, performance, and clarity all point the same way, and it is worth stating plainly because the `==` habit is common and the failure mode (a wrong branch under an unusual `__eq__`) is silent.

---

## 26.4 Edges and failure modes

**`if x:` is not `if x is not None:`.** §26.1.
For values that can legitimately be `0`, `""`, `[]`, or `{}`, truthiness treats those as false. When you mean "not `None`", write `is not None`; when you mean "empty or zero", use truthiness.

**Test singletons with `is`, not `==`.** §26.2, §26.3.
`is None`/`is True`/`is not None`. The `==` forms are slower and can be wrong under a custom `__eq__`.

**Do not write `if x == True:` or `if x is True:` to test truthiness.**
To test whether `x` is truthy, write `if x:`. `is True` checks for the *specific* `True` object (so `if 1 is True:` is `False`), and `== True` invites the `__eq__` problems above. Reserve `is True`/`is False` for the rare case where you must distinguish the boolean singleton from other truthy/falsy values.

**`__bool__` must return an actual `bool`.**
Returning `1`, `0`, or a truthy object from `__bool__` raises `TypeError` (`__bool__ should return bool`). Return `True`/`False`.

**`__len__` must return a non-negative `int`.**
A `__len__` returning a negative number raises `ValueError`, and one returning a non-`int` raises `TypeError`. If a type's "emptiness" is expensive to compute or unrelated to a length, define `__bool__` instead of abusing `__len__`.

**Truthiness via `__len__` can be expensive.**
`if x:` on a type whose `__bool__` is absent calls `__len__`, and if computing the length is costly (materializing a lazy sequence, a database count), every `if x:` pays it. Define a cheap `__bool__` for such types.

**`NotImplemented` is truthy and must not be used in boolean context.**
`bool(NotImplemented)` is deprecated and will raise in a future version. `NotImplemented` is a return sentinel for comparison/arithmetic dunders (Chapter 20), not a truth value.

**`Ellipsis` (`...`) is a real object with uses.**
Beyond type stubs (`def f() -> int: ...`), `...` is used by NumPy for full-slice indexing and by some APIs as a distinct sentinel. It is truthy and a singleton; test with `is ...`.

---

## 26.5 Connections

**Backward.**
The singletons are Chapter 19's immortal objects, and `is` is its address comparison; this chapter applies both to control flow. `bool(x)`, `len(x)`, and `==` are special-method dispatch (Chapter 20), which is why `__bool__`/`__len__` are looked up on the type and why `== None` runs the operator protocol. `is` versus `==` in general is Chapter 23; here it is specialised to the singletons, where identity is not just *a* valid test but *the* correct one.

**Forward.**
`NotImplemented`'s role in comparison and arithmetic fallback is Chapter 20 (and recurs whenever you write a dunder). Using a *custom* sentinel object (a module-level `_MISSING = object()`) to distinguish "no argument" from "argument was `None`", the pattern that generalises the singleton idea to your own code, is an idioms topic in **Deep C**. `Ellipsis` in indexing is **Deep T** (NumPy).

**Across books.**
The `None`-check discipline is a correctness seam in **Book I**: a pipeline that distinguishes "missing" (`None`) from "present but empty" (`[]`, `0`, `""`) has to use `is None`, because truthiness would collapse the two and a custom `__eq__` would make `== None` unreliable. The order-book system uses a dedicated sentinel (not `None`) for "no resting order at this level" precisely so that a real order carrying a zero quantity is never mistaken for absence, the §26.4 "`if x:` is not `is not None`" trap, avoided by design, and every singleton test in its hot path is `is`, both for the correctness of §26.2 and the speed of §26.3.

---

## 26.6 Exercises

**1. Trace the protocol.** Reproduce §26.1: build classes exercising each branch (`__bool__` only, `__len__` only, neither, both) and predict then verify `bool()` of each. Explain the `__bool__`-over-`__len__` precedence and why empty containers are falsy.

**2. Find the `if x:` bug.** Write a function that returns a list of results and a caller that does `if results:`. Show that it wrongly skips the "empty but valid" case, then fix it with `is not None` where appropriate. Explain which falsy value caused the bug.

**3. Break `== None`.** Reproduce §26.2's `BrokenEq`. Write a `find(items, target)` that uses `== None` to detect a missing default and show it misbehaves when `items` contains a `BrokenEq`. Fix it with `is None` and explain why identity is immune.

**4. Measure it.** Reproduce §26.3 for both a plain object and one with a custom `__eq__`, comparing `is None` and `== None`. Explain why the gap is larger for the custom-`__eq__` object, in terms of Chapter 20's dispatch.

**5. The design question.** Python makes *every* object truthy by default and lets containers opt into falsiness via `__len__`. Argue why this is a better default than requiring an explicit `__bool__` everywhere, using the empty-container case. Then argue the cost (the §26.4 "expensive `__len__`" and "`if x:` is not `is not None`" traps) and whether a separate "emptiness" protocol would have been cleaner.

---

## 26.7 Summary and cross-references

- **`bool(x)`** (what `if x:`, `while x:`, `not`, and boolean operators use) follows a fixed protocol: **`__bool__`** if defined, else **`__len__` == 0** test, else **`True`**. `__bool__` takes precedence over `__len__`.
- The **falsy** values are `0`, `0.0`, `""`, `[]`, `{}`, `()`, `set()`, `range(0)`, `None`, `False`; **everything else is truthy**. So `if x:` is *not* the same as `if x is not None:`.
- Python has one each of the **singletons** `None`, `True`, `False`, `Ellipsis` (`...`), `NotImplemented`. **Test them with `is`, never `==`.**
- **`is None` beats `== None` on every axis:** correct (identity cannot be overridden, `== None` can be wrong under a custom `__eq__`), **faster** (measured **3.8x**: 13.9 vs 52.3 ns), and clearer.
- **Edges:** `__bool__` must return a `bool`, `__len__` a non-negative `int`; an expensive `__len__` makes `if x:` expensive (define `__bool__`); `NotImplemented` is not a truth value; `...` is a real singleton.

**Cross-references.** Singletons as immortal objects, `is` as address comparison → Chapter 19. `bool`/`len`/`==` as special-method dispatch, `NotImplemented` → Chapter 20. `is` versus `==` in general → Chapter 23. Custom sentinels and the `_MISSING = object()` idiom → Deep C. `Ellipsis` in indexing → Deep T.
