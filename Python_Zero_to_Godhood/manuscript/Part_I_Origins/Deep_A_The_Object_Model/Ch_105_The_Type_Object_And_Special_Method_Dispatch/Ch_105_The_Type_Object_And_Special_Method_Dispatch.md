# Chapter 20: The Type Object and Special-Method Dispatch

Chapter 19 ended on a pointer.
Every object's second word is `ob_type`, and it points at the object's **type**.
This chapter is about what that pointer reaches: the type object, and the table of function pointers it carries that actually implements the object's behaviour.
When you write `len(x)`, `x + y`, `x[k]`, or `for i in x`, none of those reach into `x`.
They reach into `type(x)`, read a slot, and call it.
That single fact, **special methods are looked up on the type, not the instance**, explains a family of behaviours that otherwise look like unrelated quirks: why assigning `__len__` to an instance does nothing, why a custom `__getattribute__` never sees `len(x)`, and why `1 + MyClass()` can work when `int` has never heard of `MyClass`.

**This is the canonical home for the data model's dispatch mechanism.**
Chapter 19 owns the object header; this chapter owns what `ob_type` points at and how the interpreter calls through it.
Chapter 4 covers the 2.2 type/class unification (the release in which `ob_type` stopped pointing at two different kinds of thing); the descriptor protocol, metaclasses, and C3 linearisation are **Deep C**; attribute lookup for *ordinary* names is Chapter 21.
This chapter is specifically about **special-method** dispatch.

## Section index

- **20.1** The type object: what `ob_type` points at
- **20.2** Mechanism I: special methods are looked up on the type
- **20.3** Mechanism II: implicit lookup bypasses `__getattribute__`
- **20.4** Mechanism III: operator dispatch and the `NotImplemented` protocol
- **20.5** Measurement: the operator is not a fast shortcut
- **20.6** Edges and failure modes
- **20.7** Connections
- **20.8** Exercises
- **20.9** Summary and cross-references

Listings live under `code/ch105/` and are re-executed by `make verify` on both verification interpreters.

---

## 20.1 The type object: what `ob_type` points at

The type is not a tag or a label.
It is a full object, `object()` has a type, and so does `int`, and so does `type` itself, and the type object carries the **slot table**: an array of C function pointers (`tp_as_number->nb_add`, `sq_length`, `tp_getattro`, and dozens more) that *are* the object's behaviour.
A special method such as `__add__` is CPython's way of exposing one of those slots to Python as an attribute of the type.

```python
# code/ch105/l01_type_object.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- ob_type is the object's type ---
  type(5)            : int
--- the type carries the slot: __add__ lives on the TYPE ---
  type(5).__add__    : <slot wrapper '__add__' of 'int' objects>
  it is a slot wrapper (a C slot), kind : wrapper_descriptor
--- a Python-defined method is a plain function on the type ---
  P.__add__ kind     : function
--- a type is itself an object; its type is 'type' ---
  isinstance(int, object) : True
  type(int)               : type
  type(type)              : type   (type is its own type)
```

`type(5).__add__` is a **slot wrapper**: not a Python function but a thin `wrapper_descriptor` around the C-level `nb_add` slot, which is where integer addition actually lives.
When you *define* `__add__` in a Python class, CPython does the reverse, it installs a generic C slot that, when called, dispatches back to your Python function (`P.__add__` is an ordinary `function`).
Either way the method is an attribute **of the type**, not of any instance.

And the type is an object like any other: `isinstance(int, object)` is `True` (every type is an object), `type(int)` is `type` (the type of a type is the metatype), and `type(type)` is `type` (the tower stops here, `type` is its own type).
That closure is deliberate, it is what makes the model finite: you do not need a type-of-a-type-of-a-type; `type` describes itself.
The machinery that lets you *subclass* `type` to intercept type creation is the metaclass protocol, and it belongs to **Deep C**.
Here we only need the fact that `ob_type` points at an object whose slots implement behaviour.

---

## 20.2 Mechanism I: special methods are looked up on the type

This is the rule everything else in the chapter follows from, and it contradicts the intuition that an object's behaviour comes from the object.

```python
# code/ch105/l02_lookup_on_type.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- put __len__ on the INSTANCE dict: ignored ---
  c.__len__ is in c.__dict__ : True
  len(c) -> TypeError        : object of type 'C' has no len()
--- put __len__ on the TYPE: now len() finds it ---
  after C.__len__ = ..., len(c) : 7
--- explicit attribute access DOES see the instance one ---
  c.__len__() (explicit, instance) : 42   (the lambda: 42)
  len(c)      (implicit, type)     : 7   (the class method: 7)
```

