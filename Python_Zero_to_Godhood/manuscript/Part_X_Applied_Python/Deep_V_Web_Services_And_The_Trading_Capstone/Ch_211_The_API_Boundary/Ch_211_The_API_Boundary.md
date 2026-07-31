# Chapter 130: The API Boundary

Between the router (Chapter 128) and the handler lies the boundary where untrusted bytes become trusted objects, and back. Four jobs live here, and skipping any one is a class of bug: **parse** the body into structure, **validate** that structure against a schema (untrusted input is guilty until proven), then on the way out **negotiate** the content type the client asked for and **serialize** to it, with **errors themselves being valid, machine-readable responses**, never leaked stack traces.

The listing implements an honest boundary over stdlib `json`. The happy path turns `{"symbol":"ACME","side":"buy","qty":100}` into a validated object the handler trusts, `the handler never sees an unvalidated field`. Bad JSON is a **400 with a reason**; a schema violation is a **422 with field-level errors** (`{"symbol":"required non-empty string","side":"must be 'buy' or 'sell'","qty":"must be a positive integer"}`), so a client can *fix* the request from the response, because "validation failed" with no detail is the API equivalent of a bare `except`, true and useless. And content negotiation renders one resource three ways: `Accept: application/json` and `text/plain` both 200, `application/xml` a **406, not a guess**.

The benchmark attributes the cost: `json.loads` and `json.dumps` are microseconds (C, Chapter 42), the trivial validation is cheaper still (110 ns), and parsing is linear in size (4.8 → 416 us across 1-100 KB). Two lessons follow, validation is what scales with schema richness (hence pydantic and its Rust core), and the parser's faithfulness is the attack (a body-size limit is a *security* control, not an optimisation).

**This is a Deep V chapter.**
Chapter 42 (Deep R) owns JSON the format; Chapter 128 owns routing's first-pass validation. This chapter owns the deep boundary: parse, validate, negotiate, serialize, and errors-as-responses.

## Section index

- **130.1** The four jobs, demonstrated
- **130.2** The model: trust boundary, representations, and errors-as-data
- **130.3** Measurement: cheap parse, scaling validation, the size attack
- **130.4** Edges and failure modes
- **130.5** Connections
- **130.6** Exercises
- **130.7** Summary and cross-references

Listings live under `code/ch211/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 130.1 The four jobs, demonstrated

```python
# code/ch211/l01_the_api_boundary.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the happy path: parse, validate, serialize ---
  200 application/json
  {"accepted":{"symbol":"ACME","side":"buy","qty":100},"order_id":1001}
  untrusted bytes -> validated object -> handler -> json out. the
  handler never sees an unvalidated field, which is the boundary's
  whole job (Chapter 128's routing was the first check; this is the
  deep one)
--- bad JSON is a 400, with a reason ---
  400 : {"error":"invalid JSON","detail":"Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"}
--- a schema violation is a 422, with FIELD-LEVEL errors ---
  422 : {"error":"validation failed","fields":{"symbol":"required non-empty string","side":"must be 'buy' or 'sell'","qty":"must be a positive integer"}}
  every bad field is named with why: a client can FIX the request
  from the response. 'validation failed' with no detail is the
  API equivalent of a bare except - true and useless
--- content negotiation: the client asks, the server chooses ---
  Accept: application/json   -> 200 application/json  b'{"accepted":{"symbol":"ACME","side":"buy'
  Accept: text/plain         -> 200 text/plain  b"{'accepted': {'symbol': 'ACME', 'side': "
  Accept: application/xml    -> 406 text/plain  b'not acceptable'
  the same resource, rendered per the client's Accept header; a
  type the server cannot produce is a 406, not a guess. one
  handler, many representations - the REST idea made concrete
