# Chapter 89: Memory as a Cost Model

Time is not the only resource with a cost model, and memory is the one Python spends most freely.

Every value is an object with a header. Every container holds **pointers** to objects rather than the values themselves. And the tool everybody reaches for to measure this, `sys.getsizeof`, reports only the container and never what it points at, so a list of a million distinct objects and a list of a million `None`s report **the same size**.

The gaps are larger than most estimates. A million integers cost **44.4 bytes each** as a list of Python objects and **8.2** packed into an `array.array`, a factor of 5.4. An instance with a `__dict__` costs 7.2 times a `__slots__` instance holding the same two attributes.

And then the part that is usually left out of the argument: a packed representation is not automatically faster. Summing a hundred thousand numbers is **1.63x slower** out of an `array.array` than out of a list, because every element read has to build a Python object. Memory and time trade against each other here, and which side you want is decided by what **consumes** the data.

**This is a Deep K chapter.**
It is about measuring memory honestly, the representations available, and the trade that a size table alone will mislead you about.

## Section index

- **89.1** What an object costs, and what `getsizeof` hides
- **89.2** The representations, and what each gives up
- **89.3** Measurement: allocation, and what a smaller representation costs in time
- **89.4** Edges and failure modes
- **89.5** Connections
- **89.6** Exercises
- **89.7** Summary and cross-references

Listings live under `code/ch170/` and are re-executed by `make verify` on both verification interpreters.

---

## 89.1 What an object costs, and what `getsizeof` hides

```python
# code/ch170/l01_memory_cost_model.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- bytes per element in the container itself (header differenced out) ---
  list                 8 bytes
  tuple                8 bytes
  array.array('q')     8 bytes
  bytes                1 bytes
  a list, a tuple and an int64 array all cost 8 bytes per element, but the
  first two store POINTERS and the third stores the numbers themselves
--- sys.getsizeof is shallow, and that is the trap ---
  a list of 100 distinct objects and a list of 100 Nones report the same size : True
  because both hold 100 pointers; the objects are not counted
  deep size of the object list is larger : True
--- an instance with __dict__ against one with __slots__ ---
  WithDict  instance + its __dict__ : 344 bytes
  WithSlots instance                : 48 bytes
  ratio                             : 7.2x
  the slotted instance has no __dict__ at all : True
--- the boxing cost: the same numbers, two representations ---
  list of 1,000 large ints, deep : 40,856 bytes
  the same values in array('q')     : 8,080 bytes
  ratio                             : 5.1x
  one int object costs              : 32 bytes   (the value itself is 8 of them)
```

**Per-element figures are obtained by differencing two sizes**, exactly as Chapter 87's doubling method cancels the constant: measure the container at 1,000 and at 2,000 elements and divide the difference. That removes the fixed header and leaves the marginal cost, which is the number you can multiply by `n`.

**The first block's punchline is that three containers agree and mean different things.**
A `list`, a `tuple`, and an `array.array('q')` all cost 8 bytes per element. The first two spend those 8 bytes on a **pointer** to an integer object living elsewhere; the third spends them on the integer itself. So the list's real cost is 8 bytes plus whatever the object costs, and the array's real cost is 8 bytes, full stop.

**`sys.getsizeof` is shallow, and this is the trap that makes memory estimates wrong.**
A list of 100 distinct objects and a list of 100 `None`s report the same size, because both hold 100 pointers and neither counts what the pointers reach. For a list of small integers that is nearly correct, because the integers are cached and shared. For a list of large integers, strings, or instances it understates by a factor of five or more. **Any memory estimate built from `getsizeof` alone is a count of pointers.**

**`__slots__` is the largest single-line memory win available for objects.**
344 bytes against 48 for the same two attributes: a factor of **7.2**. The slotted instance has no `__dict__` at all, which the listing confirms rather than asserts. The cost is that you can no longer add attributes not declared in `__slots__`, and that multiple inheritance from two slotted classes with overlapping slots is an error. Deep A owns the mechanism; this chapter owns the number.

