# Chapter 11: Augmented Assignment

Python 2.0 (2000) opens the 2.x ascent, and among its additions was a small convenience that exposes one of the language's deepest distinctions: **augmented assignment**, `x += 1` for `x = x + 1`, and its siblings `-=`, `*=`, `+=`, and the rest. The convenience is real, and for immutable types it is pure sugar. But for *mutable* types, `+=` does something `= +` does not, it mutates the object in place, and the difference between mutating an object and rebinding a name is one of Python's most instructive gotchas.

This is a release chapter under the two-track rule: augmented assignment *uses* the object model (Chapter 4), it does not derive it, and the mechanism, mutation versus rebinding, names versus objects, is owned by Deep A. What this chapter owns is the release framing: 2.0 added `+=` for convenience, and in doing so surfaced the mutation-versus-rebinding line that was always present in Python's object model but rarely so visible. The listing demonstrates both faces on the verification interpreters, the sugar and the trap, including the famous "half-completing" tuple-of-list case that proves `+=` is *mutate-then-rebind*, two steps that can disagree.

## Section index

- **11.1** The constraint: a convenience that had to respect the object model
- **11.2** Immutable: += is pure sugar
- **11.3** Mutable: += mutates in place
- **11.4** The trap: += through a shared reference
- **11.5** The half-completing gotcha: mutate-then-rebind
- **11.6** Edges: where the distinction bites
- **11.7** Connections
- **11.8** Exercises
- **11.9** Summary and cross-references

Listings live under `code/ch221/` and are re-executed by `make verify` on the verification interpreters.

---

## 11.1 The constraint: a convenience that had to respect the object model

`x = x + 1` is common enough that a shorthand is worth having, most languages provide `+=`, and Python 2.0 added it. But Python's object model (Chapter 4) posed a design question C's did not. In C, `x += 1` unambiguously modifies the storage named `x`, because `x` *is* storage (a variable is a typed box). In Python, `x` is a *name bound to an object* (Deep A), and "add to `x`" could mean either "modify the object `x` names" or "rebind `x` to a new object", and for different types the answers differ.

Python resolved it with a protocol: `+=` calls the object's `__iadd__` ("in-place add") method if it has one, and falls back to `__add__` (building a new object) if it does not. Immutable objects (int, str, tuple) cannot modify themselves, so they have no meaningful `__iadd__` and `+=` rebinds to a new object, identical to `= +`. Mutable objects (list, set, dict-via-`|=`) implement `__iadd__` to modify in place, so `+=` changes the existing object. The convenience had to respect the object model's names-versus-objects distinction, and it does, by dispatching to the object's own in-place protocol, which is why `+=` means two different things for the two kinds of type.

---

## 11.2 Immutable: += is pure sugar

```python
# code/ch221/l01_augmented_assignment.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- for immutable types, += is pure sugar (new object) ---
  int x += 5 : value 15, new object : True
  str s += 'cd' : value 'abcd', new object : True
  immutable objects cannot change, so += REBINDS to a new object -
  identical to x = x + 5. no surprise here
```

**For immutable types, `+=` rebinds to a new object, exactly like `= +`.**
`x += 5` produces a new integer (the `id` changes), because an integer cannot modify itself, immutability (Deep A) means the object `15` is a different object from `10`, and `x` is rebound to it. Same for strings: `s += 'cd'` builds a new string and rebinds `s`. There is no in-place mutation because there *cannot* be, and so `+=` on an immutable is pure syntactic sugar for `= +`, with no observable difference in identity beyond what `= +` would also produce. This is the no-surprise case, and it is why `x += 1` in a loop counter behaves exactly as expected, integers are immutable, so `+=` just rebinds.

