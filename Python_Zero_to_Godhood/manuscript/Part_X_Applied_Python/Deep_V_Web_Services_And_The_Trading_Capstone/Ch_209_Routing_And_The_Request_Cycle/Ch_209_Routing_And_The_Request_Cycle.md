# Chapter 128: Routing and the Request Cycle

The gateway (WSGI or ASGI) hands your code a method and a path; *something* must map `GET /orders/42` to the right function with `order_id=42` extracted and typed. That something is a **router**, and this chapter builds one, because every framework's router is one of two designs and knowing which you hold is knowing your service's behaviour at the edges.

The listing builds the design most frameworks actually ship, a **linear list of compiled patterns tried in order**, with typed path parameters: `{order_id:int}` both *matches* only digits and *converts* the captured string to an `int` before the handler sees it, so **routing is the first layer of validation**. It then draws the three decisions a router makes that shape an API. **The two failure modes are different status codes**: `GET /orders/abc` is 404 (the int route did not match, so no such path), `POST /orders/42` is 405 (the path exists, the verb is not registered), and conflating them hides a client bug the status class was designed to name (Chapter 125). **Match order is a decision**: the literal `/orders/new` beats the parametric `/orders/{order_id}` only because it was registered first, static-before-dynamic. And **the linear-vs-trie choice is a cost model**.

The benchmark settles that last one: dispatching against 10/100/1,000 routes, the linear scan's worst case grows **589 → 5,103 → 51,314 ns** while a segment trie stays flat at **~230 ns**. The trie is asymptotically better and *practically irrelevant*, at the tens of routes real services have, linear is already sub-microsecond against a database query a thousand times longer, which is Chapter 168's complexity-beats-constants argument with the web's usual verdict that the constants never start to matter.

**This is a Deep V chapter.**
Chapters 126-127 own the gateways that feed the router; Chapter 130 owns what the handler returns. This chapter owns the dispatch: paths to handlers, params, and status semantics.

## Section index

- **128.1** Dispatch, params, and the status decisions
- **128.2** The model: linear lists, tries, and match order
- **128.3** Measurement: the crossover that does not matter
- **128.4** Edges and failure modes
- **128.5** Connections
- **128.6** Exercises
- **128.7** Summary and cross-references

Listings live under `code/ch209/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 128.1 Dispatch, params, and the status decisions

```python
# code/ch209/l01_routing.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- dispatch: method + path -> handler + extracted params ---
  GET    /orders/42             -> 200  order 42 (int int)
  DELETE /orders/42             -> 200  cancelled 42
  GET    /users/alice/orders    -> 200  orders for alice
  GET    /health                -> 200  ok
  {order_id:int} both MATCHES only digits and CONVERTS the string
  to an int before your handler sees it - routing is the first
  layer of validation, and typed params are the cheapest kind
--- the two failure modes are different status codes ---
  GET /orders/abc  -> 404  (int route did not match 'abc' -> no path -> 404)
  POST /orders/42  -> 405  (path exists, POST not registered -> 405)
  GET /nope        -> 404  (no such path -> 404)
  404 = 'no such resource', 405 = 'that resource, wrong verb':
  conflating them (returning 404 for a bad method) hides a client
  bug the status class was designed to name (Chapter 125)
--- match order is a decision, not an accident ---
  GET /orders/new  -> 'the new-order form'
  the LITERAL route was registered first, so it wins over the
  parameter route - reverse the order and '/orders/new' becomes
  order_id='new'. static-before-dynamic is the rule every router
  needs, whether by registration order (here) or by trie priority