**And the boxing cost, stated as a ratio.**
A thousand large integers cost 40,856 bytes as a list and 8,080 packed, a factor of **5.1**. One `int` object is 32 bytes, of which the value occupies 8. The other 24 are the object header and the digit-count field that let a Python integer be arbitrarily large, which is a feature you are paying for on every element whether you use it or not.

---

## 89.2 The representations, and what each gives up

| representation | per element | gives up |
|---|---|---|
| `list` of objects | 8 bytes + the object | nothing; the default |
| `tuple` of objects | 8 bytes + the object | mutability |
| instance with `__dict__` | ~128 bytes per two-attribute pair | nothing |
| instance with `__slots__` | ~88 bytes per pair | dynamic attributes, some multiple inheritance |
| `(x, y)` tuple | ~96 bytes per pair | names, methods, type identity |
| `array.array` | the machine width | one type only, no `None`, boxes on read |
| `bytes` / `memoryview` | 1 byte | all structure; you manage the layout |
| NumPy array | the machine width | a dependency; buys vectorised operations |

**The measured surprise in that table** is that a `__slots__` instance is *smaller* than the equivalent tuple (§89.3: 87.9 bytes against 95.9 per pair). The tuple is usually assumed to be the cheapest option, and it is not once the class exists anyway, because a tuple has its own object header and a variable-length body while a slotted instance is a fixed-size block.

**Why an ordinary instance is not as bad as the 344-byte figure suggests.**
Since 3.11, instances of the same class share a **keys** object: the attribute names are stored once per class, and each instance holds only the values. That is why §89.3 measures 128 bytes per two-attribute instance rather than the 344 that a standalone `__dict__` reports. The saving disappears the moment an instance gets an attribute the others do not have, which forces it back to a private key table, so "all instances of this class have the same attributes" is a memory property and not only a style preference.

**Interning and sharing are doing more work than you think.**
Integers from -5 to 256 are cached, so a list of them holds a hundred pointers to a handful of objects. Short identifier-like strings are interned. `None`, `True`, and `False` are singletons and, since 3.12, immortal (Chapter 81). This is why measuring with `range(1000)` flatters a list badly, and why the listing uses `10**18 + i` to get genuinely distinct objects.

**And the decision rule this table serves.**
Choose the representation from **what consumes the data**. If the consumer is a C routine, a socket, a hash, or NumPy, pack it: those consumers take buffers (Chapter 79) and never build a Python object per element. If the consumer is a Python loop, a list of objects is usually correct, and §89.3 measures why.

---

## 89.3 Measurement: allocation, and what a smaller representation costs in time

**Methodology.** `code/ch170/bench_memory_and_time.py`.
Memory is measured with `tracemalloc`'s **peak allocation** rather than `sys.getsizeof`, so everything the container points at is counted. Time is `min` of 7 batches.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**A million numbers, three representations.**

| representation | peak bytes | bytes/number | vs `array` |
|---|---|---|---|
| `list` of `int` objects | 44,448,744 | 44.4 | **5.4x** |
| `tuple` of `int` objects | 44,651,416 | 44.7 | 5.5x |
| `array.array('q')` | 8,184,004 | 8.2 | 1.00x |

44 bytes to store an 8-byte number. The overhead is the `int` object's 32-byte header-and-digits plus the container's 8-byte pointer plus allocator rounding. A tuple saves nothing over a list here, because the saving a tuple offers is in the container and the cost is in the elements.

**A hundred thousand coordinate pairs, three ways.**

| representation | peak bytes | bytes/pair |
|---|---|---|
| `Point` instances (with `__dict__`) | 12,796,104 | 128.0 |
| `SlottedPoint` instances | 8,792,744 | **87.9** |
| `(x, y)` tuples | 9,585,856 | 95.9 |

`__slots__` beats both, including the tuple. And the ordinary instance is 128 bytes rather than the 344 that a standalone instance-plus-`__dict__` reports, because of the shared-keys optimisation described in §89.2. Both facts are the kind that a rule of thumb gets wrong and a measurement gets right.

