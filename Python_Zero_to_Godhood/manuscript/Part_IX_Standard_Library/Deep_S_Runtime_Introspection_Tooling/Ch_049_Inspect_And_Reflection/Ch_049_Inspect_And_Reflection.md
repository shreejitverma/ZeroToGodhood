# Chapter 49: Introspection with `inspect`

A web framework reads each handler's parameters to inject dependencies: for every request, it calls
`inspect.signature(handler)` to learn what arguments the function wants, then supplies them. It is elegant,
and it is a performance bug. `inspect.signature` builds a full `Signature` object, parsing every parameter's
kind, default, and annotation into `Parameter` objects, on every call, and that is **220x** more expensive
than reading the raw `__code__.co_varnames` tuple it is derived from (4936 ns versus 22 ns). The signature of
a given function never changes, so computing it per request is pure waste; caching it once turns the 220x
back into a cheap dictionary access. Reflection is a rich convenience with a real cost, and the discipline is
to pay that cost *once*.

This chapter opens **Deep S** (runtime services, introspection, tooling) with `inspect`, the module that
turns Python's raw introspection attributes into a structured, uniform API. It is what frameworks use to read
functions and classes at runtime, and understanding both its power and its price is what separates a fast
framework from a slow one.

## Section index

- **49.1** The reflection API
- **49.2** Why `signature` is expensive
- **49.3** Measurement: three ways to introspect
- **49.4** Edges and failure modes
- **49.5** Connections
- **49.6** Exercises
- **49.7** Summary and cross-references

Listings live under `code/ch049/` and are re-executed by `make verify` on both interpreters.

---

## 49.1 The reflection API

```python
# code/ch049/l01_inspect.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- signature: parameters, kinds, defaults, annotations, as objects ---
  str(signature)      : (user_id: int, name: str, active: bool = True, *tags, **opts) -> dict
    user_id  kind=POSITIONAL_OR_KEYWORD default=-
    name     kind=POSITIONAL_OR_KEYWORD default=-
    active   kind=POSITIONAL_OR_KEYWORD default=True
    tags     kind=VAR_POSITIONAL     default=-
    opts     kind=VAR_KEYWORD        default=-
  return annotation   : dict
--- type predicates: a uniform way to ask 'what is this?' ---
  isfunction(handler) : True
  isclass(int)        : True
  ismethod(handler)   : False
  isbuiltin(len)      : True
--- binding arguments to parameters (what a framework does) ---
  bind(42, 'Ada')     : {'user_id': 42, 'name': 'Ada', 'active': True, 'tags': (), 'opts': {}}
--- the raw attributes inspect builds on (cheap, but unstructured) ---
  handler.__code__.co_varnames : ('user_id', 'name')...
  handler.__annotations__ keys : ['active', 'name', 'return', 'user_id']
```

**`inspect.signature`** is the centerpiece: it returns a `Signature` whose `parameters` map each parameter
name to a `Parameter` object carrying its **kind** (`POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL` for `*tags`,
`VAR_KEYWORD` for `**opts`, and also `POSITIONAL_ONLY`/`KEYWORD_ONLY`), its **default**, and its
**annotation**, plus the return annotation. This is the structured view that raw `__code__` cannot give you,
the parameter *kinds* especially are not a single attribute you can read.

**Type predicates** (`isfunction`, `isclass`, `ismethod`, `isbuiltin`, and many more) give a uniform,
readable way to classify an object, clearer and more correct than manual `type(...)` checks. **Argument
binding** (`sig.bind(...)` plus `apply_defaults()`) maps a call's arguments onto the parameters exactly as
Python would, filling defaults, which is precisely the operation a dependency-injection or validation
framework performs. The bottom block shows the raw attributes `inspect` is built on (`__code__.co_varnames`,
`__annotations__`): cheap to read, but unstructured, you would have to reconstruct kinds and defaults
yourself, which is what `inspect` does for you (at the cost §49.3 measures).

---

## 49.2 Why `signature` is expensive

