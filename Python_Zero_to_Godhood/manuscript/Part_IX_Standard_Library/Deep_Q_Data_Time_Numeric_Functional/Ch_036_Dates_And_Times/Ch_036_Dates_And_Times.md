# Chapter 36: Dates and Times

A service stores event timestamps as `datetime.now()` and, months later, a report that joins events
across two data centers is subtly wrong: durations are off by hours, some events appear to happen before
the events that caused them. Nothing threw. The cause is the **naive datetime**, a `datetime` with no
`tzinfo`, which Python treats as "some local time, unspecified." `datetime.now()` returns one; so does
parsing a timestamp that omits an offset. A naive datetime is not wrong in isolation, it is wrong the
moment two zones or a daylight-saving boundary meet, because there is no information in it to reconcile
them. The fix is the **aware datetime**, one that carries a `tzinfo`, and the discipline is: store and
compute in UTC-aware datetimes, convert to local only at the edges.

That correctness rule is the heart of this chapter, but there is a performance finding paired with it that
changes how you parse. The reflex for reading a timestamp string is `datetime.strptime(s, fmt)`, and for
ISO-8601 timestamps (the format logs, JSON, and databases actually use) that reflex is **53 times slower**
than `datetime.fromisoformat(s)`, a dedicated C parser that, since Python 3.11, also accepts the `Z`
suffix and a space separator. This chapter, part of **Deep Q**, is the working reference for the aware/naive
distinction and for parsing timestamps fast.

## Section index

- **36.1** Naive vs aware: the `tzinfo` is the whole story
- **36.2** Parsing: `fromisoformat` vs `strptime`
- **36.3** Measurement: the cost of the wrong parser
- **36.4** Edges and failure modes
- **36.5** Connections
- **36.6** Exercises
- **36.7** Summary and cross-references

Listings live under `code/ch036/` and are re-executed by `make verify` on both interpreters.

---

## 36.1 Naive vs aware: the `tzinfo` is the whole story

```python
# code/ch036/l01_datetime.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- naive vs aware: the tzinfo is the whole story ---
  naive.tzinfo        : None
  aware.tzinfo        : UTC
  naive is aware?     : False
  aware is aware?     : True
--- aware arithmetic: convert between zones correctly ---
  12:00 UTC in IST    : 17:30 +0530
  same instant?       : True
--- durations are timedeltas ---
  +36h                : 2026-07-26T00:00:00+00:00
  span in hours       : 36.0
--- fromisoformat: fast, and since 3.11 accepts Z and space ---
  offset form         : 2026-07-24T12:00:00+00:00
  Z suffix            : 2026-07-24T12:00:00+00:00
  space separator     : 2026-07-24T12:00:00
```

A `datetime` is **naive** if `tzinfo is None` and **aware** if it carries a `tzinfo`. That single
attribute decides whether the value denotes a specific instant on the global timeline (aware) or an
ambiguous wall-clock reading (naive). The aware datetime converts correctly: `astimezone(ist)` renders the
same instant as `17:30 +0530`, and the equality `aware == in_ist` is `True` because they *are* the same
moment expressed in two zones. A naive datetime cannot do this, it has no offset to convert from, so mixing
naive and aware datetimes raises `TypeError` on subtraction (a deliberate guard) and, worse, arithmetic on
two naive datetimes from different real zones silently produces a meaningless result.

Durations are `timedelta` objects: `aware + timedelta(hours=36)` moves the instant forward, and
`later - aware` yields a `timedelta` whose `total_seconds()` is exact. Note the discipline the listing
models: construct aware (pass `tzinfo=timezone.utc`), do arithmetic in UTC, and `astimezone` to a local
zone only for display. For named zones with real DST rules, use `zoneinfo.ZoneInfo("Asia/Kolkata")` (the
stdlib IANA database, 3.9+) rather than a fixed `timezone(timedelta(...))` offset, because a fixed offset
does not know about daylight saving.

---

