# Chapter 42: Serialization - `json` and `pickle`

A team caches computed results by pickling them to disk, and one day an attacker who can write to that
cache directory, or substitute a file, achieves remote code execution: `pickle.loads` on the poisoned file
runs their code. The team's instinct afterward is "pickle is slow and unsafe, we should have used json for
speed." Half right. Pickle *is* unsafe on untrusted input, that is the real lesson, but it is not slow. On a
1000-record structure, `pickle` is **3.3x faster to serialize** and **2.6x faster to load** than `json`,
and its binary output is **half the size** (35 KB vs 65 KB). The reason to prefer `json` is not
performance; on performance `json` loses. The reasons are **safety** (`json.loads` can never execute code)
and **interoperability** (every language reads JSON; only Python reads pickle).

Getting that trade-off right, choosing a serializer on the axes that actually differ, is this chapter's
purpose. It continues **Deep R** with the two standard-library serializers, `json` (text, universal, data-
only, safe) and `pickle` (binary, Python-only, all-types, executes code on load), and the rule for which
belongs where.

## Section index

- **42.1** Two serializers, two contracts
- **42.2** Why pickle is a code-execution format
- **42.3** Measurement: speed and size
- **42.4** Edges and failure modes
- **42.5** Connections
- **42.6** Exercises
- **42.7** Summary and cross-references

Listings live under `code/ch042/` and are re-executed by `make verify` on both interpreters.

---

## 42.1 Two serializers, two contracts

```python
# code/ch042/l01_serialize.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- type coverage: json is data-only; pickle takes most objects ---
  json round-trip     : {'name': 'Ada', 'tags': ['a', 'b'], 'count': 3}
  json.dumps(set)     : TypeError (Object of type set is not JSON serializable)
  pickle round-trip set: {1, 2, 3}
--- the security difference: unpickling runs code ---
  pickle.loads(untrusted):
      [!] code executed during unpickle
  json.loads never runs code: it only ever produces data
--- json is human-readable text; pickle is opaque binary ---
  json.dumps(data)    : {"name": "Ada", "tags": ["a", "b"], "count": 3}
  pickle is bytes     : starts with b'\x80' (PROTO opcode), 58 bytes total
```

**`json`** encodes *data*, and only the JSON data model: `dict`, `list`, `str`, `int`, `float`, `bool`,
`None`. A `set` is not JSON-serializable (`TypeError`), and neither is a `datetime`, a custom class, or a
tuple-as-tuple (tuples become lists). The output is human-readable UTF-8 text that any language can parse.
This narrowness is a feature: the format is a universal interchange contract, and `json.loads` produces
*only* data, never a live object with behavior.

**`pickle`** encodes almost any Python object, the `set` round-trips, and so do custom classes, closures'
referents, nested structures, by recording how to *reconstruct* it. The output is opaque binary (it starts
with the `\x80` PROTO opcode). That reconstruction power is exactly the danger of §42.2: the pickle does not
just describe data, it describes a *program* to rebuild the object, and loading it runs that program.

---

## 42.2 Why pickle is a code-execution format

The middle block is the security demonstration. A class can define `__reduce__` to control how it is
pickled, returning a callable and its arguments to invoke on load. The listing's `Exploit.__reduce__`
returns `(print, ("...",))`, so `pickle.loads` *calls* `print` during loading, the injected message appears.
`print` is harmless, but the mechanism is general: `__reduce__` can return `(os.system, ("rm -rf ...",))` or
any callable, and `pickle.loads` will invoke it. **Unpickling untrusted data is arbitrary code execution.**

`json.loads` has no such mechanism. It is a parser that builds data structures and nothing else; there is no
hook by which JSON content can name a callable to invoke. Feeding `json.loads` the most hostile string
possible yields, at worst, a `ValueError` or a large data structure, never code execution. That asymmetry is
the whole security case, and it is decisive: **never unpickle data from any source you would not run code
from.** A file another process can write, a network payload, a user upload, a cache another tenant can reach,
all are untrusted for pickle's purposes. For those, use `json` (or another data-only format), and if you
need pickle's power internally, sign the data or keep it on a trust boundary you control.

---

## 42.3 Measurement: speed and size

**Methodology.** `code/ch042/bench_serialize.py`. Dumping and loading a nested structure of 1000 records
(`{id, name, active, score}`) with each serializer; sizes of the serialized output. `min` per call; ratios
relative to `json.dumps`. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | min per call | vs `json.dumps` |
|---|---|---|
| `json.dumps` | **379 us** | 1.00x |
| `pickle.dumps` | **114 us** | **0.30x** (3.3x faster) |
| `json.loads` | **318 us** | 0.84x |
| `pickle.loads` | **144 us** | 0.38x |
| serialized size | `json` **64,550 B** vs `pickle` **34,682 B** | json **1.86x larger** |

`pickle` wins every performance axis for this Python data: **3.3x faster to dump**, roughly **2.2x faster to
load** than `json` (144 us vs 318 us), and **half the size** (binary versus verbose text with quoted keys
and whitespace). This inverts the common assumption that `json` is the "fast, standard" choice, `json`'s C
encoder is fast in absolute terms, but pickle's binary format is faster still and more compact for Python-
to-Python data.

So the decision is *not* made on speed or size, and stating it that way is the point:

- **Use `json`** for anything crossing a **trust boundary** (untrusted input) or a **language boundary**
  (another service, a browser, a config a human edits). You accept the slower, larger, data-only format in
  exchange for safety and universality. This is the default for I/O that leaves your process.