`inspect.signature` does far more than read an attribute. It examines the callable (unwrapping decorators via
`__wrapped__`, following `__signature__` overrides, handling functions, methods, classes, `functools.partial`,
and builtins differently), reads `__code__` for the parameter names and flags, reads `__defaults__` and
`__kwdefaults__` for defaults, reads `__annotations__` for types, and constructs a `Signature` object holding
an ordered mapping of freshly built `Parameter` objects. Every one of those `Parameter` objects is a new
allocation with its own attributes. That is a lot of work to produce the rich, uniform view, and it happens
in full on every call, because `signature` does not cache.

Reading `f.__code__.co_varnames` is, by contrast, one tuple attribute access, no parsing, no allocation, no
object model. It gives you names only (and not cleanly separated into parameters versus locals), which is why
it is 200x cheaper and also why it is not what you usually want. The gap is the price of structure: `inspect`
converts a scattering of dunder attributes into a coherent API, and that conversion is the cost.

The consequence is a caching rule. A function's signature is *immutable* for the life of the function, so the
expensive `Signature` should be computed once and reused. Frameworks that reflect per request must memoize,
`functools.lru_cache` on the signature lookup (Chapter 34), or a dict keyed by the function, turning 220x per
request into a one-time cost amortized to nothing.

---

## 49.3 Measurement: three ways to introspect

**Methodology.** `code/ch049/bench_signature.py`. Three ways to learn a function's parameters: raw
`__code__.co_varnames`, a cached `Signature`'s `.parameters`, and a fresh `inspect.signature(f)` each call.
`min` per call; ratios relative to the raw attribute. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| approach | min per call | ratio |
|---|---|---|
| raw `__code__.co_varnames` | **22 ns** | 1.00x |
| cached `Signature.parameters` | **12.5 ns** | 0.56x |
| `inspect.signature(f)` (fresh) | **4936 ns** | **220x** |

Reading the raw tuple is 22 ns. Accessing a *cached* `Signature`'s `.parameters` is even cheaper (12.5 ns, a
mapping attribute access). Building a fresh `Signature` is **4936 ns, 220x** the raw access, because it does
all the parsing and allocation of §49.2 every time. The cached and fresh numbers are the same operation's
result reused versus recomputed, and the 200x-plus between them is the entire argument for caching.

The rule: **use `inspect` for its rich, correct, uniform view, and cache the results.** Reflection is a
setup-time or first-call activity, not a per-call one. A framework should reflect each handler *once* (at
registration, or on first call with memoization) and reuse the `Signature` forever after. Never call
`inspect.signature`, `inspect.getmembers`, or `inspect.getsource` inside a hot loop or per request; they are
expensive precisely because they are thorough.

---

## 49.4 Edges and failure modes

**`inspect.signature` in a hot path.** §49.3. 220x a raw attribute read. Cache the `Signature` (per function,
it never changes); reflect once, reuse forever.

**Signatures of wrapped functions.** A decorator that does not use `functools.wraps` (Chapter 5) hides the
wrapped function's signature; `inspect.signature` then reports the *wrapper's* signature (often `(*args,
**kwargs)`). Use `functools.wraps` so `__wrapped__` lets `inspect` see through, or pass
`follow_wrapped=False` deliberately.

**Builtins and C functions.** Some C-implemented callables have no introspectable signature and
`inspect.signature` raises `ValueError`. Guard for it, or rely on `__text_signature__` where present; do not
assume every callable yields a signature.

**`getsource` needs source on disk.** `inspect.getsource`/`getsourcelines` read the `.py` file, so they fail
for objects defined in the REPL, in a C extension, or in a stripped/`.pyc`-only deployment. Do not depend on
source availability at runtime.

**`inspect.stack()` is very expensive.** Walking the call stack with `inspect.stack()` reads source context
for every frame and is far heavier than `sys._getframe()`. Avoid `inspect.stack()` in logging or hot paths;
use the lighter frame APIs when you only need the frame, not its source.

