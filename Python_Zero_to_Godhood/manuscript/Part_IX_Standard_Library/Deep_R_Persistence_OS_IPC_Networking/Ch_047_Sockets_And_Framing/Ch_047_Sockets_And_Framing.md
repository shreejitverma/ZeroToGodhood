# Chapter 47: Sockets and Framing

A service sends three messages over a TCP socket, `sock.sendall(b"HELLO")`, then `b"WORLD"`, then `b"!!!"`,
and the receiver reads them with `sock.recv(4096)` expecting three messages. In testing it works. In
production, under load or across a slower link, `recv` sometimes returns `b"HELLOWORLD!!!"` in one call, and
sometimes `b"HELL"` in one call and the rest in the next, and the protocol falls apart. The bug is a
misconception, not a race: **a stream socket is a stream of bytes, not a sequence of messages.** It
guarantees the bytes arrive in order and complete; it guarantees *nothing* about how they are grouped into
`recv` calls. Three `send`s can coalesce into one `recv`, and one `send` can split across many. If you want
messages, you must **frame** them yourself.

That correctness fact, and its standard fix (length-prefix framing), is the heart of this chapter. Paired
with it is a performance fact that shares a cause with Chapter 40: each `send` of a small buffer is a
syscall, so sending a megabyte in tiny pieces is **~40x slower** than sending it in a few large ones. This
chapter continues **Deep R** with stream sockets, using `socket.socketpair()` (two connected sockets in one
process) so the lessons need no network and run deterministically.

## Section index

- **47.1** A stream has no message boundaries
- **47.2** Framing, and why `recv` can short-read
- **47.3** Measurement: the cost of many small sends
- **47.4** Edges and failure modes
- **47.5** Connections
- **47.6** Exercises
- **47.7** Summary and cross-references

Listings live under `code/ch047/` and are re-executed by `make verify` on both interpreters.

---

## 47.1 A stream has no message boundaries

```python
# code/ch047/l01_sockets.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the problem: message boundaries are NOT preserved ---
  three sends arrived as   : b'HELLOWORLD!!!'
  boundaries preserved?    : False (a stream has none)
--- the fix: length-prefixed framing ---
  framed messages recovered: [b'HELLO', b'WORLD', b'!!!']
  recv_exactly loops until it has the full length (recv can short-read)
```

The first block is the misconception made concrete. Three `sendall` calls (`HELLO`, `WORLD`, `!!!`) arrive,
read to EOF, as the single byte string `b"HELLOWORLD!!!"`. The socket delivered every byte, in order, but
the *boundaries* between the three sends are gone, they were never part of the stream's contract. A protocol
that assumed one `recv` returns one message would here see one giant message, and under different timing
might see a message split down the middle. This is true of TCP and of any `SOCK_STREAM` socket.

The fix is **framing**: encode where each message ends inside the byte stream. The simplest scheme is a
**length prefix**, a fixed-size integer (here a 4-byte big-endian `uint32` via `struct`, Chapter 37) giving
the payload length, followed by exactly that many bytes. The receiver reads the 4-byte length, then reads
exactly that many bytes for the body. With framing, the three messages come back intact as `[b'HELLO',
b'WORLD', b'!!!']`, regardless of how the stream chopped them into `recv` calls.

---

## 47.2 Framing, and why `recv` can short-read

The subtlety that makes framing non-trivial is in `recv_exactly`. `sock.recv(n)` returns *up to* `n` bytes,
but it may return **fewer**, even one, if that is all that has arrived so far, and returns empty (`b""`) only
at EOF. So you cannot write `sock.recv(length)` and assume you got `length` bytes; you must loop, accumulating
until you have exactly the number you need:

```python
def recv_exactly(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed mid-message")
        buf += chunk
    return buf
```

This loop is the counterpart to the boundary problem: just as `send` boundaries are not preserved, a single
`recv` is not guaranteed to fill your request. Both follow from the same stream semantics. The length prefix
tells the receiver *how many* bytes constitute the next message; `recv_exactly` reliably collects that many.
Real protocols elaborate this (a header with type and length, or a delimiter-based framing like newline-
terminated for text protocols), but every stream protocol must solve the framing problem somehow, because
the socket will not solve it for you. `SOCK_DGRAM` (UDP) *does* preserve message boundaries, but at the cost
of reliability and ordering, a different trade, not a way to avoid thinking about messages.

---

## 47.3 Measurement: the cost of many small sends

**Methodology.** `code/ch047/bench_framing.py`. Sending 1 MB over a `socketpair`, as ~15,600 sends of 64
bytes versus ~16 sends of 64 KB, with a background thread draining the receiver so the sender never blocks
(the `join` has a timeout, so it cannot hang). `min` over runs; the benchmark does its own timing because it
needs the draining thread. Socket I/O is OS-bound and noisy. CPython 3.13.5, Apple M3 Pro, macOS 27.0,
arm64.

| send 1 MB | min per run | ratio |
|---|---|---|
| ~16 sends of 64 KB | **~0.5 ms** | 1.00x |
| ~15,600 sends of 64 B | **~20 ms** | **~40x** |

Sending the megabyte in a few large writes takes ~0.5 ms; sending it byte-cluster by byte-cluster takes ~20
ms, about **40x** more. Each `sendall` of a small buffer is at least one `send()` syscall, so the tiny-send
version pays ~15,600 user/kernel crossings where the large-send version pays ~16. This is precisely Chapter
40's file-buffering result on a socket: the per-write syscall dominates, and the fix is the same, batch.

