# Chapter 6: Low-Level File I/O and Exception Unwinding (Python 2.x to modern)

For fifteen years, experienced Python programmers followed a rule: keep `try` out of hot loops,
because setting up an exception handler costs something on every iteration. The rule was correct when
it was written, and it is wrong now, and the exact release where it flipped is Python 3.11. Here is
the measurement that settles it, from this chapter's benchmark:

| loop body | cost vs no `try` |
|---|---|
| no `try` | 1.00x |
| `try`, exception never raised | **1.01x** |
| `try`, exception raised and caught every iteration | **~6x** |

A `try` that never fires now costs one percent, within measurement noise of nothing. A `try` that
fires every time costs six times a plain lookup. The old advice conflated the two, and the truth
underneath it, that setting up a handler is free but *raising* is not, is the subject of half this
chapter.

This chapter closes the 2.x-origins material with the two runtime subsystems every program touches:
how bytes move between a process and the operating system, and how control unwinds when something
fails. Both were re-architected away from their 2.x forms. File I/O moved from thin C `stdio` wrappers
to the layered `io` stack (PEP 3116) that talks to the kernel directly. Exception handling moved from
a per-frame runtime block stack to a static exception table (Python 3.11) that makes a `try` cost
nothing when nothing is raised. We teach the modern mechanisms and use the 2.x originals only to show
what each redesign solved.

## Section index

- **6.1** The layered I/O architecture (PEP 3116)
- **6.2** Exception objects and the `BaseException` hierarchy
- **6.3** Zero-cost exceptions: the exception table (Python 3.11)
- **6.4** Exception chaining: `__context__`, `__cause__`, and `raise from`
- **6.5** Measurement: EAFP, LBYL, and the cost of raising
- **6.6** Edges and failure modes
- **6.7** Connections
- **6.8** Exercises
- **6.9** Summary and cross-references

Listings live under `code/ch006/` and are re-executed by `make verify` on both interpreters.

---

## 6.1 The layered I/O architecture (PEP 3116)

**Why this exists.** In Python 2, `open()` returned a `file` object that was a thin wrapper around a C
`stdio` `FILE *`. That inherited `stdio`'s buffering policy *and* its per-call internal mutex, locks
that are pure waste under the GIL, which already serializes interpreter execution. **PEP 3116**
replaced this with a composable three-layer stack (the `io` module) that calls the kernel's `read(2)`
and `write(2)` directly and lets each layer do one job:

```text
text    :  TextIOWrapper   - encode/decode str <-> bytes, universal newlines
             |
buffered:  BufferedReader / BufferedWriter - in-memory buffer, batches syscalls
             |
raw     :  FileIO          - a bare OS file descriptor; one syscall per read/write
```

The stack is observable: `open()` in text mode returns the top layer, and you can reach down through
it:

```python
# code/ch006/l01_io_stack.py
with open(path, "w", encoding="utf-8") as f:
    print("  text layer    :", type(f).__name__)
    print("  buffered layer:", type(f.buffer).__name__)
    print("  raw layer     :", type(f.buffer.raw).__name__)
```

Verified output (CPython 3.13.5):

```text
--- the three layers of a text-mode file ---
  text layer    : TextIOWrapper
  buffered layer: BufferedWriter
  raw layer     : FileIO
  default buffer: 8192 bytes
--- binary mode drops the text layer: you get bytes directly ---
  binary top layer: BufferedReader
  read returns    : bytes -> b'hello'
```

**What each layer buys you.** `FileIO` issues exactly one syscall per call, the unbuffered foundation.
`BufferedReader`/`BufferedWriter` hold an in-memory buffer (default 8192 bytes, `io.DEFAULT_BUFFER_SIZE`)
so many small reads and writes collapse into few syscalls; crossing the user/kernel boundary is the
dominant cost in I/O, and this layer is what makes line-by-line reading affordable. `TextIOWrapper`
adds the codec and newline translation. Opening in binary mode (`"rb"`/`"wb"`) omits the text layer
and hands you `bytes` directly, the right choice for protocols, images, and anything non-textual; the
full text/bytes model is Chapter 7.

**The senior-engineer contrast.** A C programmer chooses `fopen`/`fread` (buffered `stdio`) or
`open`/`read` (raw syscalls) explicitly and up front. Python's `io` stack gives you both in one
object: `f` is buffered text, `f.buffer` is buffered bytes, `f.buffer.raw` is the unbuffered
descriptor. You select the layer by reaching to it, and `open(..., buffering=0)` hands you a raw binary
stream when you want to manage buffering yourself.

---

## 6.2 Exception objects and the `BaseException` hierarchy