```

**Typed parameters make routing the first validator.**
`{order_id:int}` compiles to `(?P<order_id>[0-9]+)` *and* records `int` as the converter, so a handler declared `def handler(order_id: int)` receives an actual `int`, never a string to re-parse and re-validate. The pattern is the whole value: invalid inputs (`/orders/abc`) never reach the handler, and the handler's signature is honest about what it gets. Frameworks extend this to UUIDs, slugs, and custom converters, but the mechanism is the listing's, match-and-convert in one step, and it is the cheapest validation in the stack.

**404 versus 405 is the status decision that separates careful APIs from lazy ones.**
The router distinguishes "no route matched this path at all" (404) from "a route matched the path but not the method" (405), by tracking whether *any* route's path matched before checking the verb. The distinction is machine-actionable (Chapter 125): a client seeing 405 knows the resource exists and its request shape is wrong; a client seeing 404 knows the URL is wrong. The lazy `return 404 for everything not matched` throws that away, and it is the single most common status bug in hand-rolled routers.

**Match order encodes intent, and getting it wrong is silent.**
`/orders/new` and `/orders/{order_id}` both match `/orders/new`; the literal wins because it is registered first. Reverse the registration and the form URL becomes `order_id='new'`, a bug that produces no error, just wrong behaviour. Static-before-dynamic is the universal rule, and routers enforce it either by registration order (linear, the listing) or by trie node priority (§128.2), a router that leaves it to chance has a latent bug per overlapping route.

---

## 128.2 The model: linear lists, tries, and match order

**The linear router is a list of compiled patterns, tried until one matches.**
Each route is a regex (from the `{name:type}` template) plus a handler and its converters; dispatch walks the list, and the first match wins. Its cost is O(routes) worst case (§128.3), its virtue is *transparency*, the match order is the registration order, overlaps resolve by position, and debugging is reading a list top to bottom. This is why Flask, Bottle, and most frameworks ship it (Django's is a lightly-structured variant), routes are few and the model is legible.

**The trie routes on path *structure*, not on trying patterns.**
A segment trie stores routes as a tree keyed by path segment (`/orders/{id}` becomes `orders -> :id -> handler`), and dispatch walks the *request's* segments down the tree, O(segments) regardless of table size. It wins asymptotically (§128.3) and costs legibility, match order becomes node-priority rules (static children before parametric before wildcard), which the router must define and the developer must learn. High-scale routers (Go's httprouter, some CDN edge routers) are tries because their route counts and request rates justify the complexity; almost nothing else needs it.

**Match order is the model's one genuinely subtle property.**
In the linear router it is registration order (the developer's responsibility); in the trie it is a fixed priority (static > parametric > wildcard) the router enforces. Either way, overlapping routes have a defined winner, and the failure mode of *undefined* order (whichever route the dict happened to iterate first) is the nondeterministic-routing bug that dict-ordering changes once surfaced across Python versions. A router without a defined match order is not a router; it is a guess.

**Routing is one stage of a cycle the next chapters complete.**
The full request cycle is: gateway parses the socket into `environ`/`scope` (126-127); middleware wraps the app (128, next chapter); the router dispatches to a handler (here); the handler produces a response (130); middleware post-processes; the gateway serializes to the socket. Routing sits in the middle, the first place *your* code's structure appears, and its decisions (params, status, order) are the API's contract with its clients.

---

## 128.3 Measurement: the crossover that does not matter

**Methodology.** `code/ch209/bench_routing_scaling.py`.
Worst-case dispatch (matches the last route) against tables of 10/100/1,000 routes; `min` of 7; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| routes | linear | trie |
|---|---|---|
| 10 | 589 ns | 229 ns |
| 100 | 5,103 ns | 234 ns |
| 1,000 | 51,314 ns | **237 ns** |

**The shapes are textbook, and the conclusion is counterintuitive.**
Linear is O(routes), it may try every regex, so it grows tenfold per tenfold of table; the trie is O(segments), flat at ~230 ns because it decides on the path's own structure. Chapter 87's exponent, exactly. And yet the *engineering* answer is "ship linear", because the small-N row is the one that governs: at 10-50 routes (the real range), linear is sub-microsecond, and a service that routes and then queries a database spends milliseconds on the query, a thousandfold more than any router. The trie's win is real and dormant.

**This is Chapter 168's argument arriving at the web, with the web's twist.**
"Complexity beats constants" is true, and here it is *irrelevant*, because the constants stop mattering before the complexity starts helping. The trie pays for itself only when routes reach the hundreds *and* routing is a measured hot path (Chapter 86), a conjunction that for a database-backed service is essentially never. So the discipline is Deep K's, verbatim: measure before optimising the router, and discover it was never the bottleneck. The frameworks that ship linear routers made this measurement once, for everyone.

**Book I**'s gateway uses a trie because its route table is large (every instrument, every endpoint) *and* its request rate makes routing a real cost, the conjunction Python services lack, so it correctly pays the trie's complexity. The shared system's Python tier ships a linear router and spends its time in the database and the matching-engine call, which is where a profile (Chapter 86) says the time actually goes, the cross-book lesson that the right data structure is a function of the measured workload, not of asymptotic taste.

---

## 128.4 Edges and failure modes

**Regex path params can ReDoS.** Chapter 82.
A greedy or nested-quantifier converter (`{path:.*}` combined with more segments, or a hand-written pattern with catastrophic backtracking) turns a crafted URL into a hang. Path converters should be anchored, simple, and non-overlapping; the `[^/]+` and `[0-9]+` of the listing are safe by construction, and custom converters are exactly where Chapter 82's discipline applies.

**Trailing slashes are two URLs unless you decide otherwise.**
`/orders` and `/orders/` are distinct paths; a router that matches one and not the other, or redirects inconsistently, produces "works with the slash, 404 without" bugs. Pick a policy (redirect, match both, or strict) and apply it uniformly; frameworks differ, and the mismatch surfaces at integration.

**URL-decoding happens before routing, and its edges bite.**
`%2F` (encoded slash) in a path segment, unicode normalisation, and case are all decisions made before the router sees the path; a segment that decodes to contain a `/` can smuggle past segment-based matching. Decode once, canonically, and route on the result, the encoding lesson (Deep D) at the URL.

**Match order bugs are silent, and tests must cover overlaps.** §128.1.
Every pair of overlapping routes has a winner that a test should pin; the `/orders/new` vs `/orders/{id}` case is the archetype, and a router change (reordering, adding a route) can flip it without any error. Overlap tests are the routing equivalent of Chapter 99's race tests, the bug is in the ordering, not the logic.

**405 requires knowing all methods for a path.**
Returning a correct 405 (and the `Allow` header listing permitted methods, which the spec requires) means the router must know *which* verbs a path supports, not just fail the current one. The listing tracks path-matched-but-method-wrong; a production router populates `Allow`, and omitting it is a spec violation clients notice.

**Routing is not authorization.**
Matching a route says the URL is *shaped* right, never that the caller may access it; auth is a separate layer (middleware, Chapter 128's next chapter, or the handler). Conflating "the route matched" with "the request is allowed" is a class of access-control bug, and the 404-vs-403-vs-401 distinction (hide existence, or reveal it and deny) is a security decision the router does not make.

**And the hot-path temptation is a profiler question.**
"Our routing is slow" is almost always false (§128.3); before replacing a linear router with a trie, profile (Chapter 86) and confirm routing is the cost, which it will not be for any service that touches I/O. Optimising the router of a database-backed service is optimising the 0.1%.

---

## 128.5 Connections

**Backward.**
The method and path the router dispatches, parsed by the gateways of Chapters 126-127 from the HTTP of Chapter 125; the status classes 404/405 encode, Chapter 125; the regex engine compiling path templates, Chapter 117, and its ReDoS edge, Chapter 82; the complexity-vs-constants argument the linear/trie table instances, Chapter 168; the profile-before-optimising discipline, Chapter 86.

**Forward.**
Middleware wrapping the router into the request cycle, Chapter 128's continuation into the onion. The handler's return, serialization, and content negotiation, Chapter 130. The trading service's routes (`POST /orders`, `GET /orders/{id}`, the market-data websocket), Chapter 131, where routing meets the idempotency and status semantics of a real API.

**Across books.**
**Book I** routes with a trie for measured reasons and this chapter routes with a list for measured reasons, and both are correct because both measured; the shared system's two tiers ship different routers for their different workloads, which is the volume's recurring lesson that architecture is a function of the profile, not the fashion.

---

## 128.6 Exercises

**1. Add converters.** Extend the router with `uuid` and `slug` converters (match-and-convert); test that invalid inputs 404 before the handler and valid ones arrive typed.

**2. Populate `Allow`.** Fix the 405 path to return the `Allow` header listing all methods registered for the matched path; test with a path supporting GET and DELETE.

**3. Build the trie.** Implement a segment trie with static-before-parametric priority; port the listing's routes to it and verify identical dispatch, including the `/orders/new` overlap.

**4. Overlap test suite.** For a real API's routes, write tests pinning the winner of every overlapping pair; then reorder a route and watch a test fail, proving the coverage.

**5. Profile the router.** In a real (or realistic) service, profile a request end to end (Chapter 86) and report routing's share of the total. Then compute how large the route table would need to grow for a trie to matter.

**6. The design question.** Frameworks split on whether path converters run *type* validation (int, uuid) at the routing layer or defer all validation to the handler/schema (Chapter 130). Argue the split: what routing-layer typing buys (early 404s, honest handler signatures, the listing's win), what it costs (validation logic in two places, converter-vs-schema drift), and where the boundary should sit for a service whose real validation is a rich schema. Then check how FastAPI unifies them (path params validated by the same Pydantic layer as bodies) and whether that resolves the split or relocates it.

---

## 128.7 Summary and cross-references

- **A router maps method+path to a handler with typed params**: `{order_id:int}` matches only digits and converts before the handler sees it, so **routing is the first validator** and typed params are the cheapest kind.
- **The status decisions are the API's honesty**: 404 (no such path) vs 405 (path exists, wrong verb, with an `Allow` header), never conflated; and **match order is a decision** (static-before-dynamic), silent when wrong, so overlaps need tests.
- **Two designs, one cost model**: linear list (O(routes), transparent, what most frameworks ship) vs segment trie (O(segments), fast, complex); measured **589 → 51,314 ns** for linear across 10-1,000 routes against a **flat ~230 ns** trie.
- **The crossover does not matter**: at real route counts (tens) linear is sub-microsecond against a millisecond database query, so ship linear and profile before ever reaching for a trie, Chapter 168's argument with the web's verdict that the constants never start to bite.
- **The edges**: converter ReDoS, trailing slashes, URL-decoding smuggling, silent overlap bugs, the `Allow` header, and the firm line that routing is not authorization.

**Cross-references.** The gateways → Chapters 126-127. HTTP and status classes → Chapter 125. Regex and ReDoS → Chapters 117, 82. Complexity vs constants → Chapter 168. Profiling → Chapter 86. Serialization and the handler's return → Chapter 130. The trading service → Chapter 131.
