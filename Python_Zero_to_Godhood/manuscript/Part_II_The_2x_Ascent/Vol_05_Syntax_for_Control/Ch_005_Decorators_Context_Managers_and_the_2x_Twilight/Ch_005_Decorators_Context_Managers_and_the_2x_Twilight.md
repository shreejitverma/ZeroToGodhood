# Chapter 5: Decorators, Context Managers, and the 2.x Twilight (Python 2.4-2.7)

A team ships a web service with 200 route handlers, each decorated to add authentication. Every
endpoint works. Then they turn on the API documentation generator, and it reports 200 endpoints all
named `wrapper`, all with no description, because the auth decorator was written like this:

```python
def require_auth(f):
    def wrapper(*args, **kwargs):
        check_token()
        return f(*args, **kwargs)
    return wrapper          # f's __name__ and __doc__ are gone
```

The fix is one line, `@functools.wraps(f)`, and the reason it is needed is the subject of this
chapter: a decorator does not annotate a function, it *replaces* it, and unless you copy the original
function's identity across, every tool that reads that identity, the doc generator, the traceback
formatter, the framework's route table, sees the wrapper instead.

The late 2.x line added three features that turned Python's first-class functions and frames into
reusable structure: decorators (2.4), context managers (2.5), and generator coroutines (2.5). None is
syntax for its own sake. Decorators are function composition made declarative. Context managers are
Python's answer to C++ RAII, built on a guaranteed `try`/`finally`. Generator coroutines are the
suspendable frame that, a decade later, became `async`/`await`. This chapter teaches all three at
working depth and grounds each in the bytecode the interpreter actually emits.

## Section index

- **5.1** Decorators: composition made declarative (PEP 318, PEP 3129)
- **5.2** Context managers and `with` (PEP 343)
- **5.3** Generator coroutines: `send`, `throw`, `close` (PEP 342)
- **5.4** Measurement: what a decorator layer costs
- **5.5** Edges and failure modes
- **5.6** Connections
- **5.7** Exercises
- **5.8** Summary and cross-references

Listings live under `code/ch005/` and are re-executed by `make verify` on both interpreters.

---

## 5.1 Decorators: composition made declarative (PEP 318, PEP 3129)

**Why this exists.** Before Python 2.4, wrapping a function meant defining it and then rebinding the
name, with the transformation written *after* and *away from* the definition:

```python
# Pre-2.4 idiom: the wrapping is separated from the definition.
def query():
    ...
query = transaction(log(query))   # easy to miss; reads bottom-up, far from def
```

**PEP 318** introduced `@decorator` syntax so the transformation sits *on* the definition. It is pure
compile-time sugar: `@d` above `def f` means "after building `f`, replace it with `d(f)`." Stacked
decorators apply bottom-up, nearest the `def` first:

```python
# code/ch005/l01_decorators.py (excerpt)
@dec1
@dec2
def target():
    return "target"
```

Verified output (CPython 3.13.5):

```text
--- stacked decorators compose bottom-up ---
  result: dec1(dec2(target))
  __name__ preserved: target
```

The result `dec1(dec2(target))` is exactly the bottom-up composition. The compiler makes the
mechanism explicit, loading the decorators, building the function, then applying the calls
outermost-last:

```python
# code/ch005/l02_decorator_bytecode.py
```

Verified output (CPython 3.13.5):

```text
bytecode for  @dec1 / @dec2 / def t (opname [arg]):
  LOAD_NAME  dec1
  LOAD_NAME  dec2
  LOAD_CONST
  MAKE_FUNCTION
  CALL
  CALL
  STORE_NAME  t
```

Read the two `CALL`s bottom-up: `dec2` is applied to the freshly built function first, then `dec1` to
the result. This is current bytecode. `MAKE_FUNCTION` takes no inline argument now (closures and
defaults are applied by separate `SET_FUNCTION_ATTRIBUTE` opcodes when needed), and the call opcode is
the unified `CALL`, not the pre-3.11 `CALL_FUNCTION`. On 3.14 the sequence is identical except for a
trailing `LOAD_CONST` for the module's implicit return; both are recorded.

**`functools.wraps` is not optional**, which is the chapter's opening bug run as code:

```text
--- the bug functools.wraps prevents ---
  without wraps -> __name__: wrapper | __doc__: None
  a framework that routes by __name__, or a doc tool reading __doc__,
  now sees 'wrapper' and None for every decorated function.
```