**Why this exists.** An exception carries its type, a value, and the traceback of where it propagated,
and that state must be *per thread*, since two threads can be handling different exceptions at once.
CPython stores the active exception on the `PyThreadState`.

Two facts frame the modern design. First, **the string-exception era is over.** You could once `raise
"some error"`, a bare string matched by identity, which made hierarchies impossible; it was removed,
and **every exception must now derive from `BaseException`**. That hierarchy is load-bearing:

```python
# code/ch006/l02_exception_state.py (excerpt)
for exc in (ValueError, KeyError, KeyboardInterrupt, SystemExit, GeneratorExit):
    print(issubclass(exc, Exception))
```

Verified output (CPython 3.13.5):

```text
--- the hierarchy: control-flow signals sit outside Exception ---
  ValueError         issubclass(_, Exception) = True
  KeyError           issubclass(_, Exception) = True
  KeyboardInterrupt  issubclass(_, Exception) = False
  SystemExit         issubclass(_, Exception) = False
  GeneratorExit      issubclass(_, Exception) = False
```

`KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` derive from `BaseException` *directly*, outside
the `Exception` subtree, so that `except Exception` deliberately does not catch them. This is what
keeps a program killable with Ctrl-C and lets `sys.exit()` and generator shutdown work through a
"catch all errors" handler. Catching `BaseException` or writing a bare `except:` defeats this and is
almost always a bug.

Second, **the thread-state exception state was consolidated in 3.11.** Python 2.x kept two separate
`(type, value, traceback)` triples on the thread state; modern CPython stores a single exception
*value* object, because type and traceback are derivable from it (`type(exc)`, `exc.__traceback__`).
`sys.exc_info()` reconstructs the familiar tuple from that one object, which the listing confirms:
`type(value).__traceback__ is exc_tb` is `True`, because the traceback in the tuple is literally the
one hanging off the value. Prefer `except SomeError as e` and use `e` directly; reserve
`sys.exc_info()` for generic logging or framework code that must work without naming the type.

---

## 6.3 Zero-cost exceptions: the exception table (Python 3.11)

**Why this exists, the big change.** Through Python 3.10, each frame carried a runtime **block stack**:
entering a `try` executed a `SETUP_FINALLY`/`SETUP_EXCEPT` opcode that *pushed* a block (handler
address, stack level) onto that stack, and leaving popped it. Every `try` therefore cost real work on
entry and exit *even when no exception was raised*, the common case and the reason for the old hot-loop
rule. Python 3.11 removed the block stack and replaced it with a static, per-code-object **exception
table**: a side table mapping ranges of bytecode offsets to their handler. On the non-exception path a
`try` now executes *nothing extra*; the cost is paid only when an exception is actually raised and the
interpreter consults the table.

The structural facts are directly checkable:

```python
# code/ch006/l03_exception_table.py
def guarded(x):
    try:
        return 10 / x
    except ZeroDivisionError:
        return -1
```

Verified output (CPython 3.13.5):

```text
--- structural facts about the compiled try/except ---
  has any SETUP_* block-stack opcode: False
  has an exception table            : True
  handler opcodes present in order:
    PUSH_EXC_INFO    present: True
    CHECK_EXC_MATCH  present: True
    POP_EXCEPT       present: True
    RERAISE          present: True
```

The listing also confirms the two execution paths: `guarded(2)` returns `5.0` on the success path
where the table is never consulted, and `guarded(0)` returns `-1` on the exception path where the
table lookup finds the handler.

No `SETUP_*` opcode exists; an exception table does. On the success path (`guarded(2)`), the `try`
body carries no setup overhead and the table is never touched. On the exception path (`guarded(0)`),
the interpreter looks up the current bytecode offset in the table, finds the handler, pushes the
exception info (`PUSH_EXC_INFO`), tests it against the caught type (`CHECK_EXC_MATCH`), runs the
handler, and clears the exception state (`POP_EXCEPT`). If no handler in this frame matches, `RERAISE`
propagates to the caller, whose frame is searched the same way, building the traceback frame by frame
as it unwinds. The unwinding *semantics* are exactly what the old 2.x block-stack diagrams described;
only the *mechanism*, table lookup instead of a runtime stack, changed, and with it the cost model
that §6.5 measures.

---

## 6.4 Exception chaining: `__context__`, `__cause__`, and `raise from`

**Why this exists (PEP 3134).** When handling one error raises another, both are relevant: the new one
for the abstraction you present, the original for the root cause. Python links them automatically.
Implicit chaining sets the new exception's `__context__` to the one being handled. Explicit chaining,
`raise New() from original`, sets `__cause__` and marks the link deliberate. Suppression, `raise New()
from None`, clears the chain when the original is noise.

