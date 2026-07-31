# Chapter 126: WSGI, the Synchronous Gateway

Chapter 125 left HTTP as text on a socket; this chapter is the contract that turned that text into a *callable*. Before WSGI (PEP 333, refined as PEP 3333), every Python web server had its own application interface, so an app was married to a server, choose mod_python and you could not move to CherryPy without a rewrite. WSGI is one function signature that divorced them: **an application is a callable `app(environ, start_response)`** that reads the request from a dict, calls `start_response` with a status and headers, and *returns an iterable of body bytes*. That is the entire contract, and its consequences shaped a decade of Python web work.

The listing implements a complete app against it, three routes, a POST that echoes its body, and drives it two ways. In-process: a request is `call_app(application, "GET", "/ping")` returning `('200 OK', headers, b'pong')`, **a dict in, a tuple out, no socket, no server, no framework**, which is why the contract won: an app is trivially testable and composable because it is a plain function. Through `wsgiref.validate.validator`: the stdlib ships a *machine-checker* for the spec (bytes not str, headers well-formed, `start_response` called once), so the contract is enforceable, not hoped-for.

And the listing names the shape's ceiling: WSGI is **synchronous**, the app *returns* when the response is ready, so one request holds one worker for its whole duration. The benchmark makes that arithmetic brutal: 64 workers serving 100 ms-I/O requests cap at **634 req/s while using 1% of a CPU**, capacity paid for and unusable, the C10k wall that the sync contract cannot climb and the exact reason ASGI exists.

**This is a Deep V chapter.**
Chapter 125 owns the protocol beneath; Chapter 127 owns the async successor. This chapter owns WSGI: the callable contract, the `environ` dict, and the synchronous ceiling.

## Section index

- **126.1** The contract, implemented and validated
- **126.2** The model: a callable, a dict, and one return
- **126.3** Measurement: cheap dispatch, capped throughput
- **126.4** Edges and failure modes
- **126.5** Connections
- **126.6** Exercises
- **126.7** Summary and cross-references

Listings live under `code/ch207/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 126.1 The contract, implemented and validated

```python
# code/ch207/l01_wsgi_the_contract.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the app is a callable: test it with a dict, no server ---
  GET /ping   -> 200 OK  b'pong'
  POST /echo  -> 200 OK  b'order:buy:100'
  GET /nope   -> 404 Not Found  b'not found'
  no socket, no server, no framework: a WSGI app is app(environ,
  start_response) -> iterable, so a test is a dict in and a tuple
  out. this testability is WHY the contract won
--- environ is the request as a flat dict ---
  environ['REQUEST_METHOD']           : 'GET'
  environ['PATH_INFO']                : '/orders/42'
  environ['QUERY_STRING']             : 'verbose=1'
  environ['SERVER_PROTOCOL']          : 'HTTP/1.0'
  environ['wsgi.version']             : (1, 0)
  Chapter 125's request line and headers, flattened into CGI-style
  keys plus wsgi.* extensions - the server's job is to parse the
  socket into this dict, the app's job is to read it
--- the contract is enforceable: validator wraps any app ---
  through wsgiref.validate.validator : 200 OK  b'pong'
  the stdlib ships a VALIDATOR that checks an app obeys the spec
  (bytes not str for the body, headers well-formed, start_response
  called once): the contract is a spec you can machine-check, not
  a convention you hope for
