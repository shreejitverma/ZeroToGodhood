# Chapter 19: Exception Groups and `except*` (Python 3.11)

Run ten downloads concurrently. Three of them fail: one times out, one gets a connection reset, one
gets a 404. Before Python 3.11, your code could learn about exactly one of those failures. Whichever
exception happened to propagate first won; the other two vanished, and the caller got a single
`TimeoutError` with no hint that two other things had also gone wrong. In a concurrent program, an
exception is not a single event with a single cause. It is a *set* of events, and the language had no
type for a set.

Python 3.11 added that type. **PEP 654** introduced `ExceptionGroup`, a container that carries many
exceptions at once, and `except*`, a new syntax that catches the subgroup matching a given type while
letting the rest propagate. Together they are the exception model for structured concurrency, and they
are why `asyncio.TaskGroup` (arriving in the same release) can report that three tasks failed instead
of one. This chapter is a companion to the specializing-interpreter chapter: both are 3.11, but where
that one was about speed, this one is about correctly reporting failure when more than one thing breaks
at the same time.

## Section index

- **19.1** The problem: one slot for many failures
- **19.2** `ExceptionGroup`: a first-class collection of exceptions
- **19.3** `except*`: matching a subgroup
- **19.4** `asyncio.TaskGroup` and structured concurrency
- **19.5** Edges and failure modes
- **19.6** Connections
- **19.7** Exercises
- **19.8** Summary and cross-references

Listings live under `code/ch021/` and are re-executed by `make verify` on both interpreters.

---

## 19.1 The problem: one slot for many failures

The exception machinery of Chapter 6 propagates *one* exception up the stack: a frame either handles
it or re-raises it, and there is exactly one active exception on the thread state at a time. That model
is correct for sequential code, where one thing happens at a time and one thing fails at a time.

It breaks the moment failures become concurrent. When ten tasks run at once and three raise, there is
no single exception to propagate, and the pre-3.11 workarounds were all lossy or awkward: catch and log
each task's exception separately (losing the ability to handle them at the call site),
`gather(return_exceptions=True)` (returning a flat list of results-or-exceptions that you must inspect
by hand), or simply let the first failure win and discard the others. None of them let the caller write
`except SomeError:` and handle the relevant failures while the rest propagate. That is the gap PEP 654
fills.

---

## 19.2 `ExceptionGroup`: a first-class collection of exceptions

An `ExceptionGroup` is an ordinary exception whose payload is a *list of other exceptions*. It has a
message and an `exceptions` tuple, and it can be raised, caught, and inspected like any exception:

```python
# code/ch021/l01_exception_groups.py
eg = ExceptionGroup(
    "multiple failures",
    [ValueError("bad value"), TypeError("bad type"), ValueError("another")],
)
```

Verified output (CPython 3.13.5):

```text
--- the group object ---
  type    : ExceptionGroup
  message : multiple failures
  count   : 3
```

The same listing also runs `eg.split(ValueError)`, which prints `matched: 2 | rest: 1`.
`split` is the programmatic heart of the feature: it partitions the group into the
subgroup whose leaves are `ValueError` (here two) and the remainder (here one), preserving the group
structure of each half. `except*` is sugar over `split`.

There is a deliberate hierarchy. `ExceptionGroup` holds only ordinary `Exception`s; its parent
`BaseExceptionGroup` can also hold `BaseException`s like `KeyboardInterrupt` and `SystemExit`. This
mirrors the split from Chapter 6: because a plain `ExceptionGroup` cannot contain a `KeyboardInterrupt`,
catching an `ExceptionGroup` never accidentally swallows a shutdown signal buried among the failures.
The `BaseException`-versus-`Exception` discipline of the flat model carries over to the grouped one.

---

## 19.3 `except*`: matching a subgroup

`except*` is a new clause, distinct from `except`, that matches the *subgroup* of the raised group whose
leaves are of the given type, runs its handler with that subgroup, and lets the non-matching remainder
continue propagating. Multiple `except*` clauses can all run for a single raised group, one per matched
type:

```python
# code/ch021/l01_exception_groups.py (excerpt)
def process():
    raise ExceptionGroup(
        "batch", [ValueError("v1"), TypeError("t1"), ValueError("v2"), KeyError("k1")]
    )
```

Verified output (CPython 3.13.5):

```text
--- except* matches the subgroup of each type; the rest propagate ---
  except* ValueError -> ['v1', 'v2']
  except* TypeError  -> ['t1']
  except* KeyError   -> ["'k1'"]
```

All three handlers ran, each receiving the subgroup of its type: the two `ValueError`s together, the
one `TypeError`, the one `KeyError`. This is the crucial difference from `except`: a plain `except
ValueError:` would catch the whole thing or nothing and could handle only one type; `except*` handles
each category of a multi-failure event independently, in one `try`. You cannot mix `except` and
`except*` in the same `try` (the compiler rejects it), because they have incompatible matching
semantics: one matches the whole exception, the other matches a subgroup.

---

## 19.4 `asyncio.TaskGroup` and structured concurrency

Exception groups exist because of concurrency, and `asyncio.TaskGroup` (3.11) is the motivating
consumer. A `TaskGroup` runs tasks concurrently under an `async with` block; if any task fails, it
cancels the siblings and, when the block exits, raises an `ExceptionGroup` of everything that failed:

```python
# code/ch021/l02_taskgroup.py
async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(failing("db", ConnectionError))
            tg.create_task(failing("cache", TimeoutError))
            tg.create_task(failing("api", ValueError))
    except* ConnectionError as e:
        print("  infra failures :", sorted(str(x) for x in e.exceptions))
    except* (TimeoutError, ValueError) as e:
        print("  other failures :", sorted(str(x) for x in e.exceptions))
```

