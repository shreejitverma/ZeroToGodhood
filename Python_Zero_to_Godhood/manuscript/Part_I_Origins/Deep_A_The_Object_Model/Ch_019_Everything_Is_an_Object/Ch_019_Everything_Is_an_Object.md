# Chapter 19: Everything Is an Object

"Everything in Python is an object" is the first thing anyone is told about the language and the
last thing most people examine. It sounds like a design philosophy. It is not. It is a statement
about memory layout: every value the interpreter can name begins with the same two machine words,
and almost everything else about CPython's behaviour, its speed, its memory profile, the existence
of the GIL, follows from that decision.

This chapter is about those two words. What they are, what they cost, what the interpreter buys
with them, and the three mechanisms CPython uses to avoid paying for them when it can.

**This is the canonical home for the object model.** The historical chapters introduce pieces of it
where the timeline demands: Chapter 2 covers reference counting as it existed in Python 1.x, and
Chapter 4 covers the 2.2 type/class unification. Both cross-reference here for the model itself.

## Section index

- **19.1** The problem: a million integers
- **19.2** The model: two words in front of everything
- **19.3** Mechanism I: `PyObject`, and reading its fields from Python
- **19.4** Mechanism II: variable-size objects and the size that is not there
- **19.5** Mechanism III: immortality (PEP 683)
- **19.6** Identity, interning, and the small-integer cache
- **19.7** Measurement: what the header costs at scale
- **19.8** Edges and failure modes
- **19.9** Connections
- **19.10** Exercises
- **19.11** Summary and cross-references

Listings live under `code/ch019/` and are re-executed by `make verify` on both verification
interpreters.

---

## 19.1 The problem: a million integers

Store a million 64-bit integers. In C that is `int64_t values[1000000]`, which is 8 MB, contiguous,
one cache-friendly allocation.

Do it in Python and measure it honestly, with `tracemalloc` rather than `sys.getsizeof`, because
`getsizeof` is shallow and reports the list's own array without the objects it points at:

```python
# code/ch019/l05_memory_cost.py
N = 1_000_000
```

Verified output (CPython 3.13.5):

```text
--- storing 1,000,000 integers, four ways ---
  representation                         MB   bytes/element
  list of int  (0..N)                  38.1            40.0
  tuple of int (0..N)                  38.1            40.0
  array('q')  (int64)                   7.8             8.2
  bytes       (raw)                     7.6             8.0
```

**38.1 MB against C's 8 MB.** Roughly five times the memory, and worse than the ratio suggests: the
list holds a million pointers to a million separately allocated objects scattered across the heap,
so iterating it is a pointer chase, while the C array is a linear scan a prefetcher can predict.

The `array('q')` row is the same million integers at 7.8 MB, within a rounding error of C. So Python
can store them densely. The 30 MB difference is not Python being slow; it is the price of every one
of those integers being an *object*.

This chapter is about what that price buys, and about the fact that `array` gets to skip it.

---

## 19.2 The model: two words in front of everything

The model in one sentence: **every Python object is a C struct whose first two fields are a
reference count and a pointer to its type, and every pointer the interpreter passes around is a
pointer to that pair.**

In CPython's source this is a macro, `PyObject_HEAD`, prepended to every object struct:

```c
/* Illustrative; Include/object.h. The exact declaration has changed across
   versions, notably for free-threading. */
typedef struct _object {
    Py_ssize_t        ob_refcnt;
    struct _typeobject *ob_type;
} PyObject;
```

Two consequences make this the most important structure in the language.

**Uniformity.** Because every object starts the same way, a function taking `PyObject *` can accept
any value at all, and can find that value's type by following one pointer. There is no separate
"primitive" path: an `int`, a `dict`, a function, a module, and a type itself are all reached
through the same handle. That is what "everything is an object" actually means, and it is why
Python has no `int` versus `Integer` distinction of the kind Java carries.

**Cost.** Sixteen bytes on a 64-bit build, before the object stores a single byte of its own data.
For a `dict` that is negligible. For an integer it is twice the size of the integer.

**The senior-engineer contrast.** In C++, `int` is a machine word with no header, and you add
polymorphism deliberately by inheriting from a base with a vtable pointer, at a cost of one word
per object. Python inverts the default: every value is polymorphic, and you opt *out* by reaching
for `array`, `bytes`, NumPy, or the buffer protocol. The C++ programmer pays for dynamism where
they ask for it; the Python programmer pays everywhere and buys it back in the few places that
matter.

---

