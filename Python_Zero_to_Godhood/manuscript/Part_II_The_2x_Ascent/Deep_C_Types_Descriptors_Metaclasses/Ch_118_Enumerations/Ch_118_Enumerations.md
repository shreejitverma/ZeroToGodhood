# Chapter 37: Enumerations

The oldest bad habit in programming is the bare constant.
A status is `0`, `1`, or `2`; a direction is the string `"north"`; a permission is the magic number `4`.
Every one of these invites the same bugs: a typo (`"nrth"`) that no tool catches, a value out of range that means nothing, two unrelated codes that happen to share an integer, and a `print` that shows `1` where you wanted `RUNNING`.
`enum.Enum` (PEP 435, Python 3.4) replaces the bare constant with a **named, singleton member** that carries its name, refuses to be confused with a raw value, and is checkable, iterable, and self-documenting.

The object-model reason enums belong in Deep C is that each member is a **singleton** (Chapter 26): `Color.RED` is one object, the same one everywhere, so you compare members with `is` and identity is meaningful.
The class itself is built by a metaclass (`EnumType`/`EnumMeta`, Chapter 31) that intercepts the `NAME = value` assignments and turns them into members, which is why an enum body looks like class attributes but behaves like nothing else.
The measurement pins down the one performance-relevant fact: looking a member up *by value* (`Color(1)`) is about **7.9x** slower than referring to it by name (`Color.RED`), which tells you exactly where each belongs.

**This is the canonical home for enumerations.**
Members-as-singletons is Chapter 26; the enum class is built by a metaclass (Chapter 31); `IntEnum`/`Flag` interoperate with the numeric protocols of Deep A. It closes the "named value types" thread that dataclasses (Chapter 36) opened.

## Section index

- **37.1** `Enum`: named singleton members
- **37.2** Safety, `IntEnum` interop, and `Flag` sets
- **37.3** Measurement: name access versus value lookup
- **37.4** Edges and failure modes
- **37.5** Connections
- **37.6** Exercises
- **37.7** Summary and cross-references

Listings live under `code/ch118/` and are re-executed by `make verify` on both verification interpreters.

---

## 37.1 `Enum`: named singleton members

```python
# code/ch118/l01_enum_basics.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a member has a name and a value ---
  Color.RED        : Color.RED
  Color.RED.name   : RED
  Color.RED.value  : 1
  Color.BLUE.value : 3   (auto)
--- members are SINGLETONS: compare with is ---
  Color.RED is Color.RED : True
  Color(1) is Color.RED  : True   (value lookup)
  Color['RED'] is Color.RED : True   (name lookup)
--- the class is iterable, in definition order ---
  list(Color) names : ['RED', 'GREEN', 'BLUE']
--- a duplicate value is an ALIAS, not a new member ---
  Status.RUNNING is Status.ACTIVE : True
  iteration excludes aliases      : ['ACTIVE']
--- the rule ---
  Enum members are named singletons with .name/.value; compare with is,
  look up by name or value, iterate the class; duplicate values are aliases
```

An `Enum` subclass turns `NAME = value` assignments into **members**.
Each member has a `.name` (the identifier) and a `.value` (what you assigned), and `auto()` supplies the next value so you need not hand-number them (`BLUE` becomes `3`).
The member's `repr` shows `Color.RED`, not `1`, so logs and tracebacks are readable, the anti-bare-constant benefit in action.

The defining property is that members are **singletons** (Chapter 26).
There is exactly one `Color.RED` object, and all three ways of reaching it, the attribute `Color.RED`, the value lookup `Color(1)`, the name lookup `Color['RED']`, return the *same* object (`is` is `True`).
So you compare members with `is` (or `==`, which for enums is identity), and membership, dict keys, and `set` operations all work by identity, cleanly.
The class is also **iterable** in definition order (`list(Color)`), which is why enums are perfect for "all the valid options": you can loop them, build a dropdown, validate against them.

One subtlety worth knowing early: a **duplicate value creates an alias**, not a new member.
`Status.RUNNING = 1` where `ACTIVE = 1` already exists makes `RUNNING` a second *name* for the `ACTIVE` member (`Status.RUNNING is Status.ACTIVE`), and aliases do **not** appear in iteration (only canonical members do).
This is deliberate, it lets you provide synonyms, but it surprises people who expect two names to be two members. Use `@enum.unique` to forbid aliases when you want each value distinct.

---

## 37.2 Safety, `IntEnum` interop, and `Flag` sets