Verified output (CPython 3.13.5):

```text
--- three tasks fail concurrently; all three are preserved ---
  infra failures : ['db']
  other failures : ['api', 'cache']
```

All three failures survived, routed into two handlers by category. This is **structured concurrency**:
the `TaskGroup` block is a scope, all tasks created in it are guaranteed to complete or be cancelled
before the block exits, and their failures are collected into one typed, routable group rather than
lost. Compare the pre-3.11 alternative, `gather(return_exceptions=True)`, which the listing also runs:
it collects the failures too, but as a flat list you inspect by hand, it does not cancel siblings when
one fails, and it has no structured propagation. `TaskGroup` is the structured-concurrency primitive;
the exception group is how it reports failure. The full structured-concurrency treatment is **Deep H**.

---

## 19.5 Edges and failure modes

**Mixing `except` and `except*`.** The compiler forbids both in one `try`. Choose one matching model per
`try` block; `except*` if you expect a group, `except` if you expect a flat exception.

**A single exception is not a group.** A function that raises a plain `ValueError` does not raise an
`ExceptionGroup`; `except* ValueError:` will *not* catch a bare `ValueError`. `except*` matches groups.
If a callee may raise either, handle both, or wrap the bare one.

**Swallowing a `BaseException` in a group.** Use `except*` narrowly. `except* Exception:` on a
`BaseExceptionGroup` leaves the `BaseException` leaves (like `KeyboardInterrupt`) to propagate, which is
correct, but do not reach for `BaseExceptionGroup` handling casually.

**Nested groups.** `split` and `except*` preserve nesting: a group of groups stays structured. Do not
assume `e.exceptions` is flat; a leaf may itself be a group. Use `e.exceptions` recursively or the
group's traversal helpers when you need every leaf.

**Losing failures the old way.** §19.4. `gather` without `return_exceptions=True` still discards all but
the first failure. For multi-task failure reporting, use `TaskGroup`.

---

## 19.6 Connections

**Backward.** The flat exception model, the `BaseException`-versus-`Exception` hierarchy, and the
exception table that propagates a single exception are Chapter 6; exception groups extend that model to
sets without abandoning its `try`/`finally` guarantees. The `asyncio` event loop and Tasks that
`TaskGroup` builds on are Chapters 10 and 11.

**Forward.** Structured concurrency, `TaskGroup` cancellation semantics, and timeouts in depth are
**Deep H**. The 3.11 speed work that shipped alongside this is Chapter 17.

**Across books.** Exception groups are how Book II reports concurrent failure across both seams. A
retrieval service in **Book III** that fans out to many model or index calls under a `TaskGroup`
surfaces all the failures of a batch as one group, so the caller can retry the timeouts and log the
permanent errors in one `try`. A parallel dispatch to several **Book I** C++ kernels reports its
failures the same way. **Deep H** and **Deep U** own those seams; the exception group is the shape a
multi-failure result takes as it crosses them.

---

## 19.7 Exercises

**1. Route a mixed batch.** Build an `ExceptionGroup` containing three different exception types and
write a `try`/`except*` that handles two of them and lets the third propagate. Confirm the third
escapes, and explain what `except*` did with the group in terms of `split`.

**2. Catch nothing with `except*`.** Show that `except* ValueError:` does not catch a *bare*
`ValueError` (only a group containing one). Then write the wrapper that makes a function's bare
exceptions catchable by `except*`, and explain when you would want that.

**3. Reproduce the loss.** Write two concurrent failing tasks with plain `asyncio.gather` (no
`return_exceptions`) and show only one failure propagates. Convert to a `TaskGroup` and show both
survive. Explain the two behavioral differences beyond the exception type (cancellation, structure).

**4. Preserve the base signal.** Construct a `BaseExceptionGroup` containing a `KeyboardInterrupt` and a
`ValueError`, and show that `except* ValueError:` handles the `ValueError` while the `KeyboardInterrupt`
still propagates. Explain why this matters for a long-running server.

**5. The design question.** PEP 654 added a new syntax (`except*`) rather than making the existing
`except` handle groups. Argue why a separate syntax was necessary, in terms of what would break if
`except ValueError:` silently started matching subgroups of existing code that catches a group as a
whole. What backward-compatibility problem does the separate `*` solve?

---

## 19.8 Summary and cross-references

- Before 3.11, an exception was a single event; concurrent code that failed in several ways could
  propagate only one failure and lost the rest.
- **`ExceptionGroup`** (PEP 654) is a first-class collection of exceptions with a `message` and an
  `exceptions` tuple; `split(type)` partitions it into the matching subgroup and the remainder.
  `ExceptionGroup` holds only `Exception`s; `BaseExceptionGroup` can hold `BaseException`s, preserving
  Chapter 6's shutdown-signal discipline.
- **`except*`** matches the subgroup of a given type and lets the rest propagate; multiple `except*`
  clauses can each run for one raised group. `except` and `except*` cannot mix in one `try`, and
  `except*` does not catch a bare (non-group) exception.
- **`asyncio.TaskGroup`** is the motivating consumer: structured concurrency where sibling tasks are
  cancelled on first failure and all failures are raised as one typed group, unlike lossy `gather`.

**Cross-references.** The flat exception model and the exception table → Chapter 6. `asyncio`, the event
loop, and Tasks → Chapters 10 and 11. Structured concurrency and `TaskGroup` in depth → Deep H. The 3.11
speed work → Chapter 17. The concurrent-failure seams to Books I and III → Deep H and Deep U.