## 36.2 Parsing: `fromisoformat` vs `strptime`

The last block shows `fromisoformat` parsing three shapes of the same timestamp: the explicit `+00:00`
offset, the `Z` (Zulu/UTC) suffix, and a space instead of `T` between date and time. All three work
because, since Python 3.11, `fromisoformat` accepts the broader ISO-8601 grammar rather than only the exact
string `isoformat()` produces. Before 3.11 it was strict (offset-only, `T`-only), which is why the folklore
"use `strptime`, `fromisoformat` is too picky" persisted; on 3.11+ that folklore is stale for ISO input.

`strptime(s, fmt)` is the general parser: it interprets a `strftime` format string, so it handles *any*
layout (`"%d/%m/%Y %I:%M %p"` for `24/07/2026 12:34 PM`). That generality is exactly its cost, it parses
the format specification and then the value on every call. `fromisoformat` is a single-purpose C parser for
one grammar, ISO-8601, and pays none of that per-call interpretation. §36.3 measures the gap. The rule that
falls out: use `fromisoformat` for ISO timestamps (which is what machine-generated data almost always is),
and reserve `strptime` for genuinely non-ISO human formats.

---

## 36.3 Measurement: the cost of the wrong parser

**Methodology.** `code/ch036/bench_parse.py`. Parsing the ISO timestamp
`"2026-07-24T12:34:56.789012+00:00"` with `fromisoformat` versus `strptime` and the equivalent format
string. `min` per call; ratios within one interpreter. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| parser | min per call | ratio |
|---|---|---|
| `datetime.fromisoformat` | **76 ns** | 1.00x |
| `datetime.strptime` | **4074 ns** | **53.3x** |

`fromisoformat` parses the timestamp in **76 ns**; `strptime` takes **4074 ns**, **53x** longer, for the
identical result. The difference is per-call format interpretation: `strptime` re-parses the `"%Y-%m-%d..."`
specification every call before it even looks at the value, while `fromisoformat` is a fixed C parser for
the ISO grammar. At scale this is not academic: a pipeline ingesting a million log lines spends **4 ms**
parsing with `fromisoformat` and **~200 ms** with `strptime`, per million, and timestamp parsing is often
the hottest line in a log-ingestion loop.

The lesson generalizes the Deep Q theme: match the tool to the shape of the data. ISO-8601 is a fixed
grammar with a dedicated fast parser; using the general `strptime` for it is paying for flexibility you do
not use. Reach for `strptime` only when the input is genuinely not ISO, and then accept its cost as the
price of parsing an arbitrary layout.

---

## 36.4 Edges and failure modes

**Naive datetime from `now()` / `utcnow()`.** §36.1. `datetime.now()` returns a *naive* local datetime,
and `datetime.utcnow()` (deprecated in 3.12) returns a naive datetime whose value is UTC but whose
`tzinfo` is `None`, a trap. Use `datetime.now(timezone.utc)` for an aware UTC datetime.

**Mixing naive and aware.** Subtracting a naive from an aware datetime raises `TypeError`. This is a
feature, it refuses a meaningless operation, but it surfaces as a crash in code that assumed all its
datetimes were the same kind. Normalize to aware at every boundary.

**Fixed offset vs named zone.** §36.1. `timezone(timedelta(hours=-5))` is a *fixed* offset that does not
observe DST. For a real location, use `zoneinfo.ZoneInfo("America/New_York")`, which applies the correct
offset for each date. A fixed offset silently gives wrong wall-clock times across a DST boundary.

**`fromisoformat` before 3.11.** On 3.10 and earlier, `fromisoformat` rejects the `Z` suffix and space
separator and parses only what `isoformat()` emits. §36.2's permissiveness is a 3.11 feature; do not rely
on it if you must support older interpreters.

**`strptime` and `%z` without an offset.** Parsing a string that lacks an offset with a `%z` in the format
raises `ValueError`; parsing one that *has* an offset without `%z` produces a naive datetime that drops the
zone. The format must match the data's zone presence exactly.