```python
# code/ch118/l02_intenum_flag.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a plain Enum member is NOT its value (safety) ---
  Color.RED == 1        : False   (not equal: avoids confusion)
  Color.RED.value == 1  : True   (the value is)
--- IntEnum members ARE ints (interop with numeric codes) ---
  Priority.HIGH == 2    : True
  Priority.HIGH + 1     : 3   (arithmetic works)
  isinstance(Priority.HIGH, int) : True
--- Flag: combine options with bitwise operators ---
  Perm.R | Perm.W       : Perm.R|W
  Perm.R in (R|W)       : True
  Perm.X in (R|W)       : False
  (R|W) & W             : Perm.W
--- the rule ---
  plain Enum is value-safe (member != raw value); IntEnum for numeric
  interop; Flag for bitwise sets of options
```

**Plain `Enum` is value-safe.**
`Color.RED == 1` is `False`: a plain enum member is *not* equal to its underlying value.
This is a feature, not a limitation, it stops the bare-constant confusion where a `Color` accidentally compares equal to an unrelated `1`, a byte, or another enum's member with the same value.
If you want the value, you ask for it (`Color.RED.value == 1`).
The enum is a distinct type, and the language keeps it distinct.

**`IntEnum` when you need the value's behaviour.**
Sometimes you *do* need the member to be its value, when interoperating with a C API, a wire protocol, or a database that stores numeric codes.
`IntEnum` members **are** real `int`s: `Priority.HIGH == 2` is `True`, `Priority.HIGH + 1` is `3`, and `isinstance(Priority.HIGH, int)` is `True`.
You trade the safety of §37.2's first block for interoperability, an `IntEnum` will compare equal to a bare int and to another `IntEnum`'s member of the same value, so use it only where that interop is the point.
(`StrEnum`, Python 3.11, does the same for strings.)

**`Flag` for sets of options.**
When values are combinable (permissions, feature bits, event masks), `Flag` members support bitwise `|`, `&`, `~`, and membership: `Perm.R | Perm.W` is a combined value, `Perm.R in (R|W)` is `True`, `(R|W) & W` extracts a bit.
This replaces the error-prone hand-rolled bitmask (`READ = 4`, `if perms & 4:`) with named, type-checked, self-describing flags (`IntFlag` is the int-compatible variant for C interop).

The three cover the space: **plain `Enum`** for value-safe named constants (the default), **`IntEnum`/`StrEnum`** for interop with external numeric/string codes, **`Flag`/`IntFlag`** for combinable option sets.

---

## 37.3 Measurement: name access versus value lookup

**Methodology.** `code/ch118/bench_enum.py`.
Reaching a member three ways: attribute (`Color.RED`), value lookup (`Color(1)`), name lookup (`Color['RED']`).
`min` of 5 runs, 5,000,000 accesses.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| reach a member | ns | vs attribute |
|---|---|---|
| `Color.RED` (attribute) | 17.2 | 1.0x |
| `Color['RED']` (name lookup) | 35.7 | 2.1x |
| `Color(1)` (value lookup) | 136.2 | **7.9x** |

Value lookup `Color(1)` is **7.9x** slower than the attribute `Color.RED` (6.8x on 3.14.6), and name lookup sits in between at 2.1x.
`Color.RED` is a direct attribute read on the enum class.
`Color(1)` goes through the enum metaclass's `__call__`, which searches the value-to-member mapping (and handles the alias/missing cases), an inherently heavier operation.

The guidance is precise and about *where*, not *whether*.
**Refer to members by name in your code** (`Color.RED`): it is direct, self-documenting, checked by tools (a typo `Color.Rde` is an `AttributeError` at the point of use, and a static checker flags it), and 7.9x faster.
**Reserve `Color(value)` for the boundary**, the one place where an *external* value enters your program, a byte off a socket, a code from a database row, a field from JSON, and convert it to a member *there*, once.
After that boundary, you hold a member and refer to it by name.
This is the same discipline as parsing at the edges: do the value-to-member lookup where the raw value arrives, not repeatedly in the hot code that follows, so the 7.9x is paid once per external value rather than once per use.

---

## 37.4 Edges and failure modes

**Members compare unequal to raw values (plain `Enum`).** §37.2.
`Color.RED == 1` is `False`. If you need value equality, use `IntEnum`/`StrEnum` or compare `.value`. Do not rely on a plain enum comparing to an int.

**Duplicate values are aliases and hide from iteration.** §37.1.
Two names with the same value give one member with two names; aliases do not appear in `list(Enum)`. Use `@enum.unique` to forbid this when each value must be distinct.

**Value lookup is ~8x slower than attribute access.** §37.3.
Use `Color.RED` in code; use `Color(value)` only at the external boundary.

**`Color(bad_value)` raises `ValueError`.**
Looking up a value that is not a member raises `ValueError`. At a boundary parsing untrusted input, catch it (or define `_missing_` to map unknown values to a default/`UNKNOWN` member) rather than letting it crash.

