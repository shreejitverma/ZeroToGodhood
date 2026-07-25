# Chapter 98: Dtypes, Precision, and Memory

The default NumPy float is `float64`, and for a large array that default is often the wrong choice. A
`float64` uses 8 bytes per element; a `float32` uses 4. So a million-element array is 8 MB as `float64` and 4 MB
as `float32`, *half the memory*, and, because the CPU moves half the bytes, fits twice as many elements in
cache, and processes more per SIMD instruction, the `float32` computation is also *faster*, up to **3.2x** on
this memory-bound sum. The cost is *precision*: `float32` carries ~7 significant digits where `float64` carries
~15, and it cannot even represent every integer above 2^24 (`float32(16_777_217)` rounds to `16_777_216`). So
the dtype is a real engineering decision, memory and speed versus precision, and getting it right is why machine
learning runs on `float32` (embeddings, weights, activations are approximate, and half the memory is decisive)
while numerical science stays on `float64` (accumulation error and ill-conditioning demand the digits).

This chapter continues **Deep T** with dtypes: the memory/precision/speed trade, when each width is right, and
the precision limits that bite. It is Chapter 35's float-representation lesson applied to the *choice of width* in
array computing.

## Section index

- **98.1** Half the memory, fewer digits
- **98.2** Choosing a width
- **98.3** Measurement: float32 is smaller and faster
- **98.4** Edges and failure modes
- **98.5** Connections
- **98.6** Exercises
- **98.7** Summary and cross-references

Listings live under `code/ch098/` and are re-executed by `make verify` on both interpreters (both with NumPy
2.1.3).

---

## 98.1 Half the memory, fewer digits

```python
# code/ch098/l01_dtypes.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- width: float32 is half the memory of float64 ---
  float64 itemsize : 8 bytes
  float32 itemsize : 4 bytes
  1,000,000 float64 : 8,000,000 bytes
  1,000,000 float32 : 4,000,000 bytes  (half)
--- precision: float32 has ~7 significant digits, float64 ~15 ---
  float32 precision (digits) : 6
  float64 precision (digits) : 15
  float32(0.1)+float32(0.2) : 0.30000001192092896
  float64(0.1)+float64(0.2) : 0.30000000000000004
--- float32 cannot represent every integer above 2^24 ---
  float32(16_777_216) : 16777216.0   (2^24, exact)
  float32(16_777_217) : 16777216.0   (2^24+1, rounded down!)
  float64(16_777_217) : 16777217.0   (exact)
--- the rule ---
  float32: large approximate data (ML, images) - half memory, ~2x speed
  float64: precision-sensitive science (accumulation, ill-conditioning)
```

The **memory** fact is exact: `float64` is 8 bytes per element, `float32` is 4, so an array's footprint (and
every temporary derived from it) is *halved* by choosing `float32`. The **precision** fact is the trade:
`float32` has ~7 significant digits (NumPy reports 6 guaranteed), `float64` ~15. `float32(0.1) + float32(0.2)` is
`0.30000001...`, visibly less precise than `float64`'s `0.30000000000000004` (both wrong, Chapter 35, but
`float32` wrong in the *7th* digit versus the *17th*).

The sharpest precision limit: `float32` cannot represent every *integer* above **2^24** (16,777,216). `float32(16_777_217)`
(2^24 + 1) rounds *down* to `16_777_216`, because a 32-bit float has only 24 bits of mantissa, so consecutive
integers stop being representable past 2^24. `float64` (53-bit mantissa) is exact up to 2^53. This matters for
IDs, counts, or indices stored as `float32`, above 16 million they *silently collide*.

---

## 98.2 Choosing a width

The dtype is chosen by weighing three axes, memory, speed, precision, against the *nature of the data*.

