# Chapter 53: Context Variables

An async web service stores the current request's ID in a module global so every function can log it, and in
production the logs are scrambled: request A's log lines carry request B's ID. Nothing is racing in the
threading sense, there is one thread, but async tasks *interleave* at every `await`, and the global written by
one task is overwritten by another before the first resumes. Measured concretely: five concurrent tasks that
each store their ID in a global and read it back after an `await` all read `[4, 4, 4, 4, 4]`, the last
writer's value, instead of their own `[0, 1, 2, 3, 4]`. The same five tasks using a `contextvars.ContextVar`
each read their own ID correctly. And the ContextVar is not slower: `get()` is **~7 ns**, as fast as a dict
lookup. Correct per-request state in concurrent code, at essentially no cost, and a module global is simply
the wrong tool.

That is the case for `contextvars`, and it is a correctness case first. This chapter continues **Deep S** with
context variables: state that is local to a logical context (an async Task, a thread) and propagates correctly
through concurrency where globals corrupt and `threading.local` does not reach. It connects directly to the
`asyncio` model of Chapters 10-11, whose interleaving is exactly what breaks the global.

## Section index

- **53.1** The problem globals cannot solve
- **53.2** Why `threading.local` is not enough for async
- **53.3** Measurement: correctness at no speed cost
- **53.4** Edges and failure modes
- **53.5** Connections
- **53.6** Exercises
- **53.7** Summary and cross-references

Listings live under `code/ch053/` and are re-executed by `make verify` on both interpreters.

---

## 53.1 The problem globals cannot solve

```python
# code/ch053/l01_contextvars.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- ContextVar: each task keeps its own value across the await ---
  results             : [0, 1, 2, 3, 4]
  each task saw its own rid : True
--- module global: clobbered by interleaving (all see the last write) ---
  results             : [4, 4, 4, 4, 4]
  corrupted?          : True (all tasks saw the same rid)
--- the rule ---
  request-scoped state in async code -> ContextVar, not a global or
  threading.local (async tasks share a thread, so they share both)
```

The two handlers are identical except for where they keep the request ID. With a **module global**, each of
the five tasks writes its ID, then hits `await asyncio.sleep(...)`, which yields control so the other tasks
run and overwrite the global; when the task resumes and reads the global, it sees whatever ran *last*, so all
five read `4`. The state was shared, and concurrency shared it wrongly.

With a **`ContextVar`**, `request_id.set(rid)` writes into *this task's context*, and `request_id.get()` after
the `await` reads *this task's* value, `[0, 1, 2, 3, 4]`, each correct. A `ContextVar` is not one slot shared
by everyone; it is a slot per logical context, and `asyncio` gives each Task its own context (copied when the
Task is created). So the value set inside one Task is invisible to another, which is exactly what request-
scoped state requires. This output is deterministic (`gather` preserves order; the sleeps are equal), which is
why the corruption is reproducible rather than a flaky heisenbug, the worst kind of production bug made
visible.

---

## 53.2 Why `threading.local` is not enough for async

The instinct for "per-something state" is often `threading.local`, which gives each *thread* its own value. In
a thread-per-request server that works, each request runs on its own thread, so thread-local *is* request-
local. But async breaks the assumption: many tasks share *one* thread, so they share the same
`threading.local`, and it corrupts exactly as the module global did. `threading.local` is scoped to the wrong
thing for async concurrency.

`contextvars` is scoped to a *context*, a more general notion than a thread. In synchronous threaded code, each
thread has its own context, so a `ContextVar` behaves like `threading.local`. In async code, each Task has its
own context (via `contextvars.copy_context()`, which `asyncio` calls when creating a Task), so a `ContextVar`
is per-Task. The single abstraction covers both models, which is why `contextvars` is the correct home for
request-scoped state in *any* concurrent Python, sync or async: it tracks the logical flow of control, not the
OS thread. That is also why libraries that must work under both (loggers attaching a request ID, tracers
propagating a span) standardized on `contextvars`.

---

## 53.3 Measurement: correctness at no speed cost

**Methodology.** `code/ch053/bench_contextvar.py`. `ContextVar.get()`/`set()` versus a plain dict lookup.
`min` per call; ratios relative to the dict lookup. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | min per call | ratio |
|---|---|---|
| dict global lookup | **8.6 ns** | 1.00x |
| `ContextVar.get()` | **7.0 ns** | 0.82x |
| `ContextVar.set()` | **~100 ns** | ~12x |

`ContextVar.get()` is **7 ns**, as fast as (here slightly faster than) a dict lookup, because it is a C-level
read of the current context. `set()` is more expensive (~100 ns): it produces a new entry in the context's
immutable mapping, more work than mutating a dict in place. But `set()` happens *rarely*, once per request at
the entry point, while `get()` happens *often*, wherever the value is read, so the operation that dominates is
the fast one. In practice a `ContextVar` costs nothing measurable over a global for reads, and its one
per-request `set` is ~100 ns, negligible against a request's real work.

