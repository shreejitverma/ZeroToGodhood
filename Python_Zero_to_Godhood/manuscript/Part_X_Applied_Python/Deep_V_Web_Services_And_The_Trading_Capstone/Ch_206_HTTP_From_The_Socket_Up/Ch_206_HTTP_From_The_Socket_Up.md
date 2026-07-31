# Chapter 125: HTTP From the Socket Up

Deep V opens where every web framework bottoms out: a TCP socket (Chapter 106) carrying a text grammar. Strip away Django, FastAPI, and the rest and what remains is startlingly small, a **request is text and a response is text**. The listing speaks the grammar by hand over a real loopback socket, no `http.client`, no framework, so the protocol has nowhere to hide: it sends `GET /ping?n=1 HTTP/1.1` with two headers, and a hand-written server reads until the blank line, parses the request line, and writes back `HTTP/1.1 200 OK` with `Content-Length` and a body. Every framework in existence is that exchange with objects wrapped around it.

The one rule that makes the whole edifice possible is **framing**: a stream has no natural end, so the reader loops `recv` until `\r\n\r\n` for the head, then reads *exactly* `Content-Length` body bytes (or de-chunks a chunked body). Without a declared length, "this response" and "the next response" on a kept-alive connection are indistinguishable, which is why `Content-Length` is mandatory-in-spirit and chunked transfer exists for streaming, Chapter 91's shape at the protocol layer.

The benchmark names the budget line, and it is not what juniors optimise: even on loopback where the handshake is nearly free, a fresh connection per request costs **1.4x** a kept-alive one, a *lower bound* for the real internet where the handshake is a full round trip and TLS adds more. The parse itself is sub-microsecond. **The connection is the cost; the parse never is**, which is the entire reason for keep-alive, connection pools, HTTP/2 multiplexing, and the async server two chapters ahead.

**This is a Deep V chapter, and it opens Deep V.**
Chapter 106 (Deep J) owns the socket and stream layer; Deep O owns the parser's security. This chapter owns HTTP the protocol, the grammar under every gateway.

## Section index

- **125.1** The grammar, spoken by hand
- **125.2** The model: framing, methods, and idempotency
- **125.3** Measurement: the connection is the cost
- **125.4** Edges and failure modes
- **125.5** Connections
- **125.6** Exercises
- **125.7** Summary and cross-references

Listings live under `code/ch206/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 125.1 The grammar, spoken by hand

```python
# code/ch206/l01_http_from_the_socket.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- a request is a text grammar over a socket ---
  request line   : 'GET /ping?n=1 HTTP/1.1'
  header count   : 2
  status line    : 'HTTP/1.1 200 OK'
  response body  : b'pong'
  request line = METHOD SP TARGET SP VERSION; headers are
  Name: value lines; a blank line ends the head. that is the whole
  syntax every framework parses back into request objects
