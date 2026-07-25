# Chapter 95: Variance

A function takes `things: list[Animal]`, and you try to pass a `list[Dog]`, every `Dog` *is* an `Animal`, so a
list of dogs *is* a list of animals, right? The type checker says no, and it is *saving you from a real bug*. If
`list[Dog]` were accepted as `list[Animal]`, the function, seeing a `list[Animal]`, could `append` a plain
`Animal` (or a `Cat`) to it, and then your original `list[Dog]` would contain a non-dog, so the next `dog.bark()`
would raise `AttributeError`. This chapter *demonstrates that exact runtime failure*. Because a `list` is
**mutable**, it is **invariant**: `list[Dog]` is *not* a `list[Animal]`, and the checker forbids the substitution
to prevent the unsound write. A **read-only** container, a `tuple` or `Sequence`, is **covariant**: `tuple[Dog]`
*can* stand in for `tuple[Animal]`, because you cannot write to it, so nothing unsound can happen. The practical
payoff: type a parameter you only *read* as a general read-only type (`Iterable`/`Sequence`), and callers can
pass *anything*, a list, tuple, generator, set, with no conversion; demand a concrete `list` and you force
callers to materialize (measured, **1.22x** slower plus O(n) memory to convert a generator).

This chapter closes **Deep I** with variance: why mutability drives it, the runtime unsoundness invariance
prevents, and the accept-general-return-concrete rule it implies. It is the one type-system concept whose
*motivation* is a concrete runtime bug.

## Section index

- **95.1** Invariant, covariant, and the unsound write
- **95.2** Accept general, return concrete
- **95.3** Measurement: demanding a list forces conversion
- **95.4** Edges and failure modes
- **95.5** Connections
- **95.6** Exercises
- **95.7** Summary and cross-references

Listings live under `code/ch095/` and are re-executed by `make verify` on both interpreters.

---

## 95.1 Invariant, covariant, and the unsound write

```python
# code/ch095/l01_variance.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- an Iterable parameter accepts any iterable, no conversion ---
  total([1, 2, 3])            : 6
  total((4, 5))               : 9
  total(i for i in range(3))  : 3
  (a list[int] parameter would force callers to convert first)
--- why a MUTABLE list is invariant: the unsound write it prevents ---
  after appending an Animal, the 'list of Dogs' has : ['Dog', 'Animal']
  calling .bark() on the non-Dog raises AttributeError : True
  the checker forbids list[Dog] as list[Animal] to prevent exactly this
--- a READ-ONLY tuple/Sequence is covariant (safe, no writes) ---
  tuple[Dog] usable as tuple[Animal] (read-only, no unsound write) : True
  its element barks: 'woof'
--- the rule ---
  mutable containers: invariant. read-only containers: covariant.
  type a read-only parameter as Iterable/Sequence, return a concrete list
```

The middle block is the whole justification, made concrete at runtime. Treat a `list[Dog]` as a `list[Animal]`
(the substitution the checker forbids), `append` a plain `Animal` to it through that view, and now the list, which
your other code still believes is a `list[Dog]`, contains `['Dog', 'Animal']`. Reading the second element back as
a `Dog` and calling `.bark()` raises `AttributeError`, because it *is not* a dog. That is the bug invariance
prevents: **a mutable container cannot safely be used as a container of a supertype, because a write of a
supertype value corrupts it for readers expecting the subtype.** So `list` (and `dict`, `set`, any mutable
generic) is **invariant**.

The read-only case is safe. A `tuple[Dog]` or `Sequence[Dog]` *can* be used as `tuple[Animal]`/`Sequence[Animal]`
(**covariant**), because there is *no write*, you can only *read* elements, and reading a `Dog` where an `Animal`
is expected is always fine (a `Dog` *is* an `Animal`). No write means no way to corrupt it, so the substitution
is sound. The pattern is general: **mutability forces invariance; read-only permits covariance.**

---

## 95.2 Accept general, return concrete

Variance turns into a concrete API-design rule. Because read-only containers are *covariant* and mutable ones are
*invariant*, the way to make a function *flexible* for callers is to type each parameter you only *read* as the
most general *read-only* type that supports what you do with it:

- Only iterate it? Type it **`Iterable[T]`**, then a list, tuple, set, generator, dict-keys, anything iterable,
  passes with no conversion (the first block: `total` accepts all of them).
- Need indexing/length? Type it **`Sequence[T]`** (covariant, read-only), accepting lists and tuples.
- Need key lookup? Type it **`Mapping[K, V]`** (read-only), accepting dicts and other mappings.

Demand a *concrete, mutable* type (`list[T]`, `dict[K, V]`) only when you actually *mutate* it. A parameter typed
`list[int]` says "I will modify this list", and forces every caller to hand you a *real, mutable list*, so a
caller with a tuple or generator must *convert* (`list(...)`), which allocates (§95.3) and, for a large or lazy
source, materializes what could have streamed.

Conversely, **return concrete types**: a function *returning* a value should return a specific `list[int]` (not
`Iterable[int]`), so the caller gets the full capabilities (indexing, length, mutation) of the concrete type. The
rule, a typing analogue of Postel's law ("be liberal in what you accept, conservative in what you produce"): **accept
the most general read-only type your logic needs; return the most specific type you actually have.** This makes
your functions maximally reusable (any compatible input works) while giving callers of your *results* the most to
work with, and it is *founded* on variance: accepting `Iterable`/`Sequence` is safe and flexible *because* they
are covariant.

---

## 95.3 Measurement: demanding a list forces conversion

**Methodology.** `code/ch095/bench_variance.py`. Summing a 1000-element generator through a function typed
`Iterable[int]` (pass the generator directly) versus one typed `list[int]` (the caller must `list(...)` it
first). `min` per run; ratio relative to the `Iterable` version. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| sum a generator | min per run | ratio |
|---|---|---|
| `Iterable` param (pass generator) | **16,461 ns** | 1.00x |
| `list` param (`list(gen)` first) | **20,113 ns** | **1.22x** |

Accepting `Iterable` sums the generator *directly*, streaming it, no intermediate container. Demanding `list`
forces the caller to `list(gen)` first, allocating a 1000-element list *before* the call, which costs **1.22x**
in time *and* O(n) memory the streaming path never uses. The time ratio is modest here because the list is small
and `sum` is fast; the *memory* cost is the sharper one, for a large or lazy source (a million-row stream), the
forced `list()` materializes the whole thing, turning constant-memory streaming into O(n) (Chapter 9), which can
be the difference between a program that fits in memory and one that does not.

The rule: **type read-only parameters as the general covariant types (`Iterable`/`Sequence`/`Mapping`), not
concrete `list`/`dict`.** It is founded on variance (those read-only types are covariant, so they safely accept
subtypes and related types) and it pays off in both flexibility (callers pass anything without converting) and
performance (no forced materialization, streaming preserved). Reserve concrete mutable parameter types for when
you genuinely mutate the argument. As with the rest of the book's guidance, the general, correct choice is also
the more efficient one, accepting `Iterable` costs the caller nothing and avoids an allocation, while demanding
`list` costs a conversion. And it closes Deep I on a rule that is *not* about erasure: variance is a real
constraint that shapes how you design typed APIs, and getting it right makes typed code both safer and faster.

---

## 95.4 Edges and failure modes

**Passing `list[Sub]` where `list[Base]` is wanted.** §95.1. Rejected (invariance) to prevent the unsound write.
If the function only *reads* the list, it should accept `Sequence[Base]` (covariant), which *does* accept
`Sequence[Sub]`; then the substitution works.

**Demanding `list`/`dict` when you only read.** §95.2. Forces callers to convert (allocation, lost streaming).
Accept `Iterable`/`Sequence`/`Mapping` unless you mutate the argument.

**Returning an overly general type.** Returning `Iterable[int]` when you have a `list` denies the caller indexing/
length. Return the concrete type you have.

**Assuming all generics are invariant.** Read-only protocols (`Sequence`, `Mapping`, `Iterable`, `frozenset`) are
covariant; `Callable` is *contravariant* in its parameters (a function taking `Animal` can stand in for one taking
`Dog`); mutable containers are invariant. The variance is a property of *the type*, not a uniform rule.

**Mutating a parameter typed as read-only.** If you *do* mutate a parameter, typing it `Sequence`/`Iterable` is a
lie (they have no mutation methods, and the checker will reject `xs.append`). Type it `list`/`MutableSequence`
when you mutate, and only then.