```

**Parse-then-validate is the trust boundary, and the order is load-bearing.**
`json.loads` can fail (malformed input, a 400 with the parser's own message); only *structurally valid* JSON reaches validation, which checks *semantics* (types, required fields, ranges) and returns a typed object or field-level errors. The handler receives `{"symbol": str, "side": str, "qty": int}` with every field checked, so its code is honest about what it has and never re-validates. This is the boundary's whole purpose: **untrusted bytes in, trusted objects out**, and the handler lives entirely on the trusted side.

**Field-level errors are the difference between a usable API and a frustrating one.**
The 422 names each bad field *and why*, so a client, or a developer, can correct the request without guessing. This is Chapter 122's avalanche lesson inverted: where a hash must reveal nothing about its input, an error must reveal everything about *the client's* input (never about the server's internals, §130.4). A validation response that says only "failed" forces trial-and-error debugging against a black box; the field map is the API's respect for its callers.

**Content negotiation makes one resource many representations.**
`Accept: application/json` gets JSON, `text/plain` gets a text rendering, `application/xml` gets a **406 Not Acceptable**, a refusal, not a wrong guess. This is REST's uniform-interface idea made concrete: the resource (an accepted order) is abstract, and its *representation* is chosen per request. Most APIs support one type and skip this, but the mechanism is why the same endpoint can serve a browser (HTML), a CLI (JSON), and a legacy client (XML) without three handlers.

**And errors are responses, which the last block states as a contract.**
In: bytes to parse (400) to validate (422) to a trusted object. Out: object to negotiate (406) to serialize to bytes with the right `Content-Type`. Errors carry a status class (Chapter 125) and a machine-readable body, never a leaked traceback, Chapter 124's don't-reveal-internals meeting Chapter 129's outermost error middleware. An API whose errors are HTML stack traces has a security bug (information disclosure) and a usability bug (unparseable by clients) in one.

---

## 130.2 The model: trust boundary, representations, and errors-as-data

**The boundary is where "untrusted" ends, and it must be a wall, not a fence.**
Everything outside, the request body, query params, headers, is attacker-controlled; everything the handler touches must have crossed a validation gate. The gate's job is *total*: reject anything not conforming, with no "probably fine" paths, because the one unvalidated field is the injection, the type confusion, the overflow. This is Chapter 124's "authenticate before you act" generalised to "validate before you trust", and the two compose (auth in middleware, Chapter 129; validation at the boundary, here).

**Validation is a schema, and schemas want to be declarative.**
The listing validates by hand for transparency, but the pattern begs for declaration: a schema (types, constraints, relationships) that a library *compiles* into a validator, so the rules are data, not code. This is what pydantic, marshmallow, and JSON Schema provide, and why pydantic's v2 moved its core to Rust (validation is per-request hot path, §130.3), the declarative schema is easier to write, read, and keep in sync with documentation, and the compiled validator is faster than interpreted checks. The hand-written version teaches the mechanism; production uses the compiled one.

**Representations are chosen, not fixed, and negotiation is the mechanism.**
The `Accept` header (and `Content-Type` for the request body) drives which serializer runs. Real negotiation handles quality values (`Accept: application/json;q=0.9, text/html;q=1.0`), wildcards, and charset, and picks the best mutually-available type. The principle is separation: the handler produces an abstract result, the boundary renders it, so adding a format (CSV export, protobuf) is a new serializer, not a new handler, the same decoupling as the gateway (Chapters 126-127) one layer up.

**Errors are part of the API surface, designed like the success responses.**
A good API has an *error schema* (a consistent shape: a code, a human message, machine-readable details) so clients can handle failures programmatically. RFC 7807 (`application/problem+json`) standardises this; the listing's `{"error": ..., "fields": ...}` is a minimal version. Errors-as-data means: a status class the network understands (Chapter 125), a body the client can parse, and *nothing* about server internals. This is where Chapter 124's secrecy discipline, Chapter 125's status semantics, and Chapter 129's error middleware converge into one design surface.

---

## 130.3 Measurement: cheap parse, scaling validation, the size attack

**Methodology.** `code/ch211/bench_boundary_costs.py`.
`min` of 15 (fewer for large parses); 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. The round trip on a small order:**

| job | time |
|---|---|
| `json.loads` (parse) | 739.7 ns |
| `validate` (schema, trivial) | 110.2 ns |
| `json.dumps` (serialize) | 1,033.1 ns |

**b. Parse cost vs payload size:**

| body | time |
|---|---|
| ~1 KB | 4.8 us |
| ~10 KB | 42.0 us (8.7x) |
| ~100 KB | **416.4 us (86x)** |

**Table a locates the boundary's cost, and it is not where juniors look.**
Parse and serialize are C (`json`, Chapter 42), microseconds on a small object; the *trivial* validation is cheaper still. But the word "trivial" is the caveat: this schema checks three fields with simple rules. Real schemas, nested objects, dozens of fields, cross-field constraints (if `side` is `sell`, `qty` must not exceed holdings), custom types, make **validation the dominant boundary cost**, which is exactly why schema libraries exist and why pydantic v2 compiled its core to Rust. The boundary's budget scales with the *schema*, not the parser.

**Table b is linear and cheap, which sets up the security point.**
Parsing is O(bytes), ~86x for 100x the size, so a normal body (a few KB) is free. But that faithfulness is the attack: the parser will *happily* allocate a gigabyte of objects for a gigabyte of JSON, and a nested-array bomb can amplify further. A **body-size limit at the boundary is a security control** (Chapter 125's bounded reads), not a performance tweak, an unbounded parser is a memory-and-CPU denial of service the attacker triggers with one large request. The limit belongs *outside* the parse (reject on `Content-Length` before reading), the request-body version of Chapter 129's short-circuit.

**Book I**'s services validate against compiled schemas (its own or a code-generated one from a protobuf/IDL) for the same reason, hand-written validation does not scale in maintainability or speed, and its security chapter cites the identical size-limit-as-DoS-control. The shared system validates every order against a schema at its boundary and caps body size at its edge, so a malformed or oversized order is rejected before it can allocate or reach the matching engine, Chapter 84's boundary discipline and Chapter 129's onion meeting at the API surface.

---

## 130.4 Edges and failure modes

**Error responses must not leak internals.** §130.1.
A 500 with a Python traceback exposes file paths, library versions, and sometimes secrets (a connection string in an exception message), a real information-disclosure vulnerability. The outermost error middleware (Chapter 129) catches everything, logs the detail server-side with a request id, and returns a generic 500 with no internals, Chapter 124's discipline at the response.

**Validation must reject unknown fields, or accept silent typos.**
A schema that ignores extra fields accepts `{"quantity": 100}` (a typo for `qty`) as a valid order with a *default* qty, a silent bug. Strict validation (reject unknown keys) catches client mistakes; lenient validation hides them. The choice is a policy, and "ignore unknowns" is the default that ships bugs.

**Type confusion at the JSON boundary is subtle.**
JSON has no integer/float distinction some clients respect (`qty: 100.0`), booleans are a subtype of int in Python (`isinstance(True, int)` is True, the listing guards it explicitly), and large integers, precise decimals (money!), and dates are all `str`-or-lose-precision decisions. The `qty` validation's `isinstance(qty, bool)` check is not paranoia, it is the boundary catching `{"qty": true}` before it becomes `qty == 1`.

**Content negotiation ignored is content negotiation done badly.**
Serving JSON regardless of `Accept` "works" until a client sends `Accept: application/xml` and needs a 406, or a browser sends `Accept: text/html` and gets JSON it renders as text. Most APIs pick one type and document it (fine), but *silently* ignoring `Accept` while claiming to honour it is the bug, decide, and return 406 when you cannot satisfy.

**Serialization can fail on the way out.**
An object the handler produces may not be JSON-serializable (a `datetime`, a `Decimal`, a custom class); `json.dumps` raises, and if that happens *after* a 200 status is committed, the response is broken mid-flight (Chapter 125's headers-already-sent problem). Serialize *before* committing the status, or use a serializer that handles your types (a `default=` function), the boundary's own error path.

**Validation and documentation drift.**
Hand-written validation and API docs diverge the moment one changes without the other; a client reads docs that no longer match the validator and sends "valid" requests that 422. Schema-first tools generate docs *from* the schema (OpenAPI from pydantic), keeping them in sync by construction, the maintainability argument for declarative schemas, beyond speed.

**And the free-threaded note: validators should be stateless.**
A validator holding per-request state in module scope (a shared error list, a cached parse) is a concurrency bug under threads and worse under the free-threaded build (Chapter 96). Validators are pure functions of their input, or explicitly synchronised, exactly like middleware (Chapter 129).

---

## 130.5 Connections

**Backward.**
JSON the format and its C parser, Chapter 42; the status classes errors carry, Chapter 125; the don't-reveal-internals discipline, Chapter 124; the outermost error middleware that catches handler exceptions, Chapter 129; routing's first-pass validation, Chapter 128; the body-size-limit-as-bounded-read, Chapter 125; free-threaded statelessness, Chapter 96.

**Forward.**
The trading service whose order boundary validates every submission and whose errors are designed responses, Chapter 131; the capstone where the whole cycle, gateway, middleware, router, boundary, handler, runs end to end, Chapter 132.

**Across books.**
**Book I** validates against compiled schemas (often generated from a shared IDL the two books use) and designs its error responses as data, and the shared system's order schema is *the same schema* on both sides, so an order rejected by Book II's boundary would be rejected identically by Book I's, the cross-book contract this volume's capstone makes literal.

---

## 130.6 Exercises

**1. Strict vs lenient.** Add unknown-field rejection to the validator; show `{"quantity": 100}` (typo) being caught strictly and silently accepted leniently. Decide your default and defend it.

**2. Design an error schema.** Adopt RFC 7807 (`problem+json`): a type URI, title, status, detail, and field errors. Rewrite the listing's errors to it and validate a client can handle every failure programmatically.

**3. Money at the boundary.** Add a `price` field that must be a decimal with two places; show JSON's float imprecision corrupting it and fix with a string-decimal representation (Chapter 35). This is the finance-specific type-confusion edge.

**4. Real negotiation.** Implement quality-value parsing (`Accept: application/json;q=0.9, text/plain;q=1.0`) and pick the highest-q available type; test the tie-breaks and the 406 path.

**5. Size-limit the boundary.** Add a `Content-Length` check that rejects oversized bodies with 413 *before* parsing; demonstrate a 100 MB body rejected in constant time instead of allocated. Reconcile with §130.3b.

**6. The design question.** Hand-written validation is transparent and drifts from docs; schema libraries (pydantic) are declarative, fast (compiled), and doc-generating, but add a dependency and a DSL. Argue where the line sits for a service: what a stdlib-only boundary buys (no dependency, full control, the listing) versus what a schema library buys (speed at scale, OpenAPI generation, ecosystem), and how the free-threaded build's shared-state rules (Chapter 96) interact with a library's global schema registry. Then check how pydantic v2's Rust core changed the performance half of this argument.

---

## 130.7 Summary and cross-references

- **The boundary has four jobs**: parse (400 on garbage), validate against a schema (422 with **field-level errors** a client can fix), negotiate the content type (406 when impossible), and serialize, with the handler living entirely on the trusted side, never seeing an unvalidated field.
- **Errors are designed responses, not leaked tracebacks**: a status class (Chapter 125) plus a machine-readable body, with server internals hidden (Chapter 124) and handler exceptions caught by the outermost middleware (Chapter 129).
- **Content negotiation makes one resource many representations**, chosen by `Accept`, with a 406 refusal rather than a wrong guess, REST's uniform interface concrete.
- **Measured**: parse/serialize are C-microseconds; *trivial* validation is cheaper (110 ns) but **validation scales with schema richness** (hence compiled schema libraries); parse is linear (4.8 → 416 us over 1-100 KB), so a **body-size limit is a security control**, an unbounded parser is a DoS the attacker triggers with one large request.
- **The edges**: hide internals in errors, reject unknown fields, guard JSON type confusion (`bool` is an `int`, floats lose money), honour `Accept` or 406, serialize before committing status, keep schema and docs in sync, and keep validators stateless.

**Cross-references.** JSON → Chapter 42. Status classes → Chapter 125. Don't-reveal-internals → Chapter 124. Error middleware → Chapter 129. Routing's first check → Chapter 128. Bounded reads → Chapter 125. Free-threaded statelessness → Chapter 96. The trading service → Chapter 131. The capstone → Chapter 132.