**And what the packed representation costs in time.**

| sum 100,000 numbers | time | vs `list` |
|---|---|---|
| `sum(list)` | 1.17 ms | 1.00x |
| `sum(array.array)` | 1.91 ms | **1.63x** |
| `sum(memoryview.cast('q'))` | 1.99 ms | **1.70x** |

This is the table that a memory-only chapter would omit, and it inverts the conclusion for a whole class of code. The packed forms store raw machine values, so **every element read constructs a Python `int`**, and that allocation is paid on every pass. The list already has the objects and hands out pointers.

**So the trade has a shape, and it is not "smaller is better".**

- Packed wins **decisively** when the data is handed to something that consumes a buffer: a C routine, a socket write, `hashlib.update`, NumPy, `struct.unpack_from` (Chapters 79 and 84). There is no per-element Python object at all, and the memory saving is pure profit.
- Packed **loses** when the data is walked element by element in Python, by the 1.63x measured here plus whatever the allocator does under pressure.
- The list wins on access and loses on footprint, and at 44 bytes per number the footprint is what stops you before the access cost does, somewhere north of ten million elements on an ordinary machine.

**Book I**'s side of the shared system is the first bullet in its pure form: the tick buffer is packed because the matching engine consumes it as a buffer, and no Python object is ever created per tick. The moment the Python side wants to iterate it element by element, this table is the cost, and the design answer is not to iterate it, which is Chapter 84's decision procedure restated in the memory dimension.

---

## 89.4 Edges and failure modes

**`sys.getsizeof` is shallow, always.** §89.1.
It calls the object's `__sizeof__` and adds GC overhead. It does not follow references, does not deduplicate shared objects, and does not know about the allocator's rounding. Use `tracemalloc` for allocation, or write a deep walker that tracks `id()` to avoid double-counting shared objects.

**`tracemalloc` measures the Python allocator, not the process.**
Memory allocated by a C extension through `malloc` is invisible to it, and so is memory the allocator has returned to its own pools but not to the operating system. For process-level truth you need `resource.getrusage` or the OS, and the two figures disagree for good reasons.

**Peak is not steady state.**
`tracemalloc.get_traced_memory()` returns current and peak. Building a list then converting it to a tuple has a peak of both, which is a real cost if the machine is near its limit and invisible if you only look at the result.

**`__slots__` interacts badly with several things.**
No `__dict__` means no arbitrary attributes, no `__weakref__` unless you declare it, no default pickling of instance state in some protocols, and an error when two base classes both declare non-empty slots. It is a memory optimisation applied to classes with many instances, not a default.

**The shared-keys optimisation is fragile.** §89.2.
It holds while all instances of a class have the same attributes. One instance that gets an extra attribute after `__init__` falls back to a private key table and costs materially more. Setting all attributes in `__init__`, always, is the way to keep it.

**Small integers and interned strings will flatter any measurement.** §89.2.
Benchmarking with `range(n)` measures a list of pointers to cached objects. Use distinct values.

**A generator has no size to measure, and that is the point.** §89.3's list column is `n`-proportional and a generator's is constant, which is Chapter 91's subject; a memory table that only compares materialised representations has already conceded the largest available saving.

**Fragmentation is real and not measurable from Python.**
Freeing 90% of a large list does not return 90% of the memory to the OS, because pymalloc's arenas are only returned when entirely empty (Deep B). A program whose peak is high stays high in RSS terms even after the peak passes.

---

## 89.5 Connections

**Backward.**
Choosing the container by its time cost model is Chapter 88; this chapter is the same decision under the other resource. Measuring the exponent, which memory has as well, is Chapter 87. `sys.getsizeof`, `__slots__`, and instance layout as mechanisms are Deep A (Chapter 107). The allocator, arenas, and why freed memory does not return to the OS are Deep B. `tracemalloc` as a tool is Chapter 85 (Deep O).