The conclusion: **the correctness of per-context state is essentially free.** There is no performance argument
for keeping request-scoped state in a fragile global; the `ContextVar` reads just as fast and does not
corrupt. The rule: **use a `ContextVar` for request-scoped state, request ID, current user, trace/span
context, in any concurrent code (async or threaded); set it once at the boundary and get it wherever needed.**
Reserve module globals for genuinely process-wide, immutable-after-startup configuration, never for
per-request state.

---

## 53.4 Edges and failure modes

**Request-scoped state in a global (async).** §53.1. Interleaving corrupts it. Use a `ContextVar`.

**`threading.local` under async.** §53.2. Tasks share a thread, so they share the thread-local. Use a
`ContextVar`, which is per-context (per-Task under async).

**Reading a `ContextVar` that was never set.** `get()` with no value and no default raises `LookupError`.
Provide a default (`ContextVar("x", default=None)` or `get(default)`) unless a missing value is genuinely a
bug you want to surface.

**Manually spawned threads do not inherit context automatically.** A `ContextVar` set in one thread is not
visible in a `threading.Thread` you start yourself unless you propagate it (`contextvars.copy_context().run(...)`).
`asyncio` copies context into Tasks for you; raw threads do not. `concurrent.futures` executors can be given
the context to run in.

**`set()` returns a `Token` for restoration, not a plain value.** To restore the previous value (e.g. in a
middleware that sets then unsets), keep the `Token` from `set()` and call `reset(token)`. Ignoring this and
re-`set`ting a guessed previous value is a bug in nested contexts.

**Overusing context variables as hidden globals.** A `ContextVar` is still implicit state; threading it through
too much logic makes data flow hard to follow. Use it for genuinely cross-cutting concerns (request ID,
tracing), not as a way to avoid passing explicit arguments where explicit is clearer.

---

## 53.5 Connections

**Backward.** The `asyncio` Task interleaving that corrupts the global is Chapters 10-11, `contextvars` is the
state model that survives it. The `threading.local` contrast is the threading model of Chapter 8. The
immutable-mapping implementation connects to the value-semantics theme of Chapter 4.

**Forward.** Structured logging and distributed tracing, which propagate a request/span context through a call
graph, are built on `contextvars`, further **Deep S** and observability material. The `copy_context` mechanism
that `asyncio` uses to isolate Tasks is the primitive behind context propagation across executors and Deep U's
distributed tracing.

**Across books.** `contextvars` is how Book II carries request identity into **Book III** without threading it
through every function. A **Book III** serving path sets a request ID and trace context at the boundary, and
every downstream stage, retrieval, inference glue, logging, reads it from the `ContextVar`, so logs and traces
correlate correctly even under high async concurrency. The §53.1 corruption is precisely the failure that
makes production logs untrustworthy, which **Deep U** exists to prevent at the observability seam.

---

## 53.6 Exercises

**1. Reproduce the corruption.** Run §53.1 and confirm the global-based handler returns all-same IDs while the
`ContextVar` handler returns each task's own. Explain, in terms of `await` interleaving, why the global is
clobbered.

**2. Break `threading.local` under async.** Repeat the experiment with `threading.local` instead of a global
and show it also corrupts under async. Explain why (tasks share a thread) and why `ContextVar` does not.

**3. Measure the cost.** Run §53.3's benchmark and confirm `get()` is as fast as a dict lookup and `set()` is
cheap-but-costlier. Explain why the read/write asymmetry does not matter given how each is used.

**4. Restore with a Token.** Write a middleware-style function that `set`s a `ContextVar`, runs a callback, and
`reset`s it with the `Token`. Show nested contexts restore correctly. Explain why re-setting a guessed
previous value would be wrong.

**5. The design question.** `contextvars` scopes state to a logical context rather than a thread, covering both
sync and async concurrency. Argue why this is the right abstraction. Your answer must use the §53.1 corruption
and §53.3 measurement, explain why `threading.local` is scoped to the wrong thing for async, and say when a
plain argument is still clearer than a context variable.

---

## 53.7 Summary and cross-references

- A **module global** for request-scoped state **corrupts under async interleaving** (tasks overwrite it
  across `await`); measured, five tasks all read the last writer's value.
- A **`ContextVar`** gives each logical context (async Task, thread) its own value, so per-request state stays
  correct. It is scoped to the *context*, not the thread, so it works where **`threading.local`** fails under
  async.
- **Measured:** `ContextVar.get()` is **~7 ns**, as fast as a dict lookup; `set()` (~100 ns, done once per
  request) is negligible. Correct per-context state costs essentially nothing.
- **Use a `ContextVar`** for request ID, current user, and trace context in concurrent code; provide a default
  or handle `LookupError`; restore with the `Token` from `set()`; propagate to raw threads with
  `copy_context`.

**Cross-references.** `asyncio` Task interleaving → Chapters 10-11. `threading.local` and threads → Chapter 8.
Value semantics → Chapter 4. Structured logging and tracing → the rest of Deep S. The observability seam →
Deep U.