## 19.3 Mechanism I: `PyObject`, and reading its fields from Python

Both header fields are readable from Python, which makes the model directly observable.

```python
# code/ch019/l01_universal_header.py
import sys
x = object()
```

Verified output (CPython 3.13.5):

```text
--- the smallest possible object ---
sys.getsizeof(object())  = 16 bytes
  8 bytes: ob_refcnt  (Py_ssize_t)
  8 bytes: ob_type    (PyTypeObject *)
--- both fields are readable from Python ---
ob_type, via type()      = <class 'object'>
ob_refcnt, via getrefcount = 2
```

`object()` stores nothing. It is 16 bytes, and the accounting is exact: two fields, eight bytes
each. `type(x)` is a read of `ob_type`; `sys.getrefcount(x)` is a read of `ob_refcnt`.

That refcount of 2 for a freshly created object with one binding is the first trap:

```text
--- getrefcount always reports one more than you expect ---
after 'y = x' and 'z = x', getrefcount(x) = 4
the bindings are x, y, z = 3, plus getrefcount's own argument = 4
```

**`sys.getrefcount` counts its own argument.** Calling it binds the object to a parameter, which is
a reference like any other. The reported number is always one higher than the count you were asking
about. This is not a bug and cannot be fixed without special-casing the function; it is what
"everything is passed as a reference" means when the thing doing the asking is itself a function
call.

Now the integer:

```text
--- the header is why a Python int is not a machine int ---
sys.getsizeof(0)         = 28 bytes
sys.getsizeof(1)         = 28 bytes
a C int64_t              = 8 bytes
```

Twenty-eight bytes to store zero. Sixteen are the header. The remaining twelve are CPython's
arbitrary-precision representation: a size field and one 30-bit digit. This is why Python integers
never overflow, and the 28 bytes are the bill for that guarantee.

---

## 19.4 Mechanism II: variable-size objects and the size that is not there

A tuple of three elements and a tuple of thirty cannot be the same size, so CPython has a second
header. `PyVarObject` adds one field, `ob_size`, and the elements follow the struct in the same
allocation.

A type declares its footprint in two numbers, both visible from Python:

```python
# code/ch019/l03_varobject.py
```

Verified output (CPython 3.13.5):

```text
--- what each type declares ---
  type      __basicsize__  __itemsize__
  object               16             0
  int                  24             4
  tuple                24             8
  bytes                33             1
  list                 40             0
  dict                 48             0
  str                  64             0
```

`__itemsize__` of zero means fixed size. `tuple` at 8 bytes per item is one pointer per element.
`int` at 4 is one 30-bit digit per unit of magnitude, which is where arbitrary precision lives.
`bytes` at 1 is a byte per byte, and its odd `__basicsize__` of 33 is the struct plus the null
terminator CPython keeps so that a `bytes` can be handed to C functions expecting a C string.

Now watch the declared size fail to match the allocated size:

```text
--- tuple is the clean PyVarObject: size grows with ob_size ---
  tuple of 0: declared=  24  getsizeof=  40  delta= 16
  tuple of 1: declared=  32  getsizeof=  48  delta= 16
  tuple of 2: declared=  40  getsizeof=  56  delta= 16
  tuple of 8: declared=  88  getsizeof= 104  delta= 16
```

The growth is exactly 8 bytes per element, as declared. But every tuple is 16 bytes larger than the
type says it should be, and the gap is constant regardless of length. That gap is a **`PyGC_Head`**,
a two-pointer structure the garbage collector allocates *in front of* the object so it can thread
every container onto a doubly-linked list:

```text
--- the constant delta is the GC header, allocated in front of the object ---
  object()   gc.is_tracked=False getsizeof=  16
  (1, 2)     gc.is_tracked=True  getsizeof=  56
  [1, 2]     gc.is_tracked=True  getsizeof=  72
```

`object()` is not tracked and pays nothing. Anything that can participate in a reference cycle is
tracked and pays 16 bytes. This is the cyclic collector's fixed tax, and Chapter 3 covers why it is
necessary; **Deep B** owns the collector itself.

Finally, the case where the tidy formula stops working:

```text
--- where the naive formula breaks: list stores items elsewhere ---
  list.__itemsize__ = 0, yet a list clearly grows:
    getsizeof(list of 0) =   56
    getsizeof(list of 1) =   72
    getsizeof(list of 2) =   72
    getsizeof(list of 8) =  120
```