- **Use `pickle`** only for **trusted, Python-to-Python** data where its speed, compactness, and full type
  coverage are worth Python lock-in, an internal cache you fully control, a `multiprocessing` message between
  your own processes. Never for anything an adversary can influence.

Choosing `json` "for speed" is choosing the slower option for the wrong reason; choosing `pickle` "because
it is faster" is walking into the security trap. Choose on trust and interop, which is where the formats
actually differ.

---

## 42.4 Edges and failure modes

**Unpickling untrusted data.** §42.2. Arbitrary code execution. Never `pickle.loads` anything you would not
execute as code. Use `json` across trust boundaries.

**JSON's type coverage.** §42.1. `set`, `datetime`, `bytes`, custom classes, and tuples-as-tuples are not
JSON types. Provide a `default=` function to `json.dumps` (e.g. serialize `datetime` to an ISO string,
Chapter 36) and reverse it on load, or the dump raises `TypeError`.

**JSON silently changes types.** `json` turns tuples into lists and non-string dict keys into strings
(`json.dumps({1: "a"})` yields `{"1": "a"}`). The round-trip is lossy for those; do not assume
`loads(dumps(x)) == x` for tuples or integer keys.

**Pickle version and class coupling.** A pickle records the class's module and name; unpickling requires that
class to be importable and compatible. Refactor the class (rename, move, change fields) and old pickles may
fail or misload. Pickle is a poor *long-term* storage format for evolving code.

**`json` floats and precision.** `json` serializes floats as decimal text and parses them back through
`float`, subject to Chapter 35's representation limits, and it emits `NaN`/`Infinity` by default, which
strict JSON parsers in other languages reject. Pass `allow_nan=False` for interoperable output.

**Large documents in memory.** Both `json.load(f)` and `pickle.load(f)` build the whole object in memory. For
huge documents, stream (line-delimited JSON, `ijson`, or a database) rather than loading a multi-gigabyte
blob at once, the same laziness discipline as Chapter 9 and Chapter 40.

---

## 42.5 Connections

**Backward.** The `str`/`bytes` boundary, `json` produces text, `pickle` produces bytes, is Chapter 7 and
Chapter 37. The `datetime` values `json` cannot natively encode (and their ISO-string workaround) are
Chapter 36. The float precision `json`'s decimal text inherits is Chapter 35. The file I/O both write through
is Chapter 40.

**Forward.** `pickle` is the wire format `multiprocessing` uses to send objects between processes, the IPC
material later in **Deep R**, which is safe there precisely because both ends are your own trusted Python.
Schema-checked and cross-language serialization at scale (Protocol Buffers, Arrow, msgpack) is **Deep U** and
**Deep T**. Signing/verifying serialized data is a security topic in **Deep S**.

**Across books.** The serializer choice is a trust-boundary decision Book II makes at every seam into
**Book III**. Data that crosses a network or process boundary to another system is `json` (or a schema
format), never `pickle`; internal Python-to-Python caches and `multiprocessing` payloads that stay inside the
trust boundary may be `pickle` for its speed and type coverage. Getting this wrong, pickling across an
untrusted boundary, is the classic deserialization vulnerability **Deep U** exists to prevent.

---

## 42.6 Exercises

**1. Reproduce the speed and size gap.** Run §42.3's benchmark and confirm `pickle` is faster and smaller
than `json` for Python data. Explain why (binary vs verbose text) and why this means speed is *not* the
reason to prefer `json`.

**2. Demonstrate the danger (safely).** Write a class whose `__reduce__` returns `(print, ("ran",))` and show
that `pickle.loads` invokes it. Explain how a real payload would substitute a harmful callable, and why
`json.loads` cannot be exploited the same way.

**3. Handle a non-JSON type.** Try to `json.dumps` a `datetime` and observe the `TypeError`. Then add a
`default=` function that serializes it to an ISO string (Chapter 36) and a reverse step on load. Explain why
`json` requires this and `pickle` does not.

**4. Show the lossy round-trip.** `json.dumps` a dict with a tuple value and an integer key, load it back, and
show the tuple became a list and the key became a string. Explain which round-trips are lossy and why.

**5. The design question.** Python ships both a safe/universal/slow serializer and a fast/powerful/dangerous
one. Argue why both exist rather than one. Your answer must address the security asymmetry the §42.2 demo
shows, why pickle's speed and type coverage are real advantages *inside* a trust boundary, and why the
default for anything leaving the process must be the data-only format.

---

## 42.7 Summary and cross-references

- **`json`** encodes only data (`dict`/`list`/`str`/`int`/`float`/`bool`/`None`) as universal, human-
  readable text; **`pickle`** encodes almost any Python object as opaque binary by recording how to
  reconstruct it.
- **`pickle.loads` runs code** (via `__reduce__`): unpickling untrusted data is arbitrary code execution.
  `json.loads` only ever produces data.
- **Measured:** for Python data, `pickle` is **3.3x faster to dump**, ~2.2x faster to load, and **half the
  size** of `json`. Performance is *not* the reason to choose `json`.
- **Choose on trust and interop:** `json` for anything crossing a trust or language boundary; `pickle` only
  for trusted, Python-to-Python data where its speed, size, and type coverage are worth the lock-in.

**Cross-references.** Text vs bytes → Chapters 7 and 37. `datetime` encoding → Chapter 36. Float precision →
Chapter 35. File I/O → Chapter 40. `multiprocessing` and pickle-as-IPC → the rest of Deep R. Cross-language
serialization → Deep U and Deep T. Signing serialized data → Deep S.