A naive wrapper replaces the function's `__name__`, `__doc__`, `__qualname__`, and `__module__` with
the wrapper's. `@functools.wraps(f)` copies them across and sets `__wrapped__` to the original, so
introspection, tracebacks, and tools still see the real function. This is the single most common
decorator bug, and it is silent: the code works, only the metadata is wrong.

**Decorators with arguments** are decorator *factories*, a function returning a decorator. The output
above ends with `@repeat(3)` producing `['hi ada', 'hi ada', 'hi ada']`: `repeat(3)` returns a
decorator, which is then applied to `greet`. **Class decorators (PEP 3129, Python 2.6)** apply the
same rule to a class, `Model = class_decorator(Model)`, which is how `@dataclass` and
`@functools.total_ordering` work (Chapter 13).

---

## 5.2 Context managers and `with` (PEP 343)

**Why this exists.** Cleanup that must happen regardless of how a block exits, close a file, release a
lock, roll back a transaction, is exactly what C++ expresses with RAII and destructors. Python's
reference-counting finalization (Chapter 19) is too imprecise to rely on for this, and useless across
cycles (Chapter 3), so **PEP 343** added the `with` statement and the context-manager protocol:

- `__enter__(self)`: acquire; its return value is bound to the `as` target.
- `__exit__(self, exc_type, exc_val, exc_tb)`: release. On a clean exit all three are `None`. On an
  exception they carry its details, and **returning a truthy value suppresses the exception**; a
  falsy value (including `None`) lets it propagate.

```python
# code/ch005/l03_context_managers.py (excerpt)
class Ctx:
    def __enter__(self):
        print("  __enter__")
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("  __exit__ exc_type =", exc_type.__name__ if exc_type else None)
        return exc_type is ValueError      # suppress only ValueError
```

Verified output (CPython 3.13.5):

```text
--- clean exit: __exit__ sees three Nones ---
  __enter__
  body (clean)
  __exit__ exc_type = None
clean exit done

--- exception exit: __exit__ sees it and suppresses ValueError ---
  __enter__
  body raising ValueError
  __exit__ exc_type = ValueError
ValueError was suppressed by __exit__ returning truthy
```

**What the compiler does.** `with` desugars to a guaranteed `try`/`finally` around the block, with the
exception path routed through `__exit__`:

```python
# Conceptual desugaring of:  with expr as target: suite
mgr = expr
value = type(mgr).__enter__(mgr)
try:
    target = value          # if an "as" clause is present
    suite
except:                     # exception path
    if not type(mgr).__exit__(mgr, *sys.exc_info()):
        raise
else:                       # clean path
    type(mgr).__exit__(mgr, None, None, None)
```

The VM implements this with dedicated opcodes (`BEFORE_WITH`, `WITH_EXCEPT_START`) and the frame's
exception table (3.11+, Chapter 6) rather than the older runtime block stack, but the guarantee is
identical: `__exit__` runs on every exit path.

**`contextlib.contextmanager`** lets you write a context manager as a single generator; everything
before `yield` is `__enter__`, the `finally` is `__exit__`. The output above ends with `acquire`,
`using 42`, `release` in that order, from a five-line generator. `contextlib` adds the rest of the
toolkit, `suppress`, `closing`, `ExitStack`, `nullcontext`, covered in **Deep S**; here the point is
the protocol, and that it is Python's deterministic-cleanup primitive. Use it for every OS resource
instead of trusting `__del__`, whose timing Chapter 3 showed you cannot rely on.

---

## 5.3 Generator coroutines: `send`, `throw`, `close` (PEP 342)

**Why this exists.** Python 2.5's **PEP 342** upgraded generators from one-way producers into two-way
coroutines: a suspended frame you can resume *with a value*, inject an exception into, or shut down.
This is the conceptual seed of `async`/`await` (Chapter 11): a coroutine is a frame whose execution
pauses at a point and continues later.

The protocol adds three methods. `.send(value)` resumes the generator, and the paused `yield`
*expression* evaluates to `value`; `.send(None)` equals `next()`, and a fresh generator must be primed
with `next()` before a real send. `.throw(exc)` raises `exc` at the suspended `yield` point.
`.close()` raises `GeneratorExit` there, so the generator can release resources and return.

```python
# code/ch005/l04_generator_coroutine.py (excerpt)
def averager():
    total, count, avg = 0.0, 0, None
    while True:
        try:
            x = yield avg                 # value arrives via .send(x)
        except GeneratorExit:
            print("  averager closing")
            return
        total += x
        count += 1
        avg = total / count
```