--- the framing rule: a stream has no natural end ---
  the reader looped recv() until \r\n\r\n for the head, then must
  read exactly Content-Length body bytes (or de-chunk a chunked
  body). without a length, 'the response' and 'the next response'
  on a kept-alive connection are indistinguishable - which is why
  Content-Length is mandatory-in-spirit and chunked exists for
  streaming (Chapter 91's shape, at the protocol layer)
```

**The request line and headers are the whole syntax.**
`METHOD SP TARGET SP VERSION`, then `Name: value` lines, then a blank line: three productions a first-year could parse, and every request object your handlers receive is this text lifted into fields. Knowing that collapses the mystery of "what is a request" into "what did the client write on the socket", which is the debugging stance that beats reading framework source.

**The framing rule is the protocol's load-bearing constraint.**
TCP delivers bytes, not messages (Chapter 106, Chapter 119's identical lesson for CSV): the server had to loop `recv` until it saw the head's terminator, then would loop again for a declared body length. This is *why* HTTP has `Content-Length` and chunked encoding at all, and it is the exact seam where the protocol's worst attacks live (§125.4's request smuggling is two parties disagreeing about where a message ends).

**And the response is the request's mirror.**
Status line, headers, blank line, body, the server wrote it as literal bytes, `Content-Length: 4` making `pong` a complete, self-delimiting message that the client could read to its end and stop. The symmetry is the point: client and server speak one grammar in two directions, and a framework is a bidirectional parser-serializer for it.

---

## 125.2 The model: framing, methods, and idempotency

**Framing has exactly two mechanisms, and their disagreement is a vulnerability.**
`Content-Length: N` (read N bytes) or `Transfer-Encoding: chunked` (read size-prefixed chunks until a zero chunk). A message must use one; using both, or letting a proxy and a server interpret them differently, is **request smuggling**, one of the web's sharpest attacks, and the reason RFCs forbid the combination and hardened servers reject ambiguity. Chunked is also the streaming primitive: it lets a server send a response of unknown-in-advance length (a live feed, a large export), Chapter 91's generators reaching the wire.

**Methods are promises about what a repeat does.**
GET is *safe* (no side effects) and *idempotent* (repeating changes nothing beyond once); PUT and DELETE are idempotent but not safe; POST is neither. These are not etiquette, they are contracts the network *relies on*: a proxy or client may retry a GET or PUT after a timeout and must never auto-retry a POST, because a repeated POST might charge a card twice. The trading service two chapters ahead lives on this distinction, order *submission* is POST (retries need idempotency keys), order *status* is GET (retry freely).

**Status classes locate the fault.**
2xx success, 3xx redirection, 4xx *client* error (your request was wrong, do not retry unchanged), 5xx *server* error (my fault, retry may help). The class is machine-actionable: clients back off on 5xx, fix-and-resubmit on 4xx, and follow 3xx, and an API that returns 200 with an error body inside (the "always 200" anti-pattern) has thrown away the one field the network layer understands.

**And headers carry the cross-cutting metadata**, content type (what the body *is*, the negotiation Chapter 130 owns), caching directives, authentication (Chapter 124's tokens), and the framing itself. The header block is the protocol's extension point, which is why it is also, as untrusted attacker-controlled text, an attack surface (§125.4).

---

## 125.3 Measurement: the connection is the cost

**Methodology.** `code/ch206/bench_http_costs.py`.
100 requests over one kept-alive connection vs 100 fresh connections; `min` of 5; parse timed separately; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| shape | per request |
|---|---|
| one kept-alive connection | 48.4 us |
| fresh connection each time | 67.8 us (**1.4x**) |
| parse an 8-header request | 0.93 us |

**The 1.4x is a lower bound, and that framing is the lesson.**
Loopback makes the TCP handshake three packets between two threads on one machine, about as cheap as a connection ever gets, and it *still* costs 40% on top of the request it carries. On a real network the handshake is a full round trip (milliseconds, versus microseconds of compute), and TLS adds one or two more, so the connection dwarfs the request by orders of magnitude. Every connection-level optimisation in HTTP's history, keep-alive (1.1's default), client-side pools, HTTP/2's multiplexing of many requests over one connection, HTTP/3's 0-RTT resumption, attacks *this* number, and none of them touch the parse.

**The parse is sub-microsecond, which settles a common misdirection.**
Splitting an 8-header request into method, target, and a header dict costs 0.93 us, the per-request work a framework does before your handler runs. It is real (multiply by millions of requests and it is a core) but it is *not* the budget line, and "our framework's routing is slow" is almost always "we open a database connection per request" wearing a costume. The async server (Chapter 127) exists to hold *ten thousand connections at once*, not to parse faster, its win is concurrency of waiting, Chapter 101's whole argument.

**Book I**'s trading gateway measured this table with a C++ HTTP parser and reached the identical conclusion in nanoseconds: the parser is a rounding error, the connection and the round trip are the cost, and the architecture (persistent connections, request pipelining, the matching engine reachable without a new socket per order) is designed around that fact, not around parser microseconds.

---

## 125.4 Edges and failure modes

**Request smuggling: `Content-Length` vs `Transfer-Encoding` disagreement.** §125.2.
When a front proxy and a back server frame one byte stream differently, an attacker splices a second request the proxy cannot see, poisoning the next user's response or bypassing auth. The defence is at the protocol layer, reject messages with both headers, reject ambiguous chunking, and never write a framing parser for internet-facing traffic when a hardened one exists.

**Header injection via CRLF.**
An unvalidated `\r\n` in a header *value* (a user-supplied filename in `Content-Disposition`, a redirect URL) injects new headers or splits the response. Anything placed into a response header must have CRLF stripped/rejected, the web's version of Chapter 119's CSV injection, same shape, different delimiter.

**Slowloris and resource exhaustion.**
A client that opens a connection and sends the head one byte per second, never reaching the blank line, ties up a server thread indefinitely; the listing's unbounded `recv`-until-`\r\n\r\n` loop is exactly this vulnerability. Real servers bound header size, header count, and time-to-first-byte, and this is why the listing's server is labelled a teaching artifact, not an internet-facing one.

**`recv` returns arbitrary chunks; boundaries are never guaranteed.**
The head terminator may arrive split across two `recv` calls, or the first `recv` may contain the head *and* part of the body, or several pipelined requests. Every read loop must buffer and search, never assume one `recv` equals one message, Chapter 106's transport lesson, fatal here if forgotten.

**HTTP/2 and /3 are not this grammar.**
The text protocol above is HTTP/1.1; HTTP/2 is binary framed with header compression (HPACK) and multiplexing, HTTP/3 runs over QUIC (UDP). Application semantics, methods, status codes, headers-as-concept, carry over; the wire format does not, and hand-parsing stops working. Frameworks abstract the version; socket-level code must know which it speaks.

**And bytes-versus-text lives at the header/body boundary.**
Headers are ASCII (latin-1 historically, with encoded-word escapes for non-ASCII); the body is bytes whose interpretation the `Content-Type` charset declares (Deep D). Decoding a body without consulting its declared charset, or assuming headers are UTF-8, is the encoding bug class arriving at the protocol, the same lesson Chapter 119 taught for files.

---

## 125.5 Connections

**Backward.**
The socket and stream layer this grammar rides, Chapter 106 (Deep J); the framing lesson shared with delimited text, Chapter 119; the streaming shape chunked encoding realises, Chapter 91; the tokens in `Authorization` headers and their constant-time checks, Chapter 124; the parser-as-attack-surface generalising ReDoS, Chapter 82.

**Forward.**
The synchronous gateway that turns this exchange into a callable, WSGI, Chapter 126; the async gateway that serves ten thousand connections, ASGI, Chapter 127 (built on Chapter 101's loop). Content negotiation and the `Content-Type`/`Accept` dance, Chapter 130; the trading service that speaks this protocol, Chapter 131.

**Across books.**
**Book I**'s gateway parses HTTP/1.1 with a state machine over `string_view` and reaches this chapter's exact budget conclusion (connection, not parse), then moves its hot order path *off* HTTP onto a binary protocol for latency, which is Chapter 84's boundary decision applied to the wire. The shared system speaks HTTP at its edge for interoperability and something leaner at its core for speed, the seam this volume's capstone makes concrete.

---

## 125.6 Exercises

**1. Speak it by telnet.** Connect to a local server with raw `socket` (or `nc`) and type a request by hand; observe the response framing. Then send two pipelined requests on one connection and read both responses.

**2. Break framing.** Send a response with a `Content-Length` larger than the body; watch a client hang waiting for bytes that never come. Then one smaller than the body; watch the leftover corrupt the next response. Explain both from §125.1.

**3. Chunk a stream.** Implement chunked transfer encoding by hand for a response of unknown length (stream 5 chunks with delays); read it with a de-chunking client. Relate to Chapter 91.

**4. Measure the real gap.** Reproduce §125.3 against a server on another machine (or with `tc` adding latency); report the kept-alive-vs-fresh ratio as the round trip grows, and find where it dwarfs the parse.

**5. Slowloris a toy server.** Against the listing's server, open 50 connections that send one header byte per second; show it exhausting capacity, then add a time-to-first-byte bound and show it surviving.

**6. The design question.** HTTP/1.1 is human-readable text; HTTP/2 traded that for binary framing, multiplexing, and header compression. Argue the trade from this chapter's tables: what readability bought (debuggability, `telnet`, this listing), what binary framing bought (the connection-cost attack from §125.3, head-of-line elimination), and why the *semantics* (methods, status, headers) survived the wire-format change intact. Then decide what a from-scratch protocol for the trading capstone's hot path should keep from HTTP and what it should discard (Chapter 84 has the framework).

---

## 125.7 Summary and cross-references

- **A request is text, a response is text**: request line, headers, blank line, body, spoken by hand over a real socket, and every framework is objects wrapped around that exchange.
- **Framing is the load-bearing rule**: a stream has no natural end, so `Content-Length` or chunked encoding delimits messages; their disagreement is request smuggling, and chunked is streaming (Chapter 91) at the wire.
- **Methods and status classes are contracts**: GET/PUT idempotent (retryable), POST not; 4xx your fault, 5xx mine, machine-actionable, and the "always 200" anti-pattern discards the field the network understands.
- **The connection is the cost, not the parse**: measured **1.4x** for fresh-vs-kept-alive on loopback (a lower bound; a real handshake is a round trip), while the parse is **0.93 us**; every HTTP optimisation attacks the connection, and the async server (Chapter 127) is about connection concurrency, not parse speed.
- **The edges are the protocol's security**: smuggling, CRLF header injection, slowloris, chunk-boundary assumptions, HTTP/2-3's different wire, and the header/body encoding boundary, most owned by Deep O, all rooted in "parsing untrusted protocol text".

**Cross-references.** Sockets and streams → Chapter 106. Framing shared with CSV → Chapter 119. Chunked as streaming → Chapter 91. Auth tokens → Chapter 124. Parser security → Chapter 82. WSGI → Chapter 126. ASGI → Chapter 127. Content negotiation → Chapter 130. The trading service → Chapter 131.