**`IntEnum` trades safety for interop.** §37.2.
An `IntEnum` compares equal to bare ints and to other `IntEnum`s of the same value, reintroducing the cross-type confusion plain `Enum` prevents. Use it only where numeric interop is required, not as a default.

**Members are not subclassable in the usual way, and an enum with members cannot be extended.**
You cannot add members by subclassing an enum that already has members (`TypeError`). Mixins and methods are fine, but the member set is fixed at definition. Design the full member set up front.

**Enum members can have methods and per-member behaviour.**
An enum body can define methods (called on members) and even per-member data via a custom `__init__`/tuple values. This is powerful but easy to overuse; keep enums close to "named constants" unless the behaviour genuinely belongs to the member.

**`auto()` values are integers starting at 1.**
Do not rely on `auto()`'s specific numbers if you serialize by value, an inserted member shifts later `auto()` values. Assign explicit values for anything persisted or sent over the wire.

---

## 37.5 Connections

**Backward.**
Members-as-singletons is Chapter 26 (the singleton pattern, `is` comparison). The enum class is built by a metaclass, `EnumType` (Chapter 31), which intercepts the member assignments. `Flag`'s bitwise operators and `IntEnum`'s arithmetic are the operator protocols of Chapter 20. Enums are the named-constant complement to the value types of Chapter 36 (dataclasses).

**Forward.**
`StrEnum` (3.11) and the enum improvements across 3.11/3.12 (`Flag` boundary handling, `_missing_`, `nonmember`) are release-timeline topics. Using enums in `match` statements (structural pattern matching) is a **Deep** pattern-matching topic. Serializing enums (by name for stability, by value for compactness) is a **Deep Q**/data topic.

**Across books.**
Enums are how **Book I** models closed sets of choices safely: order sides (`BUY`/`SELL`), order types (`LIMIT`/`MARKET`/`STOP`), time-in-force, connection states, each a named enum whose members are singletons, compare by identity, print readably in logs, and cannot be confused with a bare int or a sibling enum. The order-book system uses plain `Enum` for these domain choices (value-safe), `IntEnum`/`IntFlag` only at the wire boundary where the exchange protocol uses numeric codes, and does the `Enum(value)` lookup once when decoding a message (the §37.3 boundary rule), then refers to members by name throughout the matching logic.

---

## 37.6 Exercises

**1. Named singletons.** Reproduce §37.1: an enum with `auto()`, reached by name and value, iterated. Confirm members are singletons (`is`). Add a duplicate value and show it becomes an alias absent from iteration; then add `@enum.unique` and show it now errors.

**2. Safety versus interop.** Show `Color.RED == 1` is `False` for a plain enum and `Priority.HIGH == 2` is `True` for an `IntEnum`. Explain the trade-off and give one case for each.

**3. Flags.** Define a `Flag` of permissions. Combine, test membership, and mask with `&`. Then compare to a hand-rolled integer bitmask and explain what `Flag` adds.

**4. Measure the boundary.** Reproduce §37.3. Then write a decoder that converts a list of external integer codes to members with `Color(code)` once, and a hot loop that uses the members by name. Explain why the lookup belongs in the decoder, using the 7.9x.

**5. The design question.** Python made plain `Enum` members *not* equal to their values, requiring `IntEnum` to opt into value behaviour. Argue why value-safety is the better default (the bare-constant bugs it prevents), and when `IntEnum`'s interop is worth losing it. Would auto-value-equality have been friendlier or more dangerous? Defend your answer.

---

## 37.7 Summary and cross-references

- **`Enum`** turns `NAME = value` into **named singleton members** with `.name`/`.value`, reachable by name (`Color['RED']`) and value (`Color(1)`), iterable in definition order. Members are **singletons**, compare with `is`. **Duplicate values are aliases** (absent from iteration; `@enum.unique` forbids them). `auto()` numbers them.
- **Plain `Enum` is value-safe**: `Color.RED == 1` is `False`, preventing bare-constant confusion. **`IntEnum`/`StrEnum`** make members behave as their value for interop; **`Flag`/`IntFlag`** support bitwise option sets.
- **Measured:** value lookup `Color(1)` is **7.9x** slower than attribute `Color.RED` (name lookup 2.1x), because it goes through the enum metaclass's value search. Refer to members **by name** in code; reserve `Color(value)` for the **external boundary**, done once.
- **Edges:** `Color(bad)` raises `ValueError` (catch or `_missing_` at boundaries); enums with members cannot be extended; `auto()` numbers shift if you insert members (assign explicit values for anything serialized).

**Cross-references.** Singletons and `is` → Chapter 26. The enum metaclass → Chapter 31. Bitwise/arithmetic operators → Chapter 20. Value types (dataclasses) → Chapter 36. `StrEnum`, `match` with enums, serialization → Deep timeline / Deep Q.
