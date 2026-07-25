# Chapter 89: `TypedDict`

Data arrives as dicts, a JSON body from an API, a row from a database, a config, `**kwargs`, and you want the
type checker to know its shape: that `user["id"]` is an `int` and `user["name"]` is a `str`, and that
`user["emial"]` is a typo. The instinct is to convert each dict into a dataclass to "make it typed". That works,
and it *costs*: building a dataclass instance per record allocates an object and runs `__init__`, **6.3x** slower
than just using the dicts. `TypedDict` is the tool that types dict-shaped data *in place*: it declares the keys
and value types for the static checker, while at runtime the value *is* a plain `dict`, no conversion, no new
object, no unwrapping. Static structure over the data you already have, at zero runtime cost, because a
`TypedDict` *is* the dict (Chapter 86's erasure again).

This chapter continues **Deep I** with `TypedDict`: how it types dicts without changing them, why that is free
where converting to a dataclass costs, and when each is right. It is the dict-shaped counterpart to the
`dataclass` of Chapter 13.

## Section index

- **89.1** A dict that the checker understands
- **89.2** `TypedDict` vs `dataclass`
- **89.3** Measurement: in-place vs conversion
- **89.4** Edges and failure modes
- **89.5** Connections
- **89.6** Exercises
- **89.7** Summary and cross-references

Listings live under `code/ch089/` and are re-executed by `make verify` on both interpreters.

---

## 89.1 A dict that the checker understands

```python
# code/ch089/l01_typeddict.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a TypedDict is a plain dict at runtime ---
  type(UserTD(...))     : dict
  isinstance(u, dict)   : True
  access by key         : 1, Ada
  equals a plain dict   : True
--- so JSON data needs NO conversion to be typed ---
  used in place, still a dict : True
  no new object allocated     : True
--- a dataclass is a real object: attribute access, but a conversion ---
  type(UserDC(...))     : UserDC
  attribute access      : 2, Bjarne
  a new object per dict : True
--- the rule ---
  TypedDict: type dict-shaped data (JSON/kwargs/config) IN PLACE, free
  dataclass: a real typed object (attributes, methods, validation), at a
             per-record conversion cost
```

A `TypedDict` value is a **plain `dict` at runtime**: its `type` is `dict`, `isinstance(u, dict)` is `True`, you
access it *by key* (`u["id"]`), and it *equals* an ordinary dict with the same contents. The `class UserTD(...)`
declaration exists for the *checker*, it records that the dict has an `int` `"id"` and a `str` `"name"`, and a
static checker flags a wrong-typed value or a misspelled key, but the runtime object is just a dict.

The consequence is the middle block: **dict-shaped data needs no conversion to be typed**. A dict `from_json`
straight out of `json.loads` can be *annotated* as `UserTD` (`typed: UserTD = from_json`), and it stays the
*same object*, no new allocation, no copying. The static checker now treats it as a `UserTD` and checks every key
access, while the runtime does nothing extra. Contrast the dataclass: `UserDC(**from_json)` builds a *new object*
of type `UserDC`, with attribute access (`d.id`), but it is a *conversion*, a per-record cost the TypedDict
avoids.

---

## 89.2 `TypedDict` vs `dataclass`

Both give a static shape to a record; they differ in *what the record is at runtime* and therefore in *cost and
capability*.

A **`TypedDict`** is a `dict`. It gives static key/type checking with **zero runtime overhead** (it *is* the
data), stays **JSON-serializable** (it is already a dict, no `asdict` needed), and needs **no conversion** from
dict-shaped input. What it does *not* give: attribute access (you use `["key"]`, not `.key`), methods, default
values, validation, or a distinct runtime type (it is a plain dict, so `isinstance` cannot distinguish a `UserTD`
from any other dict).

A **`dataclass`** (Chapter 13) is a real object. It gives **attribute access** (`d.id`), **methods**,
**defaults**, optional **validation** (`__post_init__`), **immutability** (`frozen=True`), a **distinct runtime
type** (`isinstance(d, UserDC)`), and a compact footprint with `slots=True`. The price is that a `dataclass` is a
*new object* you must *build*, so dict-shaped input must be *converted* (a per-record cost, §89.3), and
serializing back to a dict/JSON needs `asdict`.

The rule: **use a `TypedDict` to type data that is *already* dict-shaped and that you mostly *read*, JSON
payloads, API responses, config, `**kwargs`, event records, where you want static safety without converting or
allocating.** Use a **`dataclass`** for a *domain object* you *construct and operate on*, where attribute access,
methods, validation, and a real runtime type are worth the per-record cost. The deciding questions: *is the data
already a dict?* (favor `TypedDict`), and *does it need behavior or a distinct runtime type?* (favor `dataclass`).
For a pipeline that reads millions of JSON records and extracts a few fields, `TypedDict` is far cheaper; for a
handful of rich domain objects, the `dataclass` cost is nothing and its capabilities are worth it.

---

## 89.3 Measurement: in-place vs conversion

**Methodology.** `code/ch089/bench_typeddict.py`. Reading a field from 1000 dict records (as from `json.loads`),
using them as `TypedDict`s in place versus converting each to a `dataclass` first. `min` per run; ratio relative
to the `TypedDict` approach. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| read a field from 1000 records | min per run | ratio |
|---|---|---|
| `TypedDict` in place | **18,391 ns** | 1.00x |
| convert to `dataclass` | **117,389 ns** | **6.38x** |

Using the dicts as `TypedDict`s reads the field in **18 us**, no conversion, they are already dicts. Converting
each to a `dataclass` first takes **117 us**, **6.4x** more, because it *allocates a `dataclass` object and runs
`__init__` for every record*. The gap is entirely the conversion: 1000 object allocations plus constructor calls
that the `TypedDict` path skips because it never leaves the dict representation.

The rule: **when data is already dict-shaped and you need static typing without behavior, use a `TypedDict`, it
is free; do not convert to a `dataclass` just to get types.** For a large volume of records you read (a
retrieval pipeline over JSON, a stream of events, an API returning thousands of rows), the 6.4x conversion cost,
plus the memory of a per-record object, is pure overhead if all you needed was typed key access, which `TypedDict`
gives for nothing. Reserve the conversion for when you genuinely need the `dataclass`'s capabilities on that
record (methods, validation, a distinct type). This is Chapter 86's erasure paying off again: the `TypedDict`'s
type information is compile-time only, so the runtime cost of "typing" the data is zero.

---

## 89.4 Edges and failure modes

**Converting to a dataclass just for types.** §89.3. 6.4x plus a per-record object, for what a `TypedDict` gives
free. If you only read dict data, type it with a `TypedDict` in place.

**Expecting a `TypedDict` to be a distinct runtime type.** §89.1. It is a plain dict; `isinstance` cannot
distinguish it from any other dict, and it has no runtime validation. For a distinct type or runtime checks, use
a `dataclass` (or validate at the boundary).

**Missing or extra keys at runtime.** A `TypedDict` does not enforce keys at runtime, a dict missing a required
key, or with extra keys, is still just a dict, and accessing a missing key raises `KeyError` at *use* time, not
at construction. The checker catches missing/typo'd keys statically; the runtime does not. Use `total=False` for
optional keys, and validate external dicts if you need runtime guarantees.

**`TypedDict` inheritance and `Required`/`NotRequired`.** TypedDicts compose (one can extend another) and mark
individual keys `Required`/`NotRequired` (PEP 655). Know these for partial/optional records rather than making
everything optional with `total=False`.

**Attribute access habits.** `TypedDict` uses `["key"]`, not `.key`; code written for objects will `AttributeError`
on a TypedDict. This is the visible cost of staying a dict; choose the record type by how the data is used.

**No methods.** A `TypedDict` cannot carry methods. If the record needs behavior, it is a `dataclass`/class, not a
`TypedDict`.

---

## 89.5 Connections

**Backward.** The zero runtime cost is Chapter 86's erasure (a `TypedDict` is compile-time structure over a
runtime dict). The `dataclass` alternative is Chapter 13 (and `slots=True` for its footprint). The `dict` it is
at runtime is Chapter 32. `NewType` (Chapter 87) is the same zero-cost-static-typing idea for scalars.

