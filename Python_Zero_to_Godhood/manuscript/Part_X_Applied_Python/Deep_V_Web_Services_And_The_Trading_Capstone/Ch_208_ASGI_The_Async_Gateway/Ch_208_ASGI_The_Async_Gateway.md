# Chapter 127: ASGI, the Async Gateway

Chapter 126's WSGI callable *returns* its response, so it cannot yield control while it waits, and that single fact was the C10k wall: 64 workers capped at 634 req/s on 100 ms-I/O requests while the CPU sat idle. ASGI replaces the returning callable with an awaiting one that communicates by **messages**: `async def app(scope, receive, send)`, where `scope` describes the connection, `receive()` awaits incoming events, and `send()` emits outgoing ones. Because the app *awaits*, one event loop (Chapter 101) serves thousands of mostly-waiting connections, and the wall is climbed.

The listing keeps WSGI's best property, a test is a function call: `call_app(application, "GET", "/ping")` scripts `receive`/`send` in-process and returns `(200, b'pong')`, no server, no live loop beyond `asyncio.run`. Then it *proves* the concurrency rather than asserting it: two streaming responses driven on one loop interleave as **`A:chunk0, B:chunk0, A:chunk1, B:chunk1, ...`**, because each `send()` sits behind an `await`, so the loop serves both connections at once on one thread.

The benchmark turns that into the number the chapter exists for. Five hundred requests each waiting 20 ms: a 16-worker thread pool takes **743 ms** (serialising the waits), 256 workers reach **60 ms** (at 256 threads of cost), and **one event loop finishes all 500 in 24 ms**, one wait plus overhead, on one thread. And 208.1b confirms the win is not clawed back in per-call overhead, awaiting costs about what returning does. **Choose the gateway by whether requests wait**, Chapter 100's question, arriving at the web.

**This is a Deep V chapter.**
Chapter 126 owns the sync gateway; Chapter 101 (Deep J) owns the loop this rides. This chapter owns ASGI: the message contract, the concurrency it buys, and the one interface that spans HTTP, websockets, and lifespan.

## Section index

- **127.1** The message contract, and concurrency proven
- **127.2** The model: messages generalise where a return cannot
- **127.3** Measurement: the C10k win, and its price
- **127.4** Edges and failure modes
- **127.5** Connections
- **127.6** Exercises
- **127.7** Summary and cross-references

Listings live under `code/ch208/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 127.1 The message contract, and concurrency proven

```python
# code/ch208/l01_asgi_the_async_gateway.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the app is an async callable, still test-is-a-call ---
  GET /ping  -> 200  b'pong'
  POST /echo  -> 200  b'order:buy:100'
  GET /nope  -> 404  b'not found'
  scope in, messages out: an ASGI test is still a function call,
  WSGI's best property kept while the RETURN became a stream of
  send() events - which is the change that buys everything else
--- the request body is events, not a blocking read ---
  receive() is AWAITED, so a slow upload does not pin a worker: the
  loop runs other connections between chunks. this is Chapter 126's
  wsgi.input.read(), turned inside out into something the event
  loop can interleave (Chapter 101)
--- streaming falls out of send(), and concurrency is proven ---
  two streaming responses interleaved on one loop:
    A:chunk0;, B:chunk0;, A:chunk1;, B:chunk1;, A:chunk2;, B:chunk2;
  A and B alternate because each send() sits behind an await, so
  the loop serves both connections at once on ONE thread - the
  C10k wall (Chapter 126) climbed, not by more workers but by
  not blocking the one worker there is
--- one contract, three protocols ---
  scope['type'] is 'http', 'websocket', or 'lifespan': the same
  app object handles request/response, long-lived bidirectional
  sockets, and startup/shutdown, because MESSAGES generalise where
  a return value cannot. WSGI could never express a websocket;
  ASGI expresses it as more receive()/send() of a different type