**The immutable case also warns about `+=` in a loop over strings.**
Because `s += piece` rebinds `s` to a *new* string each time, building a string by repeated `+=` is quadratic (each rebind copies the growing string, Chapter 74's accumulation lesson), the same cost as `s = s + piece`. The `+=` syntax hides that a new object is built each iteration, and the fix is `''.join(pieces)` (Chapter 74, Chapter 9). So even the "no surprise" immutable case has a performance edge: `+=` on an immutable is convenient but not free, and for accumulation the in-place-looking syntax is a quadratic trap.

---

## 11.3 Mutable: += mutates in place

```text
--- for mutable types, += mutates IN PLACE (same object) ---
  list a += [3,4] : [1, 2, 3, 4], SAME object : True
  list b = b+[3,4]: [1, 2, 3, 4], NEW object  : True
  a += b calls list.__iadd__ (in-place extend); a = a+b builds a
  NEW list. same result value, DIFFERENT object identity - and
  that difference is the whole gotcha
```

**For mutable types, `+=` modifies the existing object while `= +` builds a new one, and that identity difference is the gotcha.**
`a += [3, 4]` keeps the *same* list object (the `id` is unchanged) and extends it in place, because `list.__iadd__` mutates. `b = b + [3, 4]` builds a *new* list and rebinds `b` (the `id` changes), because `list.__add__` returns a new object. The two produce the same *value* (`[1, 2, 3, 4]`) but different *identity*, and identity is what matters when the object is shared. This is the whole subtlety: `+=` and `= +` look interchangeable and are not, for mutable types they differ in whether the operation mutates or rebinds, which is invisible in the result value and decisive in the object graph.

**`list.__iadd__` is `list.extend`, and knowing that demystifies it.**
`a += b` for lists is equivalent to `a.extend(b)`, an in-place modification, where `a = a + b` is `a = list(a) + list(b)`, a new-object construction. Once you see `+=` as "call the in-place method" and `= +` as "build new and rebind", the behaviour is not a gotcha but a consequence, mutable objects have in-place methods, immutable ones do not, and `+=` dispatches accordingly. The confusion comes from the *syntax* looking uniform while the *semantics* branch on mutability, which is the object model (Chapter 4) surfacing in operator form.

---

## 11.4 The trap: += through a shared reference

```text
--- the trap: += through a shared reference ---
  after shared += [3]: shared=[1, 2, 3], alias=[1, 2, 3]
  the alias sees the change : True
  after other = other+[3]: other=[1, 2, 3], other_alias=[1, 2]
  the alias does NOT see it  : False
```

**When a mutable object is shared, `+=` changes it for *every* reference; `= +` changes it for none.**
`alias = shared` makes two names for one list; `shared += [3]` mutates that one list in place, so `alias`, pointing at the same object, sees `[1, 2, 3]`. But `other = other + [3]` builds a new list and rebinds *only* `other`; `other_alias` still points at the old, unchanged list `[1, 2]`. This is Chapter 4's names-versus-objects distinction in the code you write every day: `+=` acts on the *object* (all aliases see it), `= +` acts on the *name* (aliases keep the old object). The trap is real, a function that does `param += items` mutates the caller's list (surprising), where `param = param + items` does not, and the difference is exactly which of the two operations the code used.

**This is the most common real-world manifestation, and its fix is knowing the distinction.**
A function that "appends to a list argument" via `arg += extra` has a side effect on the caller's list, often unintended; the same function via `arg = arg + extra` has no such effect but also does not communicate the change back. Neither is wrong, but they are *different*, and choosing correctly requires knowing whether you want to mutate the shared object or rebind a local name. The bug is using `+=` expecting `= +`'s no-side-effect behaviour (or vice versa), and it is common precisely because the syntax hides the semantic branch on mutability and sharing.

---

## 11.5 The half-completing gotcha: mutate-then-rebind

```text
--- the tuple-of-list trap: += that both works AND raises ---
  t[0] += [3] raised TypeError...
  ...but the list WAS mutated anyway : [1, 2, 3]
  the famous gotcha: += on a list inside a tuple mutates the list
  (in-place succeeds) then tries to reassign t[0] (tuple item
  assignment fails). the operation half-completes - proof that +=
  is mutate-THEN-rebind, and the two steps can disagree
```

**The famous case: `t[0] += [3]` on a list inside a tuple both mutates the list *and* raises, proving `+=` is two steps.**
`t = ([1, 2],)` is a tuple holding a list. `t[0] += [3]` does two things: first it calls `list.__iadd__` on `t[0]` (mutating the list in place, which *succeeds*, the list becomes `[1, 2, 3]`), then it tries to *rebind* `t[0]` to the result (which *fails*, because tuples do not allow item assignment, raising `TypeError`). The operation half-completes: the mutation happened, the rebind did not, and the list is left modified even though an exception was raised. This is the single clearest proof that `+=` is **mutate-then-rebind**, two distinct steps, and that they can disagree, the mutation on a mutable object stored in an immutable container succeeds while the container's rebinding fails.

**The lesson is the whole chapter, distilled.**
`x += y` is not one atomic operation; it is "compute `x.__iadd__(y)` (or `x + y`), then bind the result to `x`". For most cases the two steps are consistent, but the tuple-of-list case forces them apart and shows the machinery: the in-place step ran and mutated, the rebind step ran and raised. Understanding this resolves every `+=` gotcha, the shared-reference trap (§11.4) is the mutate step being visible through aliases; the immutable case (§11.2) is the mutate step being a no-op so only the rebind matters. `+=` is mutate-then-rebind, and knowing that is knowing augmented assignment.

---

## 11.6 Edges: where the distinction bites

**Default mutable arguments amplify the trap.**
A function `def f(items=[]): items += [x]` mutates the *shared default list* (the default is created once, Deep A's famous gotcha), so every call sees the accumulated list. The `+=` mutation compounds the mutable-default bug, and the fix is `items=None` with `items = items or []` inside, sidestepping both the shared default and the in-place mutation.

**`+=` on a dict value that is a list.**
`d[key] += [x]` mutates the list at `d[key]` in place (if it exists) or raises `KeyError` (if it does not), the `defaultdict(list)` pattern exists precisely to make `d[key] += [x]` or `d[key].append(x)` work without the key-check. The in-place semantics interact with the container's key handling, another place the mutate-then-rebind machinery shows.

**Numpy arrays make `+=` a performance feature.**
For numpy arrays (Deep T), `a += b` mutates in place (no new array allocated) while `a = a + b` allocates a new array; for large arrays this is a real memory-and-speed difference, and numeric code uses `+=` deliberately to avoid allocation. The mutable-in-place semantics that trap list users are a *feature* for array users, the same mechanism, opposite value, depending on whether in-place mutation is wanted.

**And `+=` is not thread-safe on shared mutables.**
Under the free-threaded build (Chapter 96) or any threading, `shared += [x]` on a list shared across threads is a read-modify-write that can race (Chapter 99), the in-place mutation is not atomic against concurrent access. The mutate-then-rebind machinery is single-threaded-safe only under the GIL's coarse serialisation, and shared-mutable `+=` needs the locking discipline of Chapter 99.

---

## 11.7 Connections

**Backward.**
The object model, names versus objects, mutability, that `+=` surfaces is Chapter 4 and Deep A; the values (convenience balanced against explicitness) are Chapter 3; the quadratic-accumulation edge is Chapter 74 (Deep H) and Chapter 9.

**Forward.**
The `__iadd__` protocol and operator dispatch are Deep C (the data model); `defaultdict` for the dict-value case is Chapter 32 (Deep Q); numpy's in-place `+=` as a performance feature is Deep T; the thread-safety edge is Chapter 99 (Deep L); the mutable-default-argument gotcha is Deep A.

**Across books.**
`+=`'s mutate-vs-rebind distinction is Python's; **Book I**'s C++ has `operator+=` (in-place) versus `operator+` (new value) as separate, explicitly-defined operators, so the distinction is *visible in the type's interface* where Python's is implicit in mutability. The shared system's fixed-point price arithmetic (Chapter 131) uses immutable integer prices precisely so `+=` is unambiguous (pure rebind), avoiding the mutable-`+=` trap in code that must be deterministic.

---

## 11.8 Exercises

**1. Prove the two faces.** For int, str, tuple (immutable) and list, set, dict (mutable), demonstrate `+=` (or `|=`) and check `id` before and after; classify each as rebind or in-place mutate.

**2. Reproduce the shared-reference trap.** Write a function that mutates its list argument via `+=` and one that does not via `= +`; show the caller's list changed in one case and not the other. Explain via names-vs-objects.

**3. The half-completing case.** Reproduce `t[0] += [3]` on a tuple-of-list; catch the `TypeError` and show the list was mutated anyway. Explain the two steps and why they disagree.

**4. Mutable default amplification.** Write `def f(items=[]): items += [x]`; call it three times and show the accumulation; fix it and explain both the mutable-default and the in-place-mutation contributions.

**5. The design question.** Python's `+=` dispatches on mutability implicitly (same syntax, different semantics for list vs int), where C++ makes `operator+=` an explicit, separately-defined operation. Argue whether the implicit dispatch is the right trade, convenience and uniformity versus the gotchas it creates, and identify one place where making the distinction explicit (a separate `.extend()` call instead of `+=`) improves a real codebase's clarity.

---

## 11.9 Summary and cross-references

- **Python 2.0 (2000) added augmented assignment (`+=`)**, which for **immutable** types is pure sugar (rebinds to a new object, identical to `= +`) and for **mutable** types mutates the object *in place* (calls `__iadd__`, e.g. `list.__iadd__` is `extend`).
- **The identity difference is the gotcha**: `a += b` and `a = a + b` produce the same *value* but different *object identity* for mutable types, which is decisive when the object is shared, `+=` changes it for every alias, `= +` changes it for none (Chapter 4's names-vs-objects).
- **`+=` is mutate-then-rebind**, two steps, proven by `t[0] += [3]` on a tuple-of-list: the in-place mutation *succeeds* (the list changes) then the rebind *fails* (`TypeError`), leaving the list modified after an exception.
- **The distinction bites** with mutable default arguments (amplifies the shared-mutation bug), dict-list values (`defaultdict` exists for this), and threading (`+=` on a shared mutable races, Chapter 99), while for numpy arrays in-place `+=` is a deliberate performance feature (Deep T).
- **The release framing**: 2.0 added `+=` for convenience and surfaced the mutation-vs-rebinding line always present in the object model, the lesson is "know whether your object is mutable", because `+=` means different things for the two kinds.

**Cross-references.** The object model and mutability → Chapter 4, Deep A. The values → Chapter 3. Quadratic accumulation → Chapters 9, 74. The data-model operator protocol → Deep C. `defaultdict` → Chapter 32. numpy in-place ops → Deep T. Thread safety → Chapter 99. The C++ operator distinction → Book I, Deep M.