**Custom generic variance.** When you write your own generic class, its TypeVar's variance (`covariant=True`,
`contravariant=True`, or invariant default; or PEP 695 inference) must match how the class uses `T`, covariant if
`T` is only produced (returned), contravariant if only consumed (parameters), invariant if both. Getting it wrong
either over-restricts or is unsound.

---

## 95.5 Connections

**Backward.** The mutability that drives variance is the value-semantics and mutable-vs-immutable theme of
Chapters 4 and 37 (tuple/frozenset). The `Iterable`/`Sequence` protocols are Chapter 69 (iterator protocol) and
`collections.abc`. The streaming vs materializing cost is Chapter 9. Subtyping and inheritance are Chapter 4.

**Forward.** Custom generic-class variance (`ParamSpec`, variance inference in PEP 695) is advanced **Deep I**.
The `collections.abc` hierarchy of read-only vs mutable protocols is Chapter 69 and Deep I. Designing typed APIs
(accept-general/return-concrete) is a Deep I/Deep U design principle.

**Across books.** Variance-aware parameter typing is how Book II makes its typed functions maximally reusable for
**Book III** without forcing conversions. A **Book III** pipeline stage that only iterates its input types the
parameter `Iterable[Doc]`, so an upstream stage can hand it a lazy generator of documents that streams through in
constant memory, no materialization, no `list()`, and returns a concrete `list[Result]` for the next stage to
index. The §95.3 forced-materialization cost is exactly what a `list[Doc]` parameter would impose on a streaming
corpus, defeating the laziness **Deep U** relies on at the pipeline seam. Variance, correctly applied, keeps typed
pipelines both sound and lazy.

---

## 95.6 Exercises

**1. Reproduce the unsoundness.** Reproduce §95.1: alias a `list[Dog]` as a list, append an `Animal`, and show
`.bark()` fails on the non-dog. Explain why the checker forbids `list[Dog]` as `list[Animal]`.

**2. Covariant read-only.** Show a `tuple[Dog]`/`Sequence[Dog]` can be used where a `tuple[Animal]`/
`Sequence[Animal]` is expected (with a checker), and explain why read-only makes it safe.

**3. Accept general.** Change a function from a `list[int]` parameter to `Iterable[int]` and show it now accepts a
generator, tuple, and set with no conversion. Run §95.3's benchmark to show the conversion the `list` version
forced. Explain the flexibility and cost.

**4. Get variance right in your own class.** Write a read-only generic container and declare its TypeVar
covariant; show the checker accepts a subtype parameterization. Then make it mutable and show it must be invariant.
Explain the produced-vs-consumed rule.

**5. The design question.** Mutable containers are invariant, read-only ones covariant. Argue how this shapes API
design (accept general read-only types, return concrete). Your answer must use the §95.1 unsoundness, the §95.3
cost, and the accept-general/return-concrete principle.

---

## 95.7 Summary and cross-references

- **Variance** decides when a container of a subtype can substitute for one of a supertype. A **mutable** `list`
  is **invariant** (`list[Dog]` is *not* `list[Animal]`), preventing an unsound write (appending an `Animal`
  corrupts it for `Dog` readers, a real `AttributeError`). A **read-only** `tuple`/`Sequence` is **covariant**
  (safe, no writes); `Callable` parameters are **contravariant**.
- **Mutability forces invariance; read-only permits covariance.**
- **Design rule (from variance):** **accept the most general read-only type** (`Iterable`/`Sequence`/`Mapping`)
  for parameters you only read, so callers pass anything without converting; **return concrete types** for full
  caller capability.
- **Measured:** demanding a `list` parameter forces a caller with a generator to `list()` it, **1.22x** slower
  and O(n) memory the `Iterable` streaming path avoids. Reserve concrete/mutable parameter types for when you
  mutate the argument.

**Cross-references.** Mutability/immutability → Chapters 4, 37. `Iterable`/`Sequence`/`collections.abc` → Chapter
69. Streaming vs materializing → Chapter 9. Subtyping → Chapter 4. Custom generic variance, `ParamSpec` → Deep I.
The typed-pipeline seam → Deep U.