```python
# code/ch006/l04_chaining.py (excerpt)
def chained():
    try:
        1 / 0
    except ZeroDivisionError as e:
        raise RuntimeError("wrapped") from e
```

Verified output (CPython 3.13.5):

```text
--- raise ... from ... sets __cause__; __context__ is kept too ---
  __cause__  : ZeroDivisionError
  __context__: ZeroDivisionError
--- raise ... from None clears the chain when the original is noise ---
  __cause__  : None
  __suppress_context__: True
```

`raise ... from e` sets both `__cause__` (the deliberate link, printed as "the direct cause") and
`__context__` (the ambient one). `raise ... from None` leaves `__cause__` as `None` and sets
`__suppress_context__` so the traceback omits the original entirely. This is the right way to wrap a
low-level error in a domain error without losing the diagnostic trail: wrap a `KeyError` from a config
lookup in a `ConfigError` with `raise ConfigError(...) from e`, and the traceback shows both layers.
The multi-error generalization, exception groups and `except*` (PEP 654), belongs to concurrent code
and is Chapter 19 of the timeline (the 3.11 volume).

---

## 6.5 Measurement: EAFP, LBYL, and the cost of raising

Python idiom favors **EAFP** ("easier to ask forgiveness than permission"), try the operation and
handle the exception, over **LBYL** ("look before you leap") with pre-checks. The chapter opened with
the claim that this choice is now a performance question with a clean answer. Here is the full
measurement.

**Methodology.** `code/ch006/bench_try_cost.py`, through `_harness/bench.py`. 1000 dictionary lookups
per timed loop, four ways: a bare lookup, the same lookup inside a `try` that never raises, an EAFP
lookup of a missing key (raises and catches every iteration), and an LBYL lookup of the same missing
key with an `in` pre-check. `min` is the headline; ratios within this one interpreter. CPython 3.13.5,
`-O2`, Apple M3 Pro, macOS 27.0, arm64. Ratios reproduced across runs.

| case | ratio |
|---|---|
| no `try` (baseline) | 1.00x |
| `try`, exception never raised | **1.01x** |
| LBYL, miss every time | 1.00x (vs baseline) |
| EAFP, miss every time | **5.4x** (vs LBYL) |

**Two facts, and they point in opposite directions.** First, a `try` that never fires costs 1.01x a
bare lookup: one percent, inside the noise. That is what "zero-cost exceptions" means, and it is why
the old hot-loop rule is obsolete for the *setup* cost. Wrapping a rarely-failing operation in `try`
is free.

Second, an actually-raised-and-caught exception costs about **5.4x** the equivalent pre-check. Raising
builds an exception object, populates its traceback, and unwinds; catching tests and clears it. When
the miss is the *common* case, EAFP pays that 5.4x on most iterations and the cheap LBYL pre-check wins
by a wide margin.

So the decision rule is quantitative, not stylistic: **choose EAFP when the exceptional case is rare
(its setup is free and its raise is paid seldom), and LBYL when the exceptional case is common (the
pre-check is far cheaper than repeated raising).** The config-default lookup in the listing is EAFP
because a missing key is the exception, not the rule; a parser classifying mostly-invalid tokens would
be LBYL. The old "no `try` in hot loops" advice was a lossy compression of exactly this, correct only
because before 3.11 the setup cost was real too.

---

## 6.6 Edges and failure modes

**Bare `except:` or `except BaseException`.** §6.2. Catches `KeyboardInterrupt` and `SystemExit`,
making a program unkillable and masking shutdown. Catch `Exception` at most, and prefer the narrowest
type that fits.

**Swallowing exceptions.** `except Exception: pass` destroys diagnostics. At minimum log; better,
re-raise or wrap with `raise ... from e` (§6.4).

**EAFP where misses are common.** §6.5. A raised exception is ~5.4x a pre-check. In a loop that mostly
misses, use LBYL.