**Forward.**
Caching, which trades memory for time deliberately rather than accidentally, is Chapter 90. Streaming, which is the decision not to hold the data at all, is Chapter 91. When the trade is worth escaping Python for, and where the packed representations pay off, is Chapter 92. Buffers and `memoryview` are Chapter 79. NumPy's arrays, the packed representation with vectorised operations attached, are Deep T.

**Across books.**
This chapter is where the two books' object models differ most starkly and the consequence is arithmetic. **Book I** stores a coordinate pair in 16 bytes; Book II's cheapest equivalent is 88. That is not a criticism of either: the 72-byte difference buys dynamic typing, introspection, garbage collection, and the ability to add a method at runtime. The shared system spends it where those properties matter and packs the data where they do not, and the seam is exactly the line between the two.

---

## 89.6 Exercises

**1. Difference the header out.** Reproduce §89.1's first block for `set`, `dict`, and `str`. Explain why the set and dict figures are less clean than the list and array figures, in terms of load factor and resizing.

**2. Build a deep sizer.** Write a function that walks an object graph and reports its true size, tracking `id()` so shared objects are counted once. Run it on a structure from your own code and compare with `sys.getsizeof`.

**3. Break the shared keys.** Build 100,000 instances of a class, measure with `tracemalloc`, then set one extra attribute on half of them and measure again. Explain the difference.

**4. Find the crossover.** For a workload that both stores and repeatedly sums a large array of numbers, find the size at which `array.array` becomes the better total choice on your machine, accounting for both the 5.4x memory saving and the 1.63x access cost.

**5. Peak against steady state.** Write a program whose peak allocation is three times its final allocation, measure both with `tracemalloc`, and describe a production failure mode that only the peak predicts.

**6. The design question.** CPython could store small integers unboxed inside a list, as some language runtimes do with tagged pointers or NaN-boxing. Argue why it does not: what `PyObject *` uniformity buys the C-API (Chapters 81 and 82), what tagging would break for extensions, and why `array.array` and NumPy exist as the sanctioned alternative rather than the list being made adaptive.

---

## 89.7 Summary and cross-references

- **Every value is an object with a header, and every container stores pointers.** A `list`, a `tuple`, and an `array.array('q')` all cost **8 bytes per element**, but the first two spend that on a pointer and the third on the number itself.
- **`sys.getsizeof` is shallow.** A list of 100 distinct objects and a list of 100 `None`s report the same size. Any estimate built from it alone is a count of pointers.
- **Measured with `tracemalloc`, a million integers cost 44.4 bytes each as a list and 8.2 packed** (**5.4x**). A `tuple` saves nothing, because the saving it offers is in the container and the cost is in the elements.
- **`__slots__` is the largest single-line memory win for objects:** 344 bytes against 48 for two attributes standalone (**7.2x**), and **87.9 bytes per pair against 128** in bulk, which also beats a plain `(x, y)` tuple at 95.9.
- **Ordinary instances are cheaper than the standalone figure suggests** because of the shared-keys optimisation (3.11+), which holds only while every instance of a class has the same attributes.
- **A smaller representation is not automatically faster.** Summing 100,000 numbers costs 1.17 ms out of a list, **1.63x** out of an `array.array` and **1.70x** out of a `memoryview`, because every packed element read constructs a Python `int`.
- **So the rule is: choose from what CONSUMES the data.** Packed wins outright when the consumer takes a buffer (C routine, socket, hash, NumPy) and loses when the data is walked element by element in Python.
- **Edges:** `tracemalloc` sees the Python allocator only; peak is not steady state; `__slots__` blocks dynamic attributes and some multiple inheritance; small integers and interned strings flatter every measurement; freed memory does not return to the OS.

**Cross-references.** Container choice by time → Chapter 88. Measuring exponents → Chapter 87. `__slots__` and instance layout → Deep A. The allocator and arenas → Deep B. `tracemalloc` → Chapter 85. Caching → Chapter 90. Streaming → Chapter 91. The escape decision → Chapter 92. Buffers → Chapter 79. NumPy → Deep T.