`list` declares `__itemsize__` of zero and yet obviously grows. A list's elements do not live in the
list's allocation; they live in a separate `ob_item` array the list points at, which is what makes
`append` possible without moving the list object itself. Note also that lists of one and two
elements are both 72 bytes: the array is **over-allocated** so that repeated appends do not
reallocate every time. That growth policy is a `list` implementation detail rather than an object
model one, and it belongs to **Deep Q**.

The lesson to carry forward is about the tool, not the types: **`tp_basicsize` and `tp_itemsize`
describe the object's own struct, and nothing else.** Anything reached through a pointer, a list's
elements, a dict's table, a string's UTF-8 cache, is invisible to them and to `sys.getsizeof`.

---

## 19.5 Mechanism III: immortality (PEP 683)

`None` is one object, shared by every module, every function, and every thread in the process. Every
time a function returns `None`, its refcount goes up and then down. That is an atomic increment on
a single memory location that every thread in the program touches constantly: a contention hotspot
of the purest kind, protecting a value that is never going to be deallocated.

**PEP 683 (Python 3.12)** marked such objects **immortal**. Their refcount field holds a sentinel,
and the interpreter's incref and decref skip them entirely.

```python
# code/ch019/l02_immortality.py
```

Verified output (CPython 3.13.5):

```text
--- refcounts of objects the interpreter shares everywhere ---
  refcount(None  ) =   4294967295
  refcount(True  ) =   4294967295
  refcount(False ) =   4294967295
  refcount(0     ) =   4294967295
  refcount(1     ) =   4294967295
  refcount(256   ) =   4294967295
  refcount('a'   ) =   4294967295
--- and one that is not immortal ---
  refcount(257   ) =            3
--- the sentinel, in hex ---
  refcount(None) = 4294967295 = 0xffffffff
```

`0xffffffff`. Not a count of anything; a flag that happens to live in the count's field. And `257`
sitting at 3 tells you the boundary is not about types but about which specific objects CPython
chose to pre-create (§19.6).

The consequence is worth stating plainly because it invalidates a debugging technique:

```text
--- consequence: refcounts of immortal objects carry no information ---
  after binding None one million more times:
  refcount(None) =   4294967295  (unchanged)
```

A million new references to `None` and the number does not move. **You cannot use `getrefcount` to
find a leak involving immortal objects**, because there is nothing to count.

> **Version caveat, verified.** The sentinel is not stable across releases. On CPython 3.13.5 it is
> `4294967295` (`0xffffffff`); on 3.14.6 it is `3221225472` (`0xc0000000`). Both are recorded under
> `code/ch019/expected/`. Test for immortality by comparing against an implausibly large threshold,
> never against a literal constant, and treat the specific value as an implementation detail that
> will change again.

Immortality is also load-bearing for the free-threaded build, where an unavoidable atomic
read-modify-write on `None` for every function return would be a serious scalability problem. That
story is **Deep L**.

---

## 19.6 Identity, interning, and the small-integer cache

`is` compares addresses. Because CPython pre-allocates and shares certain objects, `is` sometimes
appears to compare values, and that coincidence has misled every Python programmer at least once.

```python
# code/ch019/l04_identity.py
```

Verified output (CPython 3.13.5):

```text
--- CPython pre-allocates the small integers ---
  ints with sentinel refcounts span -5 .. 256
--- inside that range, equal values are the same object ---
  int('256') is int('256')  ->  True
--- outside it, they are not ---
  int('257') is int('257')  ->  False
  int('257') == int('257')  ->  True
```

The range is **-5 to 256**, and it is arbitrary: chosen because those values dominate real programs
as loop counters, indices, small results, and flags. Constructing `256` twice yields the same
object; constructing `257` twice yields two.

Strings behave the same way through a different mechanism, **interning**:

```text
--- the same effect for strings, via interning ---
  two literals:      s1 is s2  ->  True
  a computed string: s1 is s3  ->  False
  but equal:         s1 == s3  ->  True
```

Two occurrences of the literal `"hello"` are the same object because the compiler interned them.
The identical string built by `"".join(["hel", "lo"])` is a different object, because it was
produced at runtime and nothing interned it. **Both are equal; only one pair is identical.**

The rule is unconditional: **use `==` for values and `is` only for singletons you control**,
meaning `None`, `True`, `False`, and sentinels you created yourself. CPython emits a
`SyntaxWarning` for `is` against an integer literal precisely because the behaviour is a
coincidence of the cache.

And the reason `is` cannot be trusted even in principle:

```text
--- id() is the object's address, and is only unique while it lives ---
  two short-lived objects reused the address: True
  the first was freed before the second was allocated, so id() collided.
```

`id(object()) == id(object())` returns `True`, reliably. The first object is freed before the second
is allocated, so the allocator hands back the same address. **An `id()` is unique only among
simultaneously live objects.** Caching one and expecting it to keep meaning the same object is a
bug, and it is the reason `id()`-keyed caches must hold a reference to whatever they key on.

---

## 19.7 Measurement: what the header costs at scale

**Methodology.** `code/ch019/l05_memory_cost.py`. Peak allocation measured with `tracemalloc`, which
counts every allocation the interpreter makes, rather than `sys.getsizeof`, which is shallow and
would report only the container. One million elements. Results were byte-identical across three
consecutive runs, so no averaging is applied and no variance is reported: the measurement is
deterministic, which is why memory is a more comfortable thing to benchmark than time.

Interpreter: CPython 3.13.5. Hardware: Apple M3 Pro, 36 GB, macOS 27.0, arm64. Memory figures are
far less build-sensitive than timings, so unlike the benchmarks in Chapter 18 these are broadly
comparable across interpreters.

| representation | MB | bytes/element | vs `array` |
|---|---|---|---|
| `list` of `int` | 38.1 | 40.0 | 4.9x |
| `tuple` of `int` | 38.1 | 40.0 | 4.9x |
| `array('q')` | 7.8 | 8.2 | 1.0x |
| `bytes` | 7.6 | 8.0 | 0.97x |

Forty bytes per element decomposes exactly: **8 bytes for the pointer** in the list's `ob_item`
array, plus **32 bytes for the `int` object** it points at, which is the 28 bytes from §19.3 rounded
up by the allocator's size classes (**Deep B**).

The important observation is which half dominates. The pointer is the cheap part. The object header
is four times the pointer, and it is the part `array('q')` eliminates by storing raw machine
integers with no per-element object at all.

Then the cache, isolated:

Verified output (CPython 3.13.5):

```text
--- and why small integers are nearly free ---
  list of 1,000,000 ints in 0..255      :    8.1 MB
  list of 1,000,000 ints above the cache:   38.6 MB
```

**A 4.8x difference from the small-integer cache alone.** The first list is a million pointers to
256 shared immortal objects, so it costs one pointer per element and nothing more. The second
allocates a million distinct integers.

This is the practical shape of §19.5 and §19.6 together, and it explains a memory profile that
otherwise looks impossible: the same data structure, the same element count, five times the memory,
because the values crossed 256.

> **A version difference worth noting.** On CPython 3.14.6 the `tuple` row reads 46.2 MB rather than
> 38.1 MB, because `tuple.__basicsize__` grew from 24 to 32 bytes. The `list` row is unchanged. I
> have confirmed the size change by measurement on both interpreters but have **not** traced it to a
> specific CPython commit or What's New entry, so I am reporting it as observed rather than
> explaining it. It is in the verification queue.

---

## 19.8 Edges and failure modes

**`sys.getrefcount` is always one high.** §19.3. Compare deltas rather than absolute values, and
never write an assertion against an exact refcount.

**Refcounts of immortal objects are meaningless.** §19.5. Leak hunting that involves `None`, small
integers, `True`, `False`, or interned strings needs a different tool.

**The immortality sentinel changes between releases.** `0xffffffff` on 3.13, `0xc0000000` on 3.14.
Threshold, never equality.

**`sys.getsizeof` is shallow.** It reports an object's own allocation and nothing it points at.
`getsizeof` of a list of a million integers reports about 8 MB, not the 38 MB actually in use. For
real accounting use `tracemalloc`, which is what §19.7 does.

**`id()` is reusable.** §19.6. Unique only among live objects.

**`is` against a literal is a coincidence, not a rule.** It works for `-5..256` and interned
strings, and silently stops working outside them. CPython warns for integer literals; it does not
warn for every case.

**`__basicsize__` does not include the GC header.** §19.4. A tracked object costs 16 bytes more than
its type claims. Any size calculation that omits this under-reports every container in the program.

**Object identity is not stable across processes or runs.** Nothing in this chapter survives
pickling, `fork`, or a restart. Address-based reasoning is process-local by definition.

---

## 19.9 Connections

**Backward.** Chapter 2 introduced reference counting in its 1.x historical setting and is the
narrative origin of `ob_refcnt`; this chapter is the model it deferred to. Chapter 3 introduced the
cyclic collector, which is why the `PyGC_Head` in §19.4 exists. Chapter 4 covers 2.2's type/class
unification, the release in which `ob_type` stopped pointing at two different kinds of thing.