Assigning `c.__len__ = lambda: 42` really does put `__len__` in `c.__dict__`, the check confirms it, and `len(c)` **still raises `TypeError`**.
`len` does not look at `c.__dict__`.
It reads the `sq_length`/`mp_length` slot on `type(c)`, finds it empty, and reports that the type "has no len()".
The moment `C.__len__` is defined on the *class*, the slot is populated and `len(c)` returns `7`.

The last two lines are the whole rule in one contrast.
`c.__len__()` is an *explicit* attribute access: it goes through normal lookup, finds the instance attribute first, and returns `42`.
`len(c)` is an *implicit* special-method call: it ignores the instance entirely and uses the type's slot, `7`.
So the practical consequences are:

- **You cannot make a single instance iterable, sized, or callable by assigning a dunder to it.**
  Per-instance special behaviour requires a per-instance *type* (or a wrapper object).
- **Monkeypatching a dunder means patching the class**, `SomeClass.__iter__ = ...`, never `instance.__iter__ = ...`.
- **A class attribute and the "same" name accessed explicitly can disagree**, as `42` versus `7` above, because one path consults the instance and the other does not.

---

## 20.3 Mechanism II: implicit lookup bypasses `__getattribute__`

If special methods went through ordinary attribute access, every `len(x)` and `x + y` in a hot loop would pay a full `__getattribute__` traversal, and worse, a class that customises `__getattribute__` (a proxy, a lazy loader) could accidentally intercept its own operators.
CPython avoids both by reading the type slot *directly*, skipping the attribute machinery altogether.

```python
# code/ch105/l03_implicit_bypass.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- EXPLICIT lo.__len__(): ordinary attribute access ---
    __getattribute__ intercepted: '__len__'
  result: 3   (__getattribute__ WAS called above)
--- IMPLICIT len(lo): slot dispatch on the type ---
  result: 3   (no __getattribute__ line above: it was bypassed)
--- the rule ---
  implicit dunder dispatch reads the type slot directly, skipping
  __getattribute__ and the instance dict; explicit access does not
```

`Loud.__getattribute__` prints on every attribute access.
When we call `lo.__len__()` explicitly, it prints, that path *is* an attribute access.
When we call `len(lo)`, there is no print: the interpreter went straight to the type's length slot without ever consulting `__getattribute__`.

This is not an optimisation detail you can ignore; it changes what is *possible*.
A transparent proxy that forwards attribute access via `__getattribute__` will forward `proxy.foo` correctly but will **not** forward `len(proxy)`, `proxy + x`, `iter(proxy)`, or `proxy[k]`, because those never call `__getattribute__`.
To proxy special methods you must define them explicitly on the proxy's class (which is why libraries that build proxies generate a fixed list of dunder forwarders).
The same fact is why `hasattr(x, "__len__")` and "is `x` usable with `len()`" are not the same question: `hasattr` uses ordinary lookup, `len()` uses the slot.

---

## 20.4 Mechanism III: operator dispatch and the `NotImplemented` protocol

An operator is not a synonym for one dunder call.
`x + y` runs a two-sided **protocol** built on a sentinel, and understanding it explains how independently written types cooperate.

```python
# code/ch105/l04_operator_protocol.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a dunder can decline by returning NotImplemented ---
  (1).__add__('x') : NotImplemented   (int cannot add a str)
  it is a sentinel, not an error: type = NotImplementedType
--- the operator uses that to try the OTHER operand's reflected op ---
  1 + R() : 'R.__radd__(1)'
  int.__add__(1, R()) returned NotImplemented, so Python tried R.__radd__
--- left operand's __add__ wins when it does NOT decline ---
  L() + 1 : 'L.__add__'   (L.__add__ handled it; no fallback)
--- when both decline, THEN TypeError ---
  object() + object() -> TypeError : unsupported operand type(s) for +: 'object' and 'object'
```