```

**The in-process calls are the contract's whole value proposition.**
No server ran; `call_app` built an `environ` dict, invoked the app, captured what `start_response` was handed, and joined the returned iterable. That means a WSGI app's *unit test is a function call*, no fixtures, no live socket, no async event loop, which is why WSGI apps and their test suites were the most portable, most testable web code Python had, and why every sync framework (Flask, Django, Bottle) is a WSGI app under the decorators.

**`environ` is Chapter 125's request as a flat dict.**
The request line's method and path become `REQUEST_METHOD` and `PATH_INFO`; the query string, protocol, and headers (as `HTTP_*` keys) join them, plus `wsgi.*` extensions (`wsgi.input`, the body stream; `wsgi.version`). The CGI-style naming is inherited history, but the shape is the lesson: **the server's job is to parse the socket into this dict; the app's job is to read it**, a clean seam that let servers and apps evolve independently.

**And the validator makes the contract a spec, not a hope.**
`wsgiref.validate.validator` wraps any app and asserts the rules at runtime, body items are bytes, `start_response` is called exactly once before the body, headers are well-formed, the iterable is closed. A contract you can machine-check is a contract that composes safely (Chapter 128's middleware stacks depend on it), and shipping the checker in the stdlib is how the ecosystem kept a decade of independent implementations interoperable.

---

## 126.2 The model: a callable, a dict, and one return

**The signature is the interoperability.**
Any callable of `(environ, start_response)` returning an iterable of bytes is an app; any server that calls such a callable is a server. That single agreement decoupled the two markets, servers (Gunicorn, uWSGI, mod_wsgi) competed on performance and ops, frameworks competed on developer experience, and any app ran on any server. It is the same move PEP 517 made for build backends (Chapter 111): *standardise the interface, let the implementations bloom*, and Deep V will make the parallel explicit.

**`start_response` plus a returned iterable is a deliberate two-phase design.**
The app sets status and headers *first* (via the callback), then produces the body *second* (via the return value), which lets a server send headers before the body is fully built and lets the body be a *generator* (streaming, Chapter 91, a large export yielded in chunks without materialising). The `exc_info` third argument to `start_response` handles the "error after headers already sent" case, the protocol-level reality that once bytes are on the wire, you cannot change your mind about the status.

**Synchronous is not an accident; it is the model's essence.**
The app *returns* its response, so control comes back to the server only when the work is done, and while the app runs, its worker is occupied. This makes WSGI apps simple to write (ordinary top-to-bottom code, ordinary `try/except`, ordinary blocking calls) and simple to reason about (no `await`, no colour, Chapter 102's two-colour problem does not exist here), at the cost the next section measures. Concurrency is *external*: run N worker processes or threads (Deep L), and the OS interleaves them.

**The middleware pattern falls out of the signature for free.**
Because an app is a callable and a server calls a callable, *middleware is an app that wraps an app*, it receives `environ`/`start_response`, does something, and calls the inner app. The validator itself is middleware. This composability, the whole of Chapter 128, exists only because the contract is a plain callable, and it is the second reason WSGI's shape outlived the servers that first implemented it.

---

## 126.3 Measurement: cheap dispatch, capped throughput

**Methodology.** `code/ch207/bench_wsgi_ceiling.py`.
Dispatch overhead `min` of 15; the ceiling is an arithmetic Little's-law model (deterministic); 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Dispatch overhead:**

| call | time |
|---|---|
| `handler()` direct | 14.1 ns |
| through the WSGI app | 259.6 ns |

**b. The synchronous ceiling** (1 ms CPU per request, plus I/O wait):

| workers | I/O wait | req/s | CPU used |
|---|---|---|---|
| 16 | 0 ms | 16,000 | 100% |
| 16 | 100 ms | 158 | 1% |
| 64 | 0 ms | 64,000 | 100% |
| 64 | 100 ms | **634** | **1%** |

**Table a settles the wrong argument.**
The WSGI wrapper, build a fresh `environ`, dispatch, collect the body, costs ~260 ns over the bare handler: a dict, a call, a list. Real, multiply-by-millions real, but *not the budget line*, exactly as Chapter 125's parse was not. Nobody's web service is slow because of WSGI dispatch; the framework tax is nanoseconds and the app's own work (that database call) is milliseconds.

**Table b is the argument, and it is Little's law with no escape.**
Throughput = workers / request_time. When a request spends 100 ms waiting on a database, each worker completes ~10 req/s, so 64 workers cap at 634 req/s *while the CPU sits 99% idle*, capacity you provisioned and cannot spend, because the blocked worker cannot take another request. You buy more throughput only by adding workers, and each worker is a process (memory, Deep L's startup cost) or a thread (the GIL for CPU, though I/O-bound threads scale, Chapter 80), until the machine is full of mostly-sleeping workers. This is the **C10k wall**: ten thousand concurrent slow connections would need ten thousand workers, which no machine affords, and it is precisely the problem Chapter 127's async server solves by putting all the waiting on *one* event loop (Chapter 101) instead of one worker each.

**Book I** does not have this wall because C++ threads are cheap and its gateway is async from the start; the shared system's Python tier ran WSGI behind a worker pool for its admin and reporting endpoints (low concurrency, fine) and moved its high-fanout order-status API to ASGI when the worker count stopped fitting, which is Chapter 127's migration told as an operational fact.

---

## 126.4 Edges and failure modes

**Blocking the worker is the whole failure mode, restated.** §126.3.
Any slow call, a database, an upstream HTTP request, a big file read, holds the worker for its duration. The sync mitigations are all external: more workers, a timeout that frees the worker (returning 504), or moving the slow work to a queue (Deep U) and returning 202 immediately. There is no in-app fix, which is the model's honest limit.

**Bytes, not str, for the body, and the validator will tell you.**
Returning `["pong"]` (str) instead of `[b"pong"]` is the most common WSGI bug; the validator catches it, production servers may not (some coerce, some 500). The str/bytes boundary (Deep D) sits exactly at the response, and the contract chose bytes because the socket takes bytes.

**`start_response` must precede the body and be called once.**
Calling it after yielding body bytes, or twice, or never, violates the two-phase model; the `exc_info` path is the *only* sanctioned way to change status after headers, and only if no body has been sent. Frameworks hide this; hand-written apps and middleware must honour it.

**`wsgi.input` is a stream you read once, up to `CONTENT_LENGTH`.**
Reading more blocks (waiting for bytes that will not come); reading without a length can hang on a kept-alive connection (Chapter 125's framing). Read exactly `CONTENT_LENGTH`, and treat a missing or oversized length as an error, the request-body version of the framing discipline.

**Middleware ordering is semantic.**
An auth middleware must wrap *outside* the app; a gzip middleware *inside* a caching one behaves differently from the reverse (Chapter 128 owns this). The composability that makes middleware powerful also makes order a correctness property, not a preference.

**`wsgiref` is a reference server, not a production one.**
Single-threaded, no timeouts, no hardening, it exists to *define* correct behaviour and to test apps, and the listing uses it for exactly that. Internet-facing WSGI runs behind Gunicorn/uWSGI with worker pools, timeouts, and a reverse proxy, the same "teaching artifact vs hardened server" line Chapter 125 drew.

**And async does not fit.**
An `async def` app is not a WSGI app, the contract has no `await`, no event loop, no way to yield control while waiting. Bolting async onto WSGI (running an event loop inside a sync worker) recreates Chapter 107's bridge with none of its safety; the right answer is a different contract, which is the next chapter.

---

## 126.5 Connections

**Backward.**
The HTTP text this contract wraps, Chapter 125; the socket and stream layer beneath, Chapter 106; the streaming-body shape a generator return enables, Chapter 91; the blocking-worker clause, Chapter 107; the worker-pool concurrency, Deep L and Chapter 80; the interface-standardisation parallel with build backends, Chapter 111.

**Forward.**
ASGI, the async contract that climbs WSGI's ceiling, Chapter 127. Middleware as wrapped callables, the pattern this signature makes free, Chapter 128. Routing the `environ`/`PATH_INFO` into handlers, Chapter 129. The API boundary and content negotiation over these responses, Chapter 130.

**Across books.**
WSGI has no C++ analogue because C++ web servers never had Python's server-app marriage to divorce; the closest parallel is CGI's `environ`, which WSGI modernised in-process. **Book I**'s services are async-native, so this chapter's ceiling is the reason the shared system's Python tier is split, sync WSGI for the simple, low-concurrency admin surface, async for everything that fans out, a split Chapter 127 completes.

---

## 126.6 Exercises

**1. Test without a server.** Write five WSGI apps (routing, redirect, error, streaming body, POST) and a test suite that never opens a socket. Confirm the streaming one returns a generator.

**2. Run the validator against real code.** Wrap a Flask or Bottle app in `wsgiref.validate.validator` and drive it; report any spec violations it finds (there are usually a couple in real apps).

**3. Build middleware.** Implement request-timing middleware (logs duration) and a body-gzip middleware as WSGI wrappers; stack them and show order matters by swapping them.

**4. Measure the real ceiling.** Run a WSGI app under `wsgiref` (or Gunicorn with N workers) where the handler `time.sleep(0.1)`s; drive it with concurrent clients and plot throughput against worker count. Reconcile with §126.3b.

**5. Free a blocked worker.** Add a per-request timeout (via signal or a worker-level config) that returns 504 when the handler exceeds a budget; demonstrate a slow handler no longer pinning a worker forever.

**6. The design question.** WSGI chose a synchronous callable when async did not exist in Python; ASGI later chose an async one. Argue whether a *single* contract could have served both (a callable that may or may not return an awaitable), what that would cost in complexity and in the two-colour problem (Chapter 107), and why the ecosystem chose two clean contracts over one hybrid. Then check how ASGI actually handles sync apps (it wraps them in a thread) and whether that vindicates the split.

---

## 126.7 Summary and cross-references

- **A WSGI app is a callable `app(environ, start_response) -> iterable[bytes]`**: a dict in, a tuple out, testable with no server, which is why the contract won and why every sync framework is a WSGI app underneath.
- **`environ` is Chapter 125's request flattened into a dict**; the server parses the socket into it, the app reads it, and `wsgiref.validate.validator` machine-checks the spec, making the contract enforceable and safely composable.
- **The two-phase design** (`start_response` for status/headers, then a returned iterable for the body) enables streaming generators and header-before-body sending; `exc_info` is the only sanctioned post-headers status change.
- **Dispatch is cheap (~260 ns), throughput is capped**: synchronous means one request holds one worker, so **64 workers cap at 634 req/s at 1% CPU** on 100 ms-I/O requests (Little's law), the C10k wall that no worker count affordably climbs and the reason for Chapter 127's async gateway.
- **The edges are the model's honest limits**: blocking is unfixable in-app, bytes-not-str at the body, `start_response` once and first, read `wsgi.input` to `CONTENT_LENGTH`, middleware order is semantic, `wsgiref` is a reference not a production server, and async does not fit.

**Cross-references.** HTTP the protocol → Chapter 125. Sockets → Chapter 106. Streaming bodies → Chapter 91. The blocking clause → Chapter 107. Worker pools → Deep L, Chapter 80. Interface standardisation → Chapter 111. ASGI → Chapter 127. Middleware → Chapter 128. Routing → Chapter 129.