**DST-ambiguous and non-existent local times.** During a fall-back hour a local time occurs twice, and
during spring-forward an hour does not exist. `zoneinfo` resolves these via the `fold` attribute; naive
local arithmetic across these boundaries is simply wrong. Compute in UTC to avoid the whole class.

---

## 36.5 Connections

**Backward.** The immutability of `datetime`/`date`/`timedelta` (every operation returns a new object) is
the value-semantics theme of Chapter 4. The number types the `timedelta` arithmetic and `total_seconds()`
rest on are Chapter 35. The `zoneinfo` module reading the IANA database is a data-file lookup like the
`collections`-backed lookups of Chapter 32.

**Forward.** The C parser behind `fromisoformat` and the object layout of `datetime` are **Deep A**.
Serializing datetimes across a boundary (ISO strings in JSON, epoch seconds in a database) is **Deep R**
(persistence). Locale-aware and calendar arithmetic beyond the proleptic Gregorian calendar is a
specialized topic flagged in **Deep S**.

**Across books.** UTC-aware timestamps are the contract Book II hands to **Book III**. An event stream
feeding a **Book III** pipeline carries aware UTC datetimes end to end, parsed with `fromisoformat` at
ingest for throughput, so that windowing, ordering, and deduplication are correct regardless of the
producers' local zones. The naive-datetime bug is precisely the kind of silent cross-boundary corruption
**Deep U** exists to prevent at the seam.

---

## 36.6 Exercises

**1. Expose the naive bug.** Construct two naive datetimes that represent the same instant in different
real zones and show that subtracting them gives a wrong duration. Then make both aware and show the
subtraction is correct. Explain what information the `tzinfo` supplied.

**2. Convert correctly.** Take an aware UTC datetime and render it in three zones with `astimezone`,
confirming the equality holds (same instant). Then do it with `zoneinfo.ZoneInfo` across a DST boundary and
show the offset changes with the date, where a fixed `timezone(timedelta(...))` would not.

**3. Measure the parser gap.** Reproduce §36.3's benchmark and confirm `fromisoformat` is far faster than
`strptime` for ISO input. Then time `strptime` on a genuinely non-ISO format and explain why `strptime` is
unavoidable there.

**4. Parse the ISO variants.** Feed `fromisoformat` the offset form, the `Z` suffix, and the space
separator (§36.1) and confirm all parse on 3.11+. Explain what changed in 3.11 and why the old "use
strptime" advice predates it.

**5. The design question.** Python ships both a fast single-grammar parser (`fromisoformat`) and a slow
general one (`strptime`), and both a naive and an aware datetime. Argue why each pair exists rather than a
single unified type/parser. Your answer must address the speed/generality trade-off the §36.3 benchmark
measures and why forcing every datetime to be aware would break as much code as it fixed.

---

## 36.7 Summary and cross-references

- A `datetime` is **naive** (`tzinfo is None`, an ambiguous wall-clock reading) or **aware** (carries a
  `tzinfo`, a specific instant). Store and compute in UTC-aware datetimes; convert to local only at the
  edges. `datetime.now()` is naive, `datetime.now(timezone.utc)` is aware.
- Use **`zoneinfo.ZoneInfo`** for real named zones (it applies DST), not a fixed `timezone(timedelta(...))`
  offset.
- **Measured:** parsing an ISO-8601 timestamp with **`fromisoformat` is 53x faster** than `strptime`
  (76 ns vs 4074 ns), because `strptime` re-interprets a format string every call. Since 3.11
  `fromisoformat` also accepts the `Z` suffix and a space separator. Use it for ISO input; reserve
  `strptime` for non-ISO formats.

**Cross-references.** Value semantics → Chapter 4. Number types behind `timedelta` → Chapter 35.
`collections` lookups → Chapter 32. The C parser and datetime layout → Deep A. Serialization → Deep R. The
timestamp seam → Deep U.