**Forward.** Validation libraries (`pydantic`'s `BaseModel`/`TypedDict` support) that *do* enforce the shape at
runtime are a Deep I/Deep O application, use them at trust boundaries where dict data is untrusted. Generic and
nested TypedDicts, and `get_type_hints` over them, are the rest of **Deep I**. JSON schema and serialization are
Deep R/Deep U.

**Across books.** `TypedDict` is how Book II types the JSON that flows to and from **Book III** without paying to
objectify it. A **Book III** service types API request/response bodies, tool-call arguments, and event records as
`TypedDict`s, so the checker verifies field access across the pipeline while the data stays plain dicts, JSON-
serializable, cheap, no conversion, and reserves `dataclass`es for its few real domain objects. The §89.3
conversion cost is why the high-volume dict path uses `TypedDict` and only the domain layer builds objects.
**Deep U** owns the JSON seam; runtime validation of untrusted dicts (`pydantic`) is a boundary concern.

---

## 89.6 Exercises

**1. See the runtime dict.** Reproduce §89.1: show a `TypedDict` value is a plain dict (type, isinstance, key
access, equality) and that a JSON dict can be typed in place with no new object. Explain where the type info
lives.

**2. Measure the conversion.** Run §89.3's benchmark and confirm converting dicts to dataclasses costs several
times more than using TypedDicts. Explain what the conversion allocates and runs.

**3. Choose the record.** For several cases (a JSON API response you read, a domain object with methods, a config
dict, a validated form), pick `TypedDict` or `dataclass` and justify each by the two questions (already a dict?
needs behavior?).

**4. Handle optional keys.** Use `total=False` (or `NotRequired`) for optional keys and show the checker treats
them as possibly-absent. Explain why the runtime still does not enforce keys.

**5. The design question.** `TypedDict` types dicts in place at zero cost; a `dataclass` builds a real object at a
cost. Argue when each is right. Your answer must use the §89.3 measurement, the capability differences (attribute
access, methods, distinct type), and Chapter 86's erasure.

---

## 89.7 Summary and cross-references

- A **`TypedDict`** declares keys and value types for the **static checker** while at runtime it **is a plain
  `dict`**, no new type, no conversion, no per-record object. It types dict-shaped data (JSON, `**kwargs`, config)
  **in place** at zero runtime cost (erasure, Chapter 86).
- A **`dataclass`** is a real object (attribute access, methods, defaults, validation, distinct runtime type,
  `slots`), but dict input must be **converted** to it, a per-record cost.
- **Measured:** using 1000 dicts as `TypedDict`s is **6.4x** cheaper than converting each to a `dataclass` (18 us
  vs 117 us), because conversion allocates an object and runs `__init__` per record.
- **Use `TypedDict`** for already-dict data you mostly read (free, JSON-serializable, no conversion); use a
  **`dataclass`** for domain objects needing behavior or a distinct runtime type. `TypedDict` does not enforce
  keys/types at runtime, validate untrusted dicts at the boundary.

**Cross-references.** Erasure → Chapter 86; `NewType` → Chapter 87. `dataclass`/`slots` → Chapters 13, 4. `dict` →
Chapter 32. `pydantic` runtime validation → Deep I, Deep O. The JSON seam → Deep U, Deep R.
