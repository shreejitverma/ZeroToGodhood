# Chapter 129: Middleware, the Onion

Chapter 126 noted, almost in passing, that because a WSGI app is a callable, **middleware is an app that wraps an app**. This chapter makes that concrete and proves its two governing facts, because middleware is where cross-cutting concerns, auth, logging, compression, error handling, live, and getting its structure wrong is a security bug, not a style lapse.

The first fact is the **onion**: a request descends through the layers outside-in and the response ascends inside-out, so each middleware sees the request going down and the response coming up, one wrapper, two hooks. The listing prints the trace, `timing:in -> auth:in -> gzip:in -> gzip:out -> auth:out -> timing:out`, and the nesting *is* the execution order. The second fact is that **order is semantic**: `timing` outside `gzip` measures the handler *plus* compression; `gzip` outside `timing` measures the handler *without* it, same two layers, different meaning. And the short-circuit case shows why placement is security: an `auth` layer that rejects on the way down (`timing:in -> auth:in -> auth:reject -> timing:out`) means `gzip` and the handler *never ran*.

The benchmark turns that into the chapter's sharpest number. A pass-through layer costs ~13 ns (a function call, Chapter 55), so deep stacks are cheap. But rejecting a bad request from the **outermost** layer costs **20 ns** while rejecting from the **innermost** (after eight expensive layers) costs **31,721 ns**, a **1,570x** difference. **Put auth on the outside and you reject an attack for free; put it on the inside and you pay full price to refuse it.**

**This is a Deep V chapter.**
Chapters 126-127 own the callable contract middleware exploits; Chapter 130 owns the error handling that the outermost layer performs. This chapter owns the onion: composition, order, and short-circuiting.

## Section index

- **129.1** The onion, traced
- **129.2** The model: wrapped callables, two hooks, one order
- **129.3** Measurement: cheap layers, expensive misplacement
- **129.4** Edges and failure modes
- **129.5** Connections
- **129.6** Exercises
- **129.7** Summary and cross-references

Listings live under `code/ch210/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 129.1 The onion, traced

```python
# code/ch210/l01_middleware_the_onion.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the onion: request descends, response ascends ---
  response : 200  b'GZ(hello alice)'
  order    : timing:in -> auth:in -> gzip:in -> gzip:out -> auth:out -> timing:out
  every :in precedes its :out, and they nest: timing wraps auth
  wraps gzip wraps the handler. one function, two hooks (before and
  after the inner call), and the nesting IS the execution order
--- short-circuit: an outer layer can stop the descent ---
  response : 401  b'unauthorized'
  order    : timing:in -> auth:in -> auth:reject -> timing:out
  auth rejected on the way DOWN, so gzip and the handler never ran
  and only timing's :out fired: this is why auth must be OUTSIDE
  expensive work - it saves the work it rejects
--- order is semantic: swap two layers, change behaviour ---
  gzip-outside-timing : gzip:in -> timing:in -> timing:out -> gzip:out
  timing-outside-gzip : timing:in -> gzip:in -> gzip:out -> timing:out
  in the first, timing measures the handler WITHOUT compression; in
  the second, it measures handler PLUS compression. same layers,
  different meaning - the stack order is a design decision with
  performance and security consequences, not a list to shuffle
--- the rules the onion imposes ---
  outermost: things that should reject/handle before work (auth,
    rate limiting, request-id assignment)
  middle: things that transform (compression, content negotiation)
  innermost: things measuring the real work (timing the handler)
  and: a layer that raises must be caught by a layer OUTSIDE it, so
  the error-handling middleware goes near the top (Chapter 130)