**Use `float32` (or narrower) for large, approximate data.** Machine-learning tensors, embeddings, model weights,
activations, image pixels, are *inherently approximate* (a weight of 0.7134 versus 0.7134001 makes no
difference to a model), and they are *large* (millions to billions of elements). Here `float32` is the standard:
half the memory (fitting bigger models/batches), up to ~2x the speed (memory-bound throughput), and enough
precision. Modern ML pushes *further*, `float16`/`bfloat16` (2 bytes) and `int8` quantization trade more
precision for more memory and speed, because the models tolerate it.

**Use `float64` for precision-sensitive computation.** Numerical science, iterative solvers, accumulations over
many terms (Chapter 35's summation error compounds faster in `float32`), ill-conditioned linear algebra,
financial/physical simulations, needs the ~15 digits. The default `float64` is right here, and downcasting to
`float32` to "save memory" can *silently corrupt results* (lost digits, integer collisions, faster-diverging
error).

**Match integer widths too.** `int64` versus `int32` versus `int8` is the same trade for integers: narrower is
smaller and faster but overflows sooner (`int8` wraps at 128). Choose the smallest width that holds your range,
and remember NumPy integers *wrap silently* (Chapter 96), unlike Python's arbitrary-precision `int`.

The rule: **pick the smallest dtype that preserves the precision (and range) your computation requires.** Default
`float64` is *safe* but often *wasteful* for large approximate data; `float32` is the ML default; narrower types
are a deliberate quantization decision. Never downcast precision-critical accumulations, and never store large
integers (IDs, counts) as `float32` (2^24 collision) or a too-narrow int (overflow).

---

## 98.3 Measurement: float32 is smaller and faster

**Methodology.** `code/ch098/bench_dtypes.py`. `(x*x).sum()` over 5,000,000 elements as `float64` versus
`float32`, with the memory each uses. `min` per run. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64, NumPy
2.1.3.

| `(x*x).sum()`, 5,000,000 elements | time | memory |
|---|---|---|
| `float64` | **3.01 ms** | **38.1 MB** |
| `float32` | **0.93 ms** | **19.1 MB** |
| ratio | **3.2x faster** | **2.0x less** |

`float32` uses **exactly half** the memory (19.1 MB vs 38.1 MB, the array plus its `x*x` temporary) and runs
**3.2x** faster here. The memory halving is *guaranteed* (4 bytes vs 8); the speedup is *workload-dependent*, for
this *memory-bound* operation (the arithmetic is trivial, the cost is moving data), halving the bytes moved is
worth up to ~2-3x, while a compute-bound operation would see less. The point is that for the array work that
dominates numeric Python, mostly memory-bound elementwise and reduction operations over large arrays, `float32`
is *both* smaller *and* faster.

The rule: **for large approximate data, `float32` halves the memory and speeds up memory-bound work; reserve
`float64` for precision.** The memory saving alone often decides it, a model or batch that fits in `float32` but
not `float64`, or twice the data in the same RAM/VRAM, and the speedup is a bonus. The discipline is to choose the
dtype *deliberately* rather than accept the `float64` default: profile your precision needs (does the result
change meaningfully in `float32`?), and if not, take the 2x memory and up-to-3x speed. This is the array-computing
face of the book's recurring theme, match the representation to the data (Chapters 35, 39), now with memory *and*
speed on the line at scale.

---

## 98.4 Edges and failure modes

**Storing large integers as `float32`.** §98.1. Above 2^24 (~16.7M), consecutive integers collide (`16_777_217` →
`16_777_216`). Never store IDs, counts, or indices as `float32`; use `int64`/`int32`.

**Downcasting precision-critical results.** §98.2. `float32` loses digits and accumulates error faster; a solver,
long accumulation, or ill-conditioned problem downcast to `float32` can silently give wrong answers. Keep such
computations in `float64`.

**Silent integer overflow.** NumPy `int` types *wrap* (unlike Python `int`, Chapter 35): `int8(127) + int8(1)` is
`-128`. Choose a width that holds your range, and watch sums/products that can overflow (`np.sum` of `int8` can
overflow, pass `dtype=` to accumulate wider).

**Accidental upcasting.** Mixing dtypes upcasts: `float32_array + a_python_float` (a `float64`) or `+ int64` can
promote the result to `float64`, silently doubling memory. Keep operands the same dtype, or cast explicitly, to
stay in `float32`.

**`float16`/`bfloat16` range and precision.** Half-precision (2 bytes) has a *tiny* range (`float16` overflows
past ~65504) and ~3 digits; useful for ML with care (mixed precision keeps a `float32` master copy), dangerous
for general use. Know its limits before quantizing.

**Assuming `float32` is always faster.** For *compute-bound* work, or tiny arrays, or when an operation upcasts
internally, `float32` may not be 2x (or faster at all). Measure; the memory saving is guaranteed, the speedup is
not.

---

## 98.5 Connections

**Backward.** Float representation, precision, and the 0.1+0.2 error are Chapter 35; integer overflow (fixed-
width vs Python's arbitrary-precision) is Chapters 35, 96. The compact typed storage is `array.array` (Chapter
39). SIMD and memory bandwidth are a Deep T hardware theme.

**Forward.** Mixed-precision training, quantization (`int8`, `bfloat16`), and GPU dtypes are Deep T ML topics.
Structured/record dtypes (heterogeneous fields) are the next Deep T material. `np.finfo`/`np.iinfo` for
introspecting limits are Deep T tooling.

**Across books.** Dtype choice is how Book II fits **Book III**'s data in memory and moves it fast. A **Book III**
system stores embeddings and model weights as `float32` (half the RAM/VRAM of `float64`, near-double the
throughput, and enough precision), quantizes to `int8`/`float16` where the model tolerates it for further wins,
and keeps precision-critical numeric code (a metric accumulation, a solver) in `float64`. The §98.1 precision
limits, especially the 2^24 integer collision, are exactly the silent-corruption traps that a careless dtype
choice creates on large data, which **Deep T** and **Deep U** guard against.

---

## 98.6 Exercises

**1. Measure both axes.** Run §98.3's benchmark and confirm `float32` uses half the memory and runs faster.
Explain why the memory saving is exact and the speedup is workload-dependent.

**2. Hit the 2^24 wall.** Show `float32` cannot represent `16_777_217` while `float64` can, and explain the
mantissa-bits reason. Explain why storing IDs as `float32` is dangerous.

**3. Watch an overflow.** Sum a large `int8` array and show the result overflow, then fix it with a wider
accumulation dtype. Explain NumPy's silent integer wrapping.

**4. Compare precision.** Accumulate a long sum in `float32` and `float64` and compare the error against an exact
(`Fraction`) reference. Explain why `float32` error is larger.

**5. The design question.** `float32` halves memory and often speeds up work, at a precision cost. Argue how to
choose a dtype. Your answer must use the §98.3 measurement, the precision limits (digits and the 2^24 integer
wall), and the ML-vs-science divide.

---

## 98.7 Summary and cross-references

- A NumPy **dtype fixes element width**: `float64` is 8 bytes / ~15 digits, `float32` is 4 bytes / ~7 digits (and
  cannot represent every integer above **2^24**). The dtype is a **memory/precision/speed** decision.
- **Measured:** `float32` uses **exactly half** the memory of `float64` (19.1 vs 38.1 MB) and runs **3.2x** faster
  on this memory-bound reduction (speedup is workload-dependent; the memory halving is guaranteed).
- **Use `float32` for large approximate data** (ML tensors, images, embeddings), narrower (`float16`/`int8`) as a
  deliberate quantization; **use `float64` for precision-sensitive science** (accumulation, ill-conditioning).
- **Edges:** never store large integers/IDs as `float32` (2^24 collision); NumPy ints wrap silently (overflow);
  mixing dtypes upcasts (silent memory doubling).

**Cross-references.** Float representation/precision → Chapter 35; integer overflow → Chapters 35, 96. Typed
storage → Chapter 39. Vectorization/SIMD → Chapters 96, Deep T. Mixed precision/quantization, structured dtypes →
the rest of Deep T. The numeric-data seam → Deep U.