```

**The in-process calls prove ASGI kept what mattered.**
WSGI's testability, the killer feature of Chapter 126, survives: `scope` in, a scripted `receive`/`send` pair, and the response reconstructed from the `send` events. An ASGI app's unit test is still a function call with a dict, no event loop machinery leaking into the test, which is why the migration from WSGI frameworks to ASGI ones (Django's evolution, Starlette, FastAPI) preserved the testing culture rather than discarding it.

**The interleaving line is the whole thesis, measured live.**
Two streaming responses, one loop, output `A:chunk0, B:chunk0, A:chunk1, ...`: A and B *alternate* because each `send()` is behind an `await asyncio.sleep(0)` that returns control to the loop, which then advances B. This is Chapter 101's determinism producing a *web* result, one thread serving two connections concurrently, and it generalises to two thousand the same way, the concurrency is in the awaiting, not in any pool.

**The request body as events is `wsgi.input` turned inside out.**
WSGI's `wsgi.input.read(length)` blocks the worker until the body arrives; ASGI's `await receive()` yields to the loop between chunks, so a slow upload occupies a *frame*, not a worker. Same information (the body), opposite concurrency: the app that reads a 10 MB upload over a slow link ties up nothing while it waits, which is the upload-heavy service's version of §127.3's table.

**And the last block is the payoff of choosing messages over a return.**
`scope['type']` is `http`, `websocket`, or `lifespan`: one app object, three protocols. A websocket is *more* `receive`/`send` of a different message type; startup/shutdown is the `lifespan` protocol. WSGI's return-a-body shape could never express a bidirectional, long-lived socket, ASGI expresses it as the same contract with different events, which is the deepest reason the industry moved.

---

## 127.2 The model: messages generalise where a return cannot

**A return value is a single answer; a message stream is a conversation.**
WSGI's app answers once (status, headers, body) and is done. ASGI's app participates in an ongoing exchange: it may `receive` many request-body events and `send` many response-body events, in any interleaving the protocol allows. That shape is *strictly more expressive*, request/response is the degenerate case (one `receive`, two `send`s), and websockets, server-sent events, and streaming uploads/downloads are the general case. The cost of the generality is that the app must drive the conversation (loop on `receive`, emit `send`s) rather than compute a value, which is the async ergonomics Chapter 102 taught.

**`scope`, `receive`, `send` map cleanly onto the loop.**
`scope` is the immutable connection description (built once when the connection opens); `receive`/`send` are async callables the server provides, backed by the loop's queues and the socket's transport (Chapter 106). The app never touches the socket, exactly WSGI's decoupling, now async: the server owns the event loop, the transport, and the protocol framing; the app owns the logic and awaits at the boundaries. This is why a single ASGI app runs unchanged under uvicorn, hypercorn, or daphne, the same interface-standardisation win as WSGI (Chapter 126) and PEP 517 (Chapter 111).

**The three protocols share one dispatch.**
`scope['type']` routes: an app checks it and handles `http` (request/response), `websocket` (accept, then receive/send frames until close), or `lifespan` (startup/shutdown, where an app opens its database pool and closes it). Frameworks provide sub-routers per type; the raw contract is one `async def` with a type switch, and the listing's `assert scope["type"] == "http"` is where a real app would branch. Unifying three protocols behind one contract is the architectural achievement, and it is only possible because messages, unlike returns, have a *type*.

**Sync apps run under ASGI via a thread, which vindicates the two-contract split.**
ASGI servers run a WSGI/sync app by executing it in a thread pool (`asgiref`'s `WsgiToAsgi`, `sync_to_async`), Chapter 107's bridge, exactly, so the ecosystem did not have to rewrite every WSGI app to adopt ASGI servers. That the bridge is needed at all is the evidence Chapter 126 predicted: sync and async are different colours (Chapter 102), and the clean answer was two contracts with an explicit bridge, not one hybrid that blurs them.

---

## 127.3 Measurement: the C10k win, and its price

**Methodology.** `code/ch208/bench_c10k.py`.
500 requests each waiting 20 ms; a real thread pool vs a real event loop, both on this machine; `min` of 3; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. 500 requests, each waiting 20 ms:**

| server model | time |
|---|---|
| thread pool, 16 workers | 743 ms |
| thread pool, 64 workers | 195 ms |
| thread pool, 256 workers | 60 ms |
| **one event loop, 500 tasks** | **24 ms** |

**b. Per-call overhead:** return a value 49 ns; await a coroutine 40 ns.

**Table a is Chapter 126's ceiling and Chapter 101's standing army, joined.**
The thread pool finishes in `(N / workers) x wait`: 16 workers serialise 500 waits into ~31 rounds (743 ms), and it takes *256 threads* to approach the loop, at 256 threads' worth of memory and scheduler cost. The single event loop runs all 500 waits *concurrently* and finishes in ~one wait (24 ms), on one thread, because a waiting task is a suspended frame, not a stack (Chapter 101's 1.4 KB-per-waiter table, now serving HTTP). This is the C10k win as an experiment, not a claim: ten thousand slow connections need ten thousand threads (impossible) or one loop (routine).

**Table b closes the escape hatch.**
Awaiting a completed coroutine costs about what returning a value costs, tens of nanoseconds (Chapter 102 measured the await itself at ~37 ns), so ASGI's win is not paid back in per-call overhead. Its real tax is the loop trip on a *genuine* suspension (~27 us, Chapter 102), and 500-fold concurrency dwarfs it. The honest verdict: ASGI is a **rout** for the I/O-bound, many-connection services the web runs, and merely **even** for CPU-bound no-wait handlers, which belong on threads or processes anyway (Deep L, Chapter 100). The gateway question is Chapter 100's exact question, does the work *wait*, applied to the web tier.

**Book I**'s gateway was async from birth for this reason, and its C10k chapter's table is this one with C++ coroutines and smaller constants; the shared system's Python tier runs ASGI for its order-status and market-data endpoints (thousands of concurrent, mostly-waiting clients) and kept sync WSGI only for the low-concurrency admin surface, the split Chapter 126 named and this measurement justifies.

---

## 127.4 Edges and failure modes

**Blocking the loop is fatal here, and worse than under WSGI.** Chapter 107.
A synchronous call (`requests.get`, a blocking DB driver, `time.sleep`) in an ASGI handler stalls *every* connection on the loop, not one worker. The single-threaded win is a single-threaded liability: one blocking handler and the C10k win becomes a C1 stall. The fix is Chapter 107's, `to_thread`/`run_in_executor` for unavoidable sync calls, async-native libraries otherwise, and it is non-negotiable in ASGI in a way it was merely advisable in WSGI.

**`await receive()` must be driven correctly, or the body is lost.**
The body arrives as one or more `http.request` events with `more_body`; reading one and assuming it is complete truncates large uploads. The listing's `while more:` loop is the required shape, and frameworks hide it, but middleware and hand-written apps must honour the event stream (the ASGI analogue of Chapter 126's read-to-`CONTENT_LENGTH`).

**`send` after the response is complete, or out of order, breaks the protocol.**
`http.response.start` must precede `http.response.body`; sending a second `start`, or a body after `more_body: False`, violates the state machine (Chapter 125's framing at the ASGI layer). Servers may error or hang; the two-phase discipline of WSGI's `start_response` is now a message ordering constraint.

**Lifespan errors are startup failures, and they are silent if unhandled.**
The `lifespan` protocol is where an app opens connection pools; an unhandled exception there can leave the server running without its resources (or, correctly configured, refuse to start). Apps must send `lifespan.startup.failed` on failure, and deployments must treat a failed startup as a failed deploy, the operational edge that "it started but nothing works" hides.

**Websocket backpressure is the app's problem.**
A fast producer sending to a slow websocket client fills buffers; `send` awaits, applying backpressure (Chapter 105's queue logic), but an app that ignores the await and floods `send` calls (or spawns unbounded tasks per message) exhausts memory. Long-lived connections need the bounded-fan-out discipline of Chapter 108, per connection.

**Testing async apps needs the loop, but not a server.** §127.1.
The in-process driver is the pattern; the trap is testing with a real server and real sockets (slow, flaky) when scripting `receive`/`send` is deterministic and fast. Frameworks ship test clients that do exactly this; the listing shows the mechanism they wrap.

**And ASGI is not automatically faster.** §127.3.
A CPU-bound handler (image resize, a big computation) on the loop blocks it exactly like a sync call; ASGI helps *waiting*, never *computing*. CPU work goes to an executor (Chapter 107) or a separate service, and a service that is CPU-bound end to end gains nothing from ASGI and pays its complexity, the Chapter 100 verdict, reaffirmed.

---

## 127.5 Connections

**Backward.**
The event loop this rides, and the standing-army memory table it realises, Chapter 101; the await machinery and its cost, Chapter 102; structured concurrency and bounded fan-out per connection, Chapters 104, 108; coordination and backpressure for websockets, Chapter 105; the blocking-bridge for sync calls, Chapter 107; the sync gateway and its ceiling, Chapter 126; the HTTP framing at the message layer, Chapter 125.

**Forward.**
Middleware as wrapped ASGI apps (async onions), Chapter 128. Routing `scope['path']` to handlers, Chapter 129. The API boundary, content negotiation, and serialization over these responses, Chapter 130. The trading service, whose order-status and market-data endpoints are exactly the many-waiting-connections workload ASGI wins, Chapter 131.

**Across books.**
ASGI is Python standardising what **Book I**'s C++ gateway did natively, an async, message-driven server interface, and the two converge on the identical verdict: async for the waiting, offload the computing, and one interface across protocols. The shared system's market-data feed is an ASGI websocket in Book II and a native async socket in Book I, speaking the same events, which is the capstone's seam previewed.

---

## 127.6 Exercises

**1. Prove the interleave.** Extend the listing to three streaming apps and show all three interleaving on one loop; then make one of them block with `time.sleep` and watch it stall the others. Fix with `to_thread`.

**2. Build a websocket echo.** Implement the `scope['type'] == 'websocket'` branch (accept, receive/send frames, close) and drive it in-process with scripted events. Confirm no return value could express it.

**3. Reproduce the C10k table** with real waits and, if you can, real sockets under uvicorn; plot loop-vs-threadpool as N grows to 5,000. Find where the thread pool stops fitting in memory.

**4. Bridge a sync app.** Wrap a WSGI app with `asgiref.WsgiToAsgi`, run it under an ASGI server, and measure the thread-hop cost per request against a native ASGI handler. Relate to Chapter 107.

**5. Backpressure a websocket.** Build a producer that floods a slow consumer; show unbounded `send`/task spawning exhausting memory, then bound it with a per-connection semaphore (Chapter 105/108) and show it holding.

**6. The design question.** ASGI chose messages (`receive`/`send`) over a richer return type (say, an async generator of response parts). Argue the choice: what messages express that a generator cannot (bidirectional websockets, the `lifespan` protocol, `receive` interleaved with `send`), what they cost (the app drives the conversation, more code than `return body`), and why one contract spanning three protocols beat three specialised interfaces. Then check how the ASGI spec versions itself (`scope['asgi']['version']`) and what that buys the ecosystem WSGI lacked.

---

## 127.7 Summary and cross-references

- **ASGI is `async def app(scope, receive, send)`**: messages replace WSGI's return, so the app *awaits* and one event loop serves thousands of waiting connections. Testability survives, a test scripts `receive`/`send` in-process, and concurrency is *proven* by two streams interleaving `A,B,A,B` on one loop.
- **Messages generalise where a return cannot**: `scope['type']` spans `http`, `websocket`, and `lifespan` in one contract; a websocket is more `receive`/`send` of a different type, which WSGI could never express.
- **Measured, the C10k win**: 500 20 ms-waits finish in **24 ms on one loop** vs 743 ms (16 workers) / 60 ms (256 workers) on thread pools; and awaiting costs ~what returning does (49 vs 40 ns), so the win is not paid back in overhead. Choose by whether requests *wait* (Chapter 100).
- **The single thread is the liability too**: one blocking call stalls every connection (Chapter 107 is mandatory here); `receive`/`send` ordering is a state machine; CPU work must go to an executor; and ASGI is a rout for I/O-bound services and merely even for CPU-bound ones.
- **Sync apps run under ASGI via a thread bridge**, which vindicates the two-contract split over one hybrid (Chapter 102's two colours).

**Cross-references.** The loop and standing army → Chapter 101. Await machinery → Chapter 102. Structured concurrency and fan-out → Chapters 104, 108. Backpressure → Chapter 105. The blocking bridge → Chapter 107. The sync gateway → Chapter 126. HTTP framing → Chapter 125. Middleware → Chapter 128. Routing → Chapter 129. The trading service → Chapter 131.