```

**The trace is the onion, and the nesting is the mechanism.**
`timing:in ... timing:out` brackets everything; inside it `auth:in ... auth:out` brackets the rest; inside that `gzip`. Each middleware is a function that does something, calls the inner app, and does something with the result, so "before" code runs on the descent (in registration/outer order) and "after" code runs on the ascent (in reverse). This is the *decorator pattern* (Chapter 5) applied to request handling, and the trace makes visible what "wraps" means: it is call nesting, nothing more mysterious.

**Short-circuiting is the onion's most consequential property.**
When `auth` returns 401 without calling its inner app, the descent *stops*: `gzip` and the handler are never entered, and on the ascent only the layers *above* auth run their "after" code (`timing:out` fired; `gzip:out` did not). This is how an outer layer *protects* the inner ones, from unauthenticated requests, from rate-exceeded requests, from malformed requests, and §129.3 measures exactly what that protection is worth.

**And the order-swap block proves placement is design.**
`timing` outside `gzip` times the handler *and* the compression; `gzip` outside `timing` times only the handler. The measurement means different things, one includes compression cost, one excludes it, and neither is wrong, but choosing requires knowing what you want to measure. Multiply this across auth, caching, compression, and logging and the stack order determines what is cached (compressed or not?), what auth sees (the raw or transformed request?), and what logs record, a design decision with performance and security consequences, never a list to shuffle.

---

## 129.2 The model: wrapped callables, two hooks, one order

**Middleware is a function `(inner_app) -> new_app`.**
It receives the app it wraps and returns a replacement with the same signature, so the composed result is still an app the gateway can call (Chapters 126-127). Because the signature is preserved, middleware composes arbitrarily deep, and the composition is *associative in structure but not in behaviour*, the layers always nest, but what each does depends on its neighbours. WSGI middleware wraps `(environ, start_response)`; ASGI middleware wraps `(scope, receive, send)` and is `async`; the pattern is identical, only the contract changes.

**Two hooks, and their placement relative to the inner call is everything.**
Code *before* `inner(request)` runs on the descent (request-side: authenticate, add a request id, start a timer, parse a body); code *after* runs on the ascent (response-side: compress, add headers, log the status, stop the timer). A middleware may use one hook or both, and it may *skip* the inner call entirely (short-circuit) or call it *multiple* times (retry, though rare and dangerous). The mental model is a function with the real work in the middle, and every middleware you read parses into "what does it do before, and after, the `inner` call".

**Order is a partial specification of a total structure.**
The rules the onion imposes are a layering: reject-early concerns outermost (auth, rate limiting, request-id assignment, error handling), transforming concerns in the middle (compression, content negotiation), measuring concerns innermost (timing the *real* work). Error handling is subtle, a layer that raises must be caught by a layer *outside* it, so the error-catching middleware goes near the top, which is why Chapter 130's error handling is the outermost non-security layer. Get the layering right and each concern sees exactly the request/response it should; get it wrong and auth inspects a compressed body, or the timer includes the auth rejection, or an error escapes uncaught.

**The pattern is the framework's extension mechanism.**
Every framework's "middleware", "filters", "interceptors" is this: user code inserted into the request cycle as wrapped callables. The power is that cross-cutting concerns compose without touching handlers (a handler does not know it is timed, authed, and compressed), and the danger is that the composition is invisible at the handler, the request the handler receives has already been through N transformations it cannot see. This is the same power-and-danger as decorators (Chapter 5) and context managers, and the discipline is the same: keep each layer's contract narrow and its ordering documented.

---

## 129.3 Measurement: cheap layers, expensive misplacement

**Methodology.** `code/ch210/bench_middleware_stack.py`.
`min` of 15; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Per-layer overhead:**

| stack | time | vs bare |
|---|---|---|
| bare handler | 14.7 ns | 1.00x |
| 1 middleware | 26.3 ns | 1.79x |
| 4 middlewares | 59.8 ns | 4.07x |
| 8 middlewares | 105.9 ns | 7.20x |

**b. Short-circuiting a bad request (8 expensive layers):**

| placement | time |
|---|---|
| reject from the **outermost** layer | 20.2 ns |
| reject from the **innermost** layer | **31,721 ns (1,570x)** |

**Table a says: stack freely.**
Each layer is a function call wrapping a function call (Chapter 55's ~12 ns), so eight layers cost ~90 ns over the bare handler, linear and cheap. This is why frameworks stack a dozen middlewares without ceremony and why "too much middleware is slow" is almost never true, the per-layer cost is nanoseconds against a handler that does milliseconds of real work. The onion's *depth* is free; its *order* is not.

**Table b is the chapter, as a number.**
Reject a bad request from the outermost layer and it costs 20 ns, one layer's check, then stop. Reject the *same* request from the innermost layer, after eight expensive layers have run, and it costs 31,721 ns, **1,570x more**, because the request paid for all the work before being refused. This is Chapter 129's short-circuit made quantitative, and it is a *security* result: a service whose auth is innermost does full request processing for every unauthenticated request, which is a denial-of-service amplifier (an attacker sends garbage and you do 8 layers of work to reject each one). **Auth, rate limiting, and cheap validation belong outermost** so the stack does no work for the requests it will refuse, and the 1,570x is what that placement is worth against an attack.

**Book I**'s gateway orders its filter chain by the same principle, cheap rejections first, and its DDoS-resilience chapter cites the identical arithmetic: the cost of processing a request you will reject, times the rate an attacker can send them, is the amplification factor, and pushing rejection to the edge (even to the load balancer, before the app) collapses it. The shared system rejects unauthenticated order requests at its outermost layer, so a flood of forged orders costs a signature check each, not a matching-engine call each, Chapter 84's boundary discipline applied to the request cycle.

---

## 129.4 Edges and failure modes

**Auth inside expensive work is a DoS amplifier.** §129.3.
The 1,570x is not academic: an attacker who can make you do N layers of work per rejected request has an N-times amplification. Reject at the outermost feasible point, the load balancer, the gateway, the first middleware, and never after the expensive work. This is the measured reason the layering rule leads with security.

**A middleware that swallows exceptions hides failures.**
A layer with a bare `except:` around `inner()` that returns 200 on error turns handler bugs into silent wrong answers, and turns the outer error-handling middleware into a no-op (the error never reaches it). Middleware either handles a *specific* exception it understands or re-raises; the error-handling layer at the top is the one place a catch-all belongs (Chapter 130).

**Order changes what each layer sees, silently.**
Compression outside caching caches *compressed* bodies (good for bandwidth, wrong if the cache is shared across `Accept-Encoding` values); auth outside body-parsing authenticates before reading the body (good) but cannot auth *based on* the body (bad for signature-over-body schemes). Every ordering is a set of tradeoffs, and swapping two layers to "clean up the config" is a behaviour change, tested or not.

**Response-side code runs even on short-circuit, for layers above the cut.** §129.1.
`timing:out` fired when auth rejected; a layer whose "after" code assumes the handler ran (reads a handler-set attribute, closes a handler-opened resource) crashes or misbehaves on short-circuit. Response-side code must tolerate the inner app not having run its expected path, the middleware equivalent of `finally` correctness.

**Async and sync middleware do not mix without a bridge.**
An ASGI (async) stack cannot include a WSGI (sync) middleware directly; the thread bridge (Chapter 107, Chapter 127) is required, and a sync middleware that blocks stalls the whole loop (Chapter 127's fatal edge). Stacks must be homogeneous in colour, or bridge explicitly.

**Middleware state and the free-threaded build.**
A middleware holding shared mutable state (a counter, a cache) across requests is shared across the workers/threads serving them; under the free-threaded build (Chapter 96) that state needs the same locking discipline as any shared object, and even under the GIL a per-request assumption baked into module-level state is a concurrency bug. Middleware should be stateless or explicitly synchronised.

**And "it works" hides ordering bugs until an edge case.**
An auth-inside-cache stack serves cached responses *without re-authenticating* (the cache short-circuits before auth), a critical bug invisible until someone accesses another user's cached data. Ordering bugs are latent and severe; the mitigation is the same as Chapter 128's overlap tests, test the *interactions*, especially auth-vs-cache and error-vs-everything.

---

## 129.5 Connections

**Backward.**
The callable contract middleware wraps, Chapters 126-127; the decorator pattern it instances, Chapter 5; the function-call cost per layer, Chapter 55; the short-circuit-as-cheap-rejection principle shared with Chapter 84's boundary discipline; shared-state hazards under free-threading, Chapter 96.

**Forward.**
The error-handling middleware that sits outermost and turns exceptions into responses, and the content negotiation a transforming layer performs, Chapter 130; the trading service whose auth and rate-limiting middleware protect the matching engine, Chapter 131.

**Across books.**
The onion is universal, **Book I**'s filter chains, servlet filters, HTTP interceptors, all the same wrapped-handler pattern, and both books order it security-first for the same measured DoS-amplification reason. The shared system's request cycle looks identical in both languages because the pattern is about composition, not syntax, which is the volume's recurring point.

---

## 129.6 Exercises

**1. Trace your own stack.** Instrument a real framework's middleware (Django, Starlette) to print the onion trace for one request; identify each layer's before/after hooks and confirm the nesting.

**2. Measure the amplifier.** Reproduce §129.3b with auth outermost and innermost; then simulate an attack (1,000 unauthenticated requests) and report total work done in each placement. Compute the amplification factor.

**3. Break auth-vs-cache.** Build a stack with caching outside auth; demonstrate a cached response served without re-authentication (the critical bug); fix by ordering and add the test that catches it.

**4. Error middleware.** Write the outermost error-handling middleware that catches any handler exception, logs it with the request id (assigned by an even-outer layer), and returns a 500 with no stack trace to the client. Test that a handler `raise` becomes a clean 500.

**5. Async onion.** Port the listing to ASGI (async middleware); prove the trace is identical and that a blocking sync middleware stalls the loop (Chapter 127), then bridge it correctly.

**6. The design question.** Middleware makes cross-cutting concerns invisible at the handler, which is its power (handlers stay clean) and its danger (the handler cannot see what transformed its request). Argue where the line should sit: what belongs in middleware (auth, logging, compression, universally cross-cutting) versus what belongs explicitly in the handler (business validation, which the handler *should* see), and how the invisibility interacts with debugging (a request that arrives "wrong" at the handler because a middleware transformed it). Then check how observability tools (request-id propagation, structured logging) mitigate the invisibility, and whether that vindicates deep stacks.

---

## 129.7 Summary and cross-references

- **Middleware is a wrapped callable `(inner) -> app`**, and the request descends outside-in while the response ascends inside-out, the onion, with two hooks (before and after the inner call) and the nesting *as* the execution order.
- **Order is semantic, not stylistic**: `timing` outside vs inside `gzip` measures different things; auth outside vs inside the handler protects vs fails to protect; caching outside auth is a critical bug. Swapping layers is a behaviour change.
- **Short-circuiting is the onion's key property**: an outer layer that rejects stops the descent, so inner layers never run, and only outer "after" code fires.
- **Measured**: layers are cheap (~13 ns each, stack freely), but **rejecting from the outermost layer costs 20 ns vs 31,721 ns (1,570x) from the innermost**, a DoS-amplification result that makes auth-outermost a security requirement, not a preference.
- **The layering**: reject-early outermost (auth, rate limiting, error handling), transforms in the middle (compression, negotiation), measurement innermost; response-side code must tolerate short-circuits, exceptions must reach the outer handler, and shared state needs synchronisation.

**Cross-references.** The gateways → Chapters 126-127. Decorators → Chapter 5. Call cost → Chapter 55. Boundary/rejection economics → Chapter 84. Free-threaded shared state → Chapter 96. Error handling and negotiation → Chapter 130. The trading service → Chapter 131.