Verified output (CPython 3.13.5):

```text
--- driving a coroutine with send() ---
  avg after 10:        10.0
  avg after 10,20:     15.0
  avg after 10,20,30:  20.0
  averager closing
--- priming is mandatory: send() on a just-started generator raises ---
  send(10) before priming -> TypeError: can't send non-None value to a just-started generator
```

**What the interpreter actually does.** At a `yield`, `_PyEval_EvalFrameDefault` does not destroy the
frame: it records the resume point (`f_lasti`), freezes the evaluation-stack depth, marks the
generator suspended, and detaches the frame from the thread state, returning control to the caller
while the frame stays alive on the heap. `.send` and `next` re-attach the frame and resume at
`f_lasti`. That **suspendable heap frame** is the mechanism `yield from` (Chapter 9) and native
coroutines (Chapter 11) generalize. This chapter keeps to the 2.5 milestone; the full
iterator/coroutine model is Chapter 9.

---

## 5.4 Measurement: what a decorator layer costs

The opening bug is about correctness. The other thing every guide says about decorators is a
performance claim, that a "transparent" pass-through wrapper is free, and it is testable.

**Methodology.** `code/ch005/bench_decorator_overhead.py`, through `_harness/bench.py`. 1000 calls per
timed loop of a trivial function three ways: called directly, called through one `*args`/`**kwargs`
pass-through wrapper, and an `lru_cache`-decorated recursive Fibonacci hitting a warm cache. `min` is
the headline; ratios within this one interpreter. CPython 3.13.5, `-O2`, Apple M3 Pro, macOS 27.0,
arm64. Ratios reproduced across runs.

| case | ratio vs bare call |
|---|---|
| bare call | 1.00x |
| one pass-through wrapper | **3.3x** |
| `lru_cache` hit | **1.3x** |

**A pass-through wrapper costs about 3.3x the bare call**, not nothing. "Transparent" describes the
semantics, not the cost: the wrapper is a second Python call that packs the arguments into a tuple and
a dict on the way in and unpacks them on the way out, and the specializing interpreter cannot fold
that away because the wrapper genuinely calls another function. Stack three decorators and you have
paid for three of these. For a route handler that then does a database query this is invisible; for a
function called a million times in a numeric inner loop it is not, and the fix is to not decorate the
inner function, decorate the boundary.

`lru_cache` is the instructive counter-case at **1.3x per hit**. That is *above* a bare call, so a
cache hit is not free either, yet `lru_cache` is one of the most valuable decorators in the language,
because it does not add work to the call, it *replaces* the work the call would have done. A warm
`cached_fib(30)` returns a stored result instead of recursing. The lesson generalizes the chapter's
three predecessors: a decorator's cost is a number, its value is what the number buys, and on a hot
path you measure both rather than assuming either.

---

## 5.5 Edges and failure modes

**Missing `functools.wraps`.** §5.1. Silent: the code works, the metadata is wrong, and every tool
that reads `__name__`/`__doc__`/`__wrapped__` is misled. Always wrap the wrapper. This is the chapter
opener and the single most common decorator mistake.

**A decorator on a hot inner function.** §5.4. Each layer is about 3.3x a bare call. Decorate the
boundary of the hot region, not the function inside the loop.

**Swallowing exceptions in `__exit__`.** §5.2. Returning truthy suppresses *all* matching exceptions,
which hides bugs. Suppress narrowly (check `exc_type`) or use `contextlib.suppress` with explicit
types.

**Trusting `__del__` for resource cleanup.** §5.2 and Chapter 3. Reference-count finalization is
imprecise and does not run for cycles. Use `with` for every OS resource, and `contextlib.closing` for
objects that have `.close()` but are not context managers.

**Sending to an un-primed generator.** §5.3. `.send(non_None)` on a just-started generator raises
`TypeError`. Prime with `next()` first, or use `async`/`await` for new code, which removes the manual
priming dance entirely.

**A decorator that changes the signature.** If a wrapper accepts different arguments than the function
it wraps, `functools.wraps` copies the *name* but not a corrected `inspect.signature`; tools that read
the signature will be wrong. For strict cases, adjust `__signature__` explicitly.

---

## 5.6 Connections