**`open()` without `with`.** Leaks the descriptor until the GC happens to finalize it, which is never
deterministic (Chapter 3) and under load hits the process's open-file limit. Always `with open(...) as
f:` (Chapter 5).

**Forgetting durability.** §6.1. Buffering means a "written" value is in user space until flushed; for
crash-durable writes, `f.flush()` then `os.fsync(f.fileno())`. A returned `write()` is not a durable
write.

**Reading a huge file with `.read()`.** Pulls the whole file into one `str`/`bytes`. Iterate the file
object (line-buffered) or read in chunks sized to `io.DEFAULT_BUFFER_SIZE` or a multiple.

**Assuming the traceback line count is stable.** The exception *table* is an implementation detail; its
textual disassembly format has changed across versions, which is why Listing 6.3 tests structural
facts (no `SETUP_*`, table present, specific handler opcodes) rather than a raw `dis` dump.

---

## 6.7 Connections

**Backward.** Deterministic resource cleanup with `with`, which every file should use, is Chapter 5,
and the exception table this chapter details is what implements `with`'s guaranteed `__exit__`.
Reference-count and GC finalization of file objects, and why you cannot trust them for cleanup, are
Chapters 19 and 3.

**Forward.** The full text/bytes/Unicode and codec model that `TextIOWrapper` applies is Chapter 7,
the next chapter and the start of the Python 3 era. Exception groups and `except*`, the multi-error
generalization of §6.4, are the 3.11 volume. The "Faster CPython" work that produced the exception
table, and the specializing interpreter alongside it, is Chapter 17. The complete `io` and OS-interface
reference is **Deep R**, and benchmarking discipline is **Deep K**.

**Across books.** The layered I/O stack is where Python meets the operating system, and it is also
where the zero-copy path to **Book I** begins: a `BufferedReader` over a memory-mapped file, or a raw
`FileIO` whose descriptor is handed to a C++ routine, avoids copying bytes through the Python heap
entirely. The buffer protocol that makes this possible, and `memoryview` over a file mapping, is
**Deep A** and the seam is **Deep M**. The order-book example ingests its market-data feed exactly this
way, raw bytes read once and viewed, never copied per record.

---

## 6.8 Exercises

**1. Find the layer.** Open the same file three ways: text mode, binary mode, and `buffering=0`. For
each, print the type of the top object and whether `.buffer` and `.buffer.raw` exist. Explain why
`buffering=0` is only legal in binary mode, in terms of what `TextIOWrapper` needs from the layer below
it.

**2. Prove the durability gap.** Write a value to a file, and without closing or flushing, read the
underlying file (via a second descriptor or `os.read`) to show the bytes are not yet on disk. Then
flush and show they are. Explain where the bytes lived in between, and what `os.fsync` adds on top of
`flush` that matters for a crash.

**3. Catch the uncatchable, then stop.** Write a loop that a bare `except:` makes impossible to
interrupt with Ctrl-C, observe it, then fix it to `except Exception` and confirm Ctrl-C works. Explain
using §6.2 exactly which class in the hierarchy the fix stops catching, and why that class sits where
it does.

**4. Find your crossover.** Using the §6.5 benchmark, vary the *miss rate* of the lookup (say, a
dictionary where a given fraction of keys are present) and find the miss rate at which EAFP and LBYL
cost the same. Report to the standard of §6.5. Then state, for a real cache with a 95% hit rate, which
idiom you would choose and why.

**5. The design question.** Python made a `try` free on the success path by moving handler information
out of the runtime into a static table, at the cost that raising is now a table lookup plus traceback
construction. C++ made the same trade decades earlier (zero-cost exceptions via unwind tables), while
Go rejected it, using explicit error-return values and no unwinding at all. Argue which model fits
Python best given its EAFP idiom (§6.5), and what Go's model would cost a language whose standard way to
report a missing key is to raise.

---

## 6.9 Summary and cross-references

- File I/O is a **three-layer stack** (PEP 3116): `FileIO` (raw syscalls), `BufferedReader`/`Writer`
  (batch syscalls, 8192-byte default buffer), `TextIOWrapper` (codec and newlines). Reach to
  `f.buffer`/`f.buffer.raw` to pick a layer; binary mode drops the text layer.
- Every exception derives from **`BaseException`**; `KeyboardInterrupt`, `SystemExit`, and
  `GeneratorExit` sit *outside* `Exception`, so `except Exception` spares them. The thread-state
  exception triples collapsed to a single value object in 3.11; `sys.exc_info()` reconstructs the
  tuple.
- Python 3.11 replaced the runtime **block stack** with a static **exception table**, making `try`
  cost nothing on the success path; unwinding is now a table lookup that builds the traceback frame by
  frame.
- **Chaining** links errors: implicit `__context__`, explicit `__cause__` via `raise from`, suppressed
  via `from None`.
- **Measured:** a `try` that never raises costs **1.01x** a bare lookup; a raised-and-caught exception
  costs **~5.4x** a pre-check. EAFP is free when misses are rare and expensive when they are common;
  choose by miss rate, not by style.

**Cross-references.** Deterministic cleanup with `with` → Chapter 5. GC finalization of files →
Chapters 3 and 19. The text/bytes/codec model → Chapter 7. Exception groups and `except*` → the 3.11
volume. The exception table and Faster CPython → Chapter 17. The full `io`/OS reference → Deep R.
Benchmarking → Deep K. The zero-copy path to C/C++ → Deep A and Deep M.

---

*The 2.x-origins material is complete. The next chapter opens the Python 3 era with the Unicode
paradigm shift.*