The key object is **`NotImplemented`**: a singleton (Chapter 19's immortal cohort) that a special method returns to mean "I do not know how to do this with that operand", distinct from raising, and distinct from `None`.
`(1).__add__('x')` returns it rather than raising, and that return value is what drives the fallback.

The full algorithm for `x + y`:

1. Call `type(x).__add__(x, y)`.
   If it returns anything other than `NotImplemented`, that is the result.
2. Otherwise call the **reflected** method `type(y).__radd__(y, x)`.
   If it returns anything other than `NotImplemented`, that is the result.
3. If both return `NotImplemented`, raise `TypeError`.

(With one refinement: if `type(y)` is a *subclass* of `type(x)`, the reflected method is tried first, so a subclass can override.)
This is why `1 + R()` works: `int.__add__` has never heard of `R`, returns `NotImplemented`, and Python then tries `R.__radd__`, which succeeds.
A brand-new type on the *right* of `+` cooperates with a builtin on the left, without the builtin being modified, exactly the extensibility the sentinel buys.
And when `L.__add__` handles the operation directly, no fallback happens; when both operands decline (`object() + object()`), only then is it a `TypeError`.

The rule: **an operator is a protocol, not a call.**
Returning `NotImplemented` (never raising `TypeError` yourself) from a binary dunder is what lets the other operand get its turn; raising instead of returning the sentinel breaks that cooperation.

---

## 20.5 Measurement: the operator is not a fast shortcut

**Methodology.** `code/ch105/bench_dispatch.py`.
`x + y` (the full protocol of §20.4) against `x.__add__(y)` (a direct method call that skips the protocol) for a small `__slots__` class whose operands match, so the *first* dunder always succeeds and no reflected call is actually taken.
`min` of 5 runs, 5,000,000 calls each.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| addition, matching operands | ns/call | vs direct |
|---|---|---|
| `a.__add__(b)` (direct method call) | **77.8** | 1.0x |
| `a + b` (operator protocol) | **93.2** | **1.2x** |

The folklore is that operators are a fast path.
They are not: `a + b` is measurably **slower** than calling the dunder directly, ~1.2x here, and the same direction on 3.14.6 (94.5 vs 78.6 ns).
The operator does *more* work: it dispatches to `type(a).__add__`, inspects the result for the `NotImplemented` sentinel, and is prepared to try `type(b).__radd__`, all of which `a.__add__(b)` skips by going straight to one method.

So the operator does not buy speed.
It buys the **`NotImplemented` fallback protocol**, the thing that makes `1 + R()` work.
That reframes when each is appropriate: use the operator in ordinary code and get the cooperation; call the dunder directly only when you have already decided which operand handles the operation and specifically want *no* fallback (some numeric-library internals do this).
The measurement is also a reminder that "goes through C" is not automatically "faster", the C code here is running a richer protocol than the Python-level method call it is compared against, and the richer protocol costs.

---

## 20.6 Edges and failure modes

**Instance dunders are ignored by implicit dispatch.** §20.2.
`instance.__len__ = f` does nothing for `len(instance)`.
Set the method on the class.

**Explicit and implicit access can return different objects.** §20.2.
`x.__len__` (attribute lookup, sees the instance) and the slot used by `len(x)` (the type) are not guaranteed to be the same callable.
Never reason about operator behaviour from `x.__dunder__`.

**Special-method dispatch skips `__getattribute__` and `__getattr__`.** §20.3.
A proxy built on `__getattribute__` does not forward operators, `len`, `iter`, subscripting, or `with`.
Forward special methods by defining them explicitly on the proxy class.

**Return `NotImplemented`, do not raise, from a binary dunder that cannot handle an operand.** §20.4.
Raising `TypeError` yourself denies the other operand its reflected turn and breaks cooperation; returning the sentinel lets the protocol continue.

**`NotImplemented` is not `NotImplementedError` and not falsy-by-intent.**
`NotImplemented` is a singleton *value* returned by dunders; `NotImplementedError` is an *exception* raised by abstract methods.
Also, using `NotImplemented` in a boolean context is deprecated and will eventually error, it is a protocol sentinel, not a `False`.

**The slot is cached on the type; changing a dunder updates it, but with a cost.**
Assigning `C.__add__ = ...` re-derives the C slot and invalidates the type's method cache (and, on the specializing interpreter, any specialized `BINARY_OP`).
Dunders are meant to be defined at class-creation time; rebinding them at runtime works but is not free and is a code smell.

**A metaclass can intercept dunder access on the *type* itself.**
`SomeClass + x` looks up `__add__` on `type(SomeClass)`, the metaclass, not on `SomeClass`.
Operators on classes (as opposed to instances) are a metaclass concern (**Deep C**).

---

## 20.7 Connections

**Backward.**
`ob_type`, the pointer this chapter follows, is Chapter 19.
`NotImplemented`, `None`, and the other sentinels are the immortal objects of §19.5.
Chapter 4's 2.2 type/class unification is why there is a single `ob_type` slot table to dispatch through at all, before it, built-in and user-defined types were different mechanisms.

**Forward.**
Ordinary attribute lookup (`x.foo`), the `__getattribute__`/`__getattr__`/`__dict__`/MRO algorithm that §20.2 and §20.3 deliberately stepped around, is Chapter 21.
The descriptor protocol (how a function on the type becomes a bound method, how `property` works) and metaclasses (dunders on types) are **Deep C**.
How the specializing interpreter turns a hot `BINARY_OP` into a type-guarded fast path that skips even the slot indirection is **Deep H** (the interpreter and JIT).

**Across books.**
This dispatch model is why **Book I**'s numeric types integrate seamlessly: a NumPy array or a decimal implements `__add__`/`__radd__` and *becomes* a first-class operand of `+`, `*`, and the rest, cooperating with `int` and `float` through the `NotImplemented` protocol rather than being special-cased by the interpreter.
The order-book system carried through the series relies on exactly this, its price and quantity types define the arithmetic dunders and then read like plain numbers at every call site, which is the payoff §20.4 describes and **Deep M** builds on at the C boundary.

---

## 20.8 Exercises

**1. Predict the dispatch.** Without running, say what each prints and why:

```python
class C: pass
c = C()
c.__call__ = lambda: "instance"      # (a) does c() work?
C.__call__ = lambda self: "type"     # (b) now does c() work?
print(c.__call__())                  # (c)
print(c())                           # (d)
```

Then run it. Explain the difference between (c) and (d) in terms of §20.2.

**2. Break a proxy.** Write a `Proxy` class that wraps an object and forwards *ordinary* attributes via `__getattribute__`. Show that `proxy.upper()` works on a wrapped string but `len(proxy)` and `proxy[0]` fail. Then make them work, and explain, from §20.3, why the fix has to be what it is.

**3. Trace the fallback.** Define two classes `A` and `B` where `A.__add__` returns `NotImplemented` and `B.__radd__` succeeds. Add print statements and show the exact order of calls for `A() + B()`. Then make `B` a subclass of `A` and show how the order changes, and say which rule from §20.4 caused it.

**4. Measure your own type.** Reproduce §20.5 for a type of your choosing, and then construct a case where `a + b` must actually take the reflected `__radd__` fallback (the left operand returns `NotImplemented`). Measure that against the non-fallback case and explain the additional cost in terms of the protocol steps.

**5. The design question.** Special methods are looked up on the type and bypass `__getattribute__` (§20.2, §20.3). CPython could instead have made `len(x)` ordinary attribute access on the instance. Argue what that would cost, in performance (§20.5), in the ability to specialize operators (**Deep H**), and in correctness for proxies. Then argue the one thing it would make *easier*, and say whether it is worth it.

---

## 20.9 Summary and cross-references

- `ob_type` points at the **type object**, which carries the **slot table** of C function pointers that implement behaviour; a special method is an entry in that table, exposed as an attribute **of the type**. A type is itself an object, and `type(type)` is `type`.
- **Special methods are looked up on the type, not the instance.** Assigning a dunder to an instance does nothing for implicit dispatch; monkeypatching a dunder means patching the class.
- **Implicit special-method dispatch bypasses `__getattribute__` and the instance `__dict__`.** Proxies built on `__getattribute__` do not forward operators, `len`, `iter`, or subscripting unless those dunders are defined explicitly.
- **An operator is a protocol, not a call.** `x + y` tries `type(x).__add__`; on the `NotImplemented` sentinel it tries the reflected `type(y).__radd__`; if both decline, `TypeError`. Returning `NotImplemented` (not raising) is what lets the other operand cooperate.
- **Measured:** `a + b` costs **1.2x** a direct `a.__add__(b)` (93.2 vs 77.8 ns), because the operator runs the fallback protocol the direct call skips. The operator buys cooperation, not speed.

**Cross-references.** The object header `ob_type` follows from → Chapter 19. Immortal sentinels (`None`, `NotImplemented`) → §19.5. Type/class unification → Chapter 4. Ordinary attribute lookup, `__getattribute__`, `__getattr__`, MRO → Chapter 21. Descriptors, `property`, metaclasses (dunders on types) → Deep C. Operator specialization in the interpreter → Deep H. Crossing to C with cooperating numeric types → Deep M.