**Backward.** Decorators build on first-class functions and the frame model of Chapter 2, and the
`f_lasti` resume point a suspended generator records is that chapter's code-object machinery.
`property` and the descriptor alternative to decorators are Chapter 4. The reference-counting
finalization that context managers exist to replace is Chapter 19, and the cycles that defeat it are
Chapter 3.

**Forward.** The exception table that implements `with`'s guarantee is Chapter 6 (zero-cost
exceptions). The suspendable frame of §5.3 becomes `yield from` in Chapter 9 and native `async`/`await`
in Chapter 11, the through-line of the whole async story. `@dataclass` as a class decorator is Chapter
13. The full `contextlib` toolkit is **Deep S**. Benchmarking decorated hot paths is **Deep K**.

**Across books.** A context manager is Python's RAII, and it is exactly what you reach for at the
**Book I** boundary: a C++ resource acquired through `nanobind`, a device handle, a mapped buffer, is
wrapped in `__enter__`/`__exit__` so its release is deterministic rather than left to Python's garbage
collector, which does not understand the C++ object's lifetime. The order-book example acquires its
C++ matching engine this way. **Deep M** owns the boundary; this chapter provides the cleanup
primitive it uses.

---

## 5.7 Exercises

**1. Predict the composition.** Without running it, give the output of `f()`:

```python
def shout(g):
    def w(*a, **k): return g(*a, **k).upper()
    return w
def exclaim(g):
    def w(*a, **k): return g(*a, **k) + "!"
    return w

@shout
@exclaim
def f(): return "hi"
```

State the order the two decorators apply, and whether swapping the two `@` lines changes the result.
Explain using §5.1's bottom-up rule.

**2. Break introspection, then fix it.** Write a timing decorator without `functools.wraps` and show,
with `inspect.signature` and `help()`, exactly what a tool sees. Then add `wraps` and show the
difference. Which single attribute does `wraps` set that lets a debugger recover the original function
object, and why is that more useful than the name alone?

**3. Suppress the wrong thing.** Write a context manager whose `__exit__` suppresses `KeyError`, then
use it around a block that raises a `KeyError` you *did* want to see because it was a real bug.
Describe how you would notice, and rewrite the manager so it suppresses only the intended case. This is
the §5.5 failure mode made concrete.

**4. Measure a real decorator.** Take the benchmark from §5.4 and add your own decorator that does a
small amount of genuine work (say, increments a counter). Predict where it lands relative to the 3.3x
pass-through, then measure it to the standard of §5.4. Then answer: at what amount of per-call work
does the decorator's own overhead stop mattering?

**5. The design question.** Python's context manager is RAII expressed as a protocol with an explicit
`with` block; C++'s RAII is implicit in a destructor that runs at scope exit. Argue the trade. Your
answer must address the fact that Python has no deterministic destructor (Chapter 3), why the explicit
`with` is both more verbose and safer than relying on `__del__`, and one case where C++'s implicit
version is genuinely better.

---

## 5.8 Summary and cross-references

- **Decorators** are compile-time sugar for `f = d(f)`, applied **bottom-up**; parameterized
  decorators are factories, and class decorators (PEP 3129) apply the same rule to classes. Always use
  **`functools.wraps`**, or every tool that reads a function's identity sees the wrapper. This is the
  chapter's opening 200-endpoint bug.
- **Context managers** (`__enter__`/`__exit__`) are Python's **deterministic-cleanup** primitive, RAII
  on a guaranteed `try`/`finally`; `__exit__` returning truthy suppresses the exception. `contextlib`
  provides generator-based managers and a toolkit.
- **Generator coroutines** (PEP 342) add `send`/`throw`/`close`, making a generator a **suspendable,
  resumable heap frame**, the conceptual origin of `async`/`await`. A fresh generator must be primed.
- **Measured:** one pass-through decorator costs about **3.3x** a bare call; an `lru_cache` hit costs
  about **1.3x** but *replaces* the work it caches. "Transparent" is about semantics, not cost.

**Cross-references.** First-class functions, frames, and `f_lasti` → Chapter 2. Reference counting
versus deterministic cleanup → Chapter 19; the cycles that defeat `__del__` → Chapter 3. Descriptors
as an alternative to decorators → Chapter 4. The exception table behind `with` → Chapter 6. `yield
from` and native coroutines → Chapters 9 and 11. `@dataclass` → Chapter 13. The full `contextlib`
reference → Deep S. Benchmarking discipline → Deep K. The C-API boundary and RAII across it → Deep M.