**Forward.** `ob_type` points at a `PyTypeObject`, and its slot table is the subject of the next
chapter. Reference counting as an algorithm, its interaction with the cyclic collector, and the
allocator that produces the size classes in §19.7 are **Deep B**. The free-threaded build's
biased reference counting, which changes what `ob_refcnt` even means, is **Deep L**.

**Across books.** §19.1's 4.9x memory gap is the reason the boundary to **Book I** exists at all.
Every technique for crossing it, the buffer protocol, `memoryview`, NumPy's dtypes, `array`, is a
way of holding a large number of values *without* giving each one a `PyObject` header, and then
handing the raw block to C or C++ code that can address it directly. The order-book example that
runs through all three books stores its price levels exactly this way. **Deep M** owns that
boundary; the chapter you are reading is why it is worth crossing.

---

## 19.10 Exercises

**1. Predict the refcount.** Without running it, give the value `sys.getrefcount(x)` prints after
each line, and justify each:

```python
x = object()          # (a)
lst = [x, x, x]       # (b)
d = {"k": x}          # (c)
del lst               # (d)
```

Then run it. If any prediction was wrong by exactly one, you have found the §19.3 trap; if wrong by
more, explain what else held a reference.

**2. Find the cache boundary yourself.** §19.6 reports -5 to 256 using refcount sentinels. That
technique only works because those objects are immortal, which was not true before 3.12. Devise a
second, independent test for the boundary that would have worked on Python 3.11, and explain why
`is` on literals is *not* a valid basis for it.

**3. Account for a dict.** Take `{"alpha": 1, "beta": 2}`. Predict its `sys.getsizeof`, then measure
it, then measure the total memory with `tracemalloc`. Explain the entire gap between the second and
third numbers. Which of the three mechanisms in this chapter accounts for the keys being cheaper
than you expected?

**4. Build the 8 MB list.** §19.7 shows a list of a million integers at 38.1 MB and `array('q')` at
7.8 MB. Construct a *list* holding a million logically distinct integer values that costs close to
8 MB, without using `array`, NumPy, or `bytes`. Then say precisely what you gave up, and name the
one property of the values that made it possible.

**5. The design question.** PEP 683 made some objects immortal to remove refcount contention. That
is a special case of a general alternative: CPython could have used tracing garbage collection
throughout and had no `ob_refcnt` at all, as Java and Go do. Argue what CPython would gain and what
it would lose. Your answer must address deterministic destruction, the C-API's `Py_INCREF` contract,
and why the free-threaded build (**Deep L**) makes this trade-off sharper rather than settling it.

---

## 19.11 Summary and cross-references

- Every Python object begins with **`ob_refcnt`** and **`ob_type`**, 16 bytes on a 64-bit build,
  before storing any of its own data. That uniformity is what lets one `PyObject *` refer to
  anything, and it is the language's largest standing cost.
- **`sys.getrefcount` reports one more than the true count**, because calling it creates a reference.
- Variable-size objects add **`ob_size`**; a type declares **`tp_basicsize`** and **`tp_itemsize`**,
  neither of which includes the **16-byte `PyGC_Head`** carried by every GC-tracked object, and
  neither of which describes memory reached through a pointer.
- **PEP 683 (3.12)** made shared objects **immortal**: their refcount is a sentinel the interpreter
  never touches, so those refcounts carry no information. The sentinel value **differs between 3.13
  and 3.14** and must never be compared for equality.
- CPython pre-allocates the integers **-5 to 256** and interns compile-time strings, which makes
  `is` appear to compare values. It does not. Use `==` for values; reserve `is` for singletons.
  **`id()` is reused** once an object dies.
- **Measured:** a million integers cost **38.1 MB** in a `list` against **7.8 MB** in `array('q')`,
  a **4.9x** gap, of which the object header rather than the pointer is four fifths. The same list
  built from values inside the small-integer cache costs **8.1 MB**, a **4.8x** swing from the cache
  alone.

**Cross-references.** Reference counting in its historical setting → Chapter 2. The cyclic collector
and why `PyGC_Head` exists → Chapter 3. Type/class unification → Chapter 4. The type object and its
slot table → Chapter 20. The allocator, size classes, and the collector in full → Deep B. Biased
reference counting under free-threading → Deep L. Escaping the header via the buffer protocol →
Deep M.