**Mutating what you introspect.** Introspection can encourage runtime monkey-patching of signatures,
annotations, or members. It is powerful and fragile: a patched `__signature__` that disagrees with the actual
parameters makes `bind` and callers lie to each other. Prefer reading over rewriting.

---

## 49.5 Connections

**Backward.** The raw attributes `inspect` structures, `__code__`, `__defaults__`, `__annotations__`, are the
function object internals of Chapters 5 and 12 (annotations, PEP 649 deferred evaluation). `functools.wraps`
and `lru_cache` (for caching signatures) are Chapters 5 and 34. The parameter kinds (positional-only,
keyword-only) are Chapter 14. The `Signature`/`Parameter` object model is ordinary classes (Chapter 4).

**Forward.** `typing.get_type_hints` (resolving annotations to types, respecting PEP 649) is the typing-side
companion, Chapter 16 and later Deep S. `dis` (disassembling `__code__` to bytecode) is the next Deep S
introspection tool. The `sys.monitoring`/`settrace` runtime hooks are Chapter 22. Metaclasses, which
introspect and rewrite classes at creation, are Chapter 31.

**Across books.** Cached reflection is how Book II builds the framework glue that **Book III** rides on. A
**Book III** serving layer that maps HTTP requests to Python handlers, or tools to LLM function-calling
schemas, reflects each handler's signature *once* at registration to generate the schema, then dispatches
without reflecting again. The §49.3 caching rule is what keeps that dispatch fast per request. **Deep U** owns
the framework seam; the schema generation from signatures is a **Book III** bridge.

---

## 49.6 Exercises

**1. Reproduce the reflection cost.** Run §49.3's benchmark and confirm `inspect.signature` is orders of
magnitude more expensive than a cached `Signature` or a raw attribute. Explain what `signature` does that the
attribute read does not.

**2. Cache a signature.** Wrap a per-call `inspect.signature(f)` lookup in `functools.lru_cache` (keyed by the
function) and show the amortized cost collapses. Explain why a function's signature can safely be cached
forever.

**3. See through a decorator.** Write a decorator with and without `functools.wraps` and show that
`inspect.signature` reports the wrapper's signature in the unwrapped case and the real one when `wraps` is
used. Explain the role of `__wrapped__`.

**4. Bind like a framework.** Use `sig.bind(...)` and `apply_defaults()` to map a call's arguments onto a
function's parameters, and show it fills defaults and separates `*args`/`**kwargs`. Explain how a
dependency-injection framework would use this.

**5. The design question.** `inspect` offers a rich, uniform reflection API layered over cheap raw dunder
attributes. Argue why both layers exist. Your answer must use the §49.3 measurement, explain what structure
`inspect` adds that the raw attributes lack, and state the caching discipline that makes rich reflection
affordable in a framework.

---

## 49.7 Summary and cross-references

- **`inspect`** structures Python's raw introspection attributes into a uniform API: **`signature`**
  (parameters with kinds, defaults, annotations, as objects), **type predicates** (`isfunction`, `isclass`,
  ...), **argument binding** (`bind` + `apply_defaults`), and source/member access.
- **`inspect.signature` is expensive:** it builds a full `Signature`/`Parameter` model on every call.
- **Measured:** a fresh `inspect.signature(f)` is **220x** a raw `__code__.co_varnames` read (4936 ns vs 22
  ns); a *cached* `Signature` is cheaper than the raw read. **Reflect once and cache;** never call
  `signature`/`getmembers`/`getsource` in a hot path.
- **Edges:** use `functools.wraps` so signatures see through decorators; guard for builtins with no signature;
  `getsource` needs source on disk; `inspect.stack()` is very heavy.

**Cross-references.** Function internals and `wraps` → Chapters 5, 12. `lru_cache` → Chapter 34. Parameter
kinds → Chapter 14. Annotations and `get_type_hints` → Chapter 16. `dis` and runtime hooks → the rest of Deep
S and Chapter 22. Metaclasses → Chapter 31. The framework seam → Deep U.