The two lessons combine into one discipline: **build up a full message (framed) and send it in as few large
`sendall` calls as possible; never write a stream socket byte-by-byte or field-by-field.** Assemble the
length prefix and the payload into one buffer and send that, rather than a `send` for the length and a `send`
for each field. (At the TCP layer, Nagle's algorithm coalesces small sends to mitigate this, which is why
latency-sensitive protocols disable it with `TCP_NODELAY`, but relying on the kernel to fix an application
that sends byte-by-byte is a workaround, not a design. `socketpair` here is a Unix-domain socket, so the
figure is pure application/syscall cost without Nagle.)

---

## 47.4 Edges and failure modes

**Assuming one `recv` = one message.** §47.1. A stream has no message boundaries. Frame your messages
(length prefix or delimiter); never assume `recv` returns exactly what one `send` wrote.

**Assuming `recv(n)` returns `n` bytes.** §47.2. It returns *up to* `n`, often fewer. Loop with
`recv_exactly` until you have the full frame, and treat empty as EOF.

**Sending byte-by-byte.** §47.3. A syscall per tiny send is ~40x the batched cost. Assemble the full frame in
one buffer and `sendall` it once.

**`send` vs `sendall`.** Plain `send` may transmit *fewer* bytes than given (returning the count), leaving the
rest unsent; `sendall` loops until all bytes are sent (or it errors). Use `sendall` unless you have a
specific reason to manage partial sends yourself.

**Blocking forever without a timeout.** A `recv` on a peer that never sends, or a `sendall` to a peer that
never reads (filling the buffer), blocks indefinitely. Set `sock.settimeout(...)` (raising `socket.timeout`)
for any socket talking to an untrusted or unreliable peer, and design for the peer that stalls.

**Untrusted length prefixes.** A framed protocol reading a length from the wire must *bound* it: a malicious
peer can send a length of 4 GB and cause the receiver to try to allocate it. Cap the maximum frame size and
reject anything larger before reading the body.

**Forgetting byte order.** The length prefix must use a fixed byte order (`>I` big-endian / network order,
Chapter 37) so a sender and receiver on different-endian machines agree. Native order on the wire is a bug.

---

## 47.5 Connections

**Backward.** The `struct` length prefix and its explicit big-endian byte order are Chapter 37. The per-write
syscall cost and the batch-your-writes fix are Chapter 40, this is that lesson on a socket. The `bytes` that
flow over the socket are Chapter 7 and Chapter 37.

**Forward.** `asyncio` (Chapters 10-11) is the standard way to handle many sockets concurrently without a
thread each, and its streams API provides framing helpers (`readexactly`, `readuntil`) that automate §47.2.
HTTP, TLS, and higher-level protocols build message framing on exactly this foundation, deeper **Deep R** and
application material. UDP's datagram semantics (boundaries preserved, reliability not) are the contrast case.

**Across books.** Stream framing is how Book II speaks to networked services on the way to **Book III**. A
**Book III** client talking to a model server, a vector database, or a message broker frames its requests
(length-prefixed or protocol-defined), reads responses with a `recv_exactly`-style loop, bounds frame sizes
against hostile peers, and batches writes, so the transport is correct under real network timing, not just in
localhost testing. The §47.1 boundary bug is the classic failure that only appears in production, which
**Deep U** exists to design out at the seam.

---

## 47.6 Exercises

**1. Break the boundary assumption.** Reproduce §47.1: send three messages with three `sendall`s and read to
EOF, showing they arrive as one stream. Explain why a protocol that assumed one `recv` per message would
fail, and under what timing it fails intermittently.

**2. Implement framing.** Write `send_msg`/`recv_msg` with a 4-byte length prefix and confirm messages round-
trip intact over a `socketpair`. Then make `recv` return one byte at a time (small reads) and show
`recv_exactly` still reconstructs each message. Explain the short-read loop.

**3. Measure the send cost.** Run §47.3's benchmark and confirm many small sends are far slower than few
large ones. Explain the syscall cost and connect it to Chapter 40's file buffering.

**4. Defend the length prefix.** Add a maximum-frame-size check to `recv_msg` and show it rejects an absurd
length before allocating. Explain why an unbounded length prefix is a denial-of-service vulnerability.

**5. The design question.** TCP provides an ordered, reliable *byte stream* rather than a message service.
Argue why that is the right abstraction for a general transport even though it forces every application to
implement framing. Your answer must address what the stream guarantees and what it deliberately does not, why
UDP's message boundaries are not a free upgrade, and how framing plus batched sends (the two lessons here)
follow from the stream model.

---

## 47.7 Summary and cross-references

- **A stream socket is a byte stream, not a message channel.** Message boundaries are not preserved: multiple
  `send`s can coalesce and one `send` can split across `recv`s.
- **Frame messages yourself,** most simply with a length prefix (a fixed-size `struct` integer, then the
  body). The receiver must loop (`recv_exactly`) because `recv(n)` returns *up to* `n` bytes, often fewer.
- **Measured:** sending 1 MB in ~15,600 small sends is **~40x slower** than in ~16 large ones, a `send()`
  syscall per write, Chapter 40's buffering result on a socket. Assemble a full frame and `sendall` it once.
- **Edges:** use `sendall` (not `send`), set timeouts, bound untrusted length prefixes, and use network byte
  order for the prefix.

**Cross-references.** `struct` and byte order → Chapter 37. Per-write syscalls and batching → Chapter 40.
Bytes and text → Chapters 7 and 37. `asyncio` streams and many-socket concurrency → Chapters 10-11 and the
rest of Deep R. The network seam → Deep U.
