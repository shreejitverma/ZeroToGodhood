# Chapter 106: The I/O Layer

Chapter 101 put a selector at step 2 of the loop and moved on. This chapter is the stack that turns "file descriptor 7 is readable" into `line = await reader.readline()`, three layers in one cake: the **selector** reports readiness; **transports and protocols** turn readiness into callbacks, with chunk boundaries decided by the kernel; and **streams** turn callbacks back into awaitables with framing and backpressure built in.

The listing exercises all three over real loopback sockets and prints only chunking-independent facts, which is the first lesson wearing the book's own methodology: *the number of `data_received` calls per write is not printable in a verified book*, because TCP does not preserve write boundaries, and any code that assumes it does is already wrong.

The benchmark then prices the cake where the prices are visible, loopback, which runs at memory speed and hides nothing: the full asyncio stack costs about **3x** raw blocking sockets on bulk throughput and **3.4x** on concurrency-one latency; and the read-size sweep recovers a factor of **2.4** inside the stack itself, because every short read is a potential loop trip (Chapter 102's 27 us unit) and `read(256 KB)` amortises what `read(1 KB)` pays per kilobyte. On a real network the wire dominates and the taxes vanish into it; the sweep's lesson survives every network.

**This is a Deep J chapter.**
Deep R owns sockets and the OS interfaces beneath; Chapter 101 owns the loop's polling step. This chapter owns asyncio's I/O stack: the layer contract, the framing tools, and the numbers.

## Section index

- **106.1** The cake, exercised
- **106.2** The machinery: readiness to callbacks to awaitables
- **106.3** Measurement: the taxes and the sweep
- **106.4** Edges and failure modes
- **106.5** Connections
- **106.6** Exercises
- **106.7** Summary and cross-references

Listings live under `code/ch187/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 106.1 The cake, exercised

```python
# code/ch187/l01_streams_and_transports.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- streams: an echo round trip over a real socket ---
  sent 6,405 bytes, echoed back identical : True
  write() buffers, drain() awaits the flow control, read() awaits
  readiness: the awaitable surface over Chapter 101's selector
--- reader contracts: framed, exact, and ended ---
  readline x2   : b'line-one\n', b'line-two\n'
  readexactly(10): b'RAWPAYLOAD'
  read() at EOF : b''  (empty bytes IS the EOF signal)
  framing is the reader's job, not the socket's: TCP hands the
  stack arbitrary chunks, and readline/readexactly reassemble your
  frames from the stream buffer, suspending only when short
--- one layer down: transports and protocols ---
  protocol echo, sent == echoed : True (200,000 bytes)
  data_received fires with whatever chunks the kernel delivers -
  the count of calls is not printable in a verified book, and any
  code that assumes one write means one callback is already wrong
```

**The streams block is the API most code should live on.**
`start_server` and `open_connection` yield reader/writer pairs; `write()` buffers into the transport, `drain()` is the backpressure await (Chapter 105's queue logic at the byte layer), and the echo returns byte-identical across a real socket. Note the shutdown choreography in the listing, `write_eof`, `wait_closed`, `server.wait_closed`: deterministic output over real sockets requires closing everything deliberately, which is also just what correct servers do.

**The contracts block is framing as a service.**
`readline` returns through the newline; `readexactly(10)` returns precisely ten bytes or raises `IncompleteReadError`; `read()` at end-of-stream returns `b''`, and the empty bytes *is* the EOF signal, the same convention as file objects, and the loop condition `while data := await reader.read(n):` falls out of it. All of this reassembly happens in the stream's internal buffer; the socket underneath delivered whatever fragments it pleased.

**And the protocol block prints the only chunking fact that is a fact.**
Two hundred thousand bytes in, two hundred thousand out; how many `data_received` calls carried them is the kernel's whim, varying by platform, load, and moon phase. The listing's refusal to print the call count is the chapter's core warning made structural: **TCP is a byte stream, not a message stream**, and every protocol built on it needs explicit framing, length prefixes, delimiters, or fixed sizes, which is exactly what the streams layer's readers provide.

---

## 106.2 The machinery: readiness to callbacks to awaitables

**Layer one: the selector owns the syscall.**
`kqueue`/`epoll` registration per socket, one poll per loop iteration (Chapter 101, step 2). Everything above is dispatch: the loop maps "fd 7 readable" to the transport that owns fd 7.

**Layer two: the transport owns the socket; the protocol owns the bytes.**
The transport does the actual `recv` into a buffer and calls `protocol.data_received(chunk)`; on the write side, `transport.write` appends to an internal buffer that the transport drains as the socket accepts it, applying **flow control**: when the buffer passes its high-water mark, the transport calls `protocol.pause_writing`, and `resume_writing` when it drains below the low-water mark. Callbacks, not awaitables: this layer is the loop's native idiom, fast, fiddly, and allocation-light, and it is where `uvloop` plugs in a C implementation of the same contract.

**Layer three: streams adapt callbacks to awaitables.**
`StreamReader` is a buffer plus a "data or EOF arrived" future the reader methods await; `StreamWriter.drain()` awaits a future that `resume_writing` completes. Each blocking-feeling call is Chapter 102's machinery over the protocol events, which is why the streams tax in §106.3 is real and why it buys the entire difference in programming model: `await reader.readline()` against hand-rolled buffering in callbacks.

**Backpressure composes through all three layers.**
A slow peer fills the kernel buffer; the transport's writes stop draining; the buffer crosses high water; `pause_writing` fires; `drain()` suspends the producer coroutine; the producer's upstream `Queue.put` suspends behind it (Chapter 105). One slow consumer at the bottom quietly slows the whole pipeline at every layer, with no code written anywhere, and *removing* any bounded link (an unbounded queue mid-pipeline) severs the chain and converts backpressure into memory growth.

---

## 106.3 Measurement: the taxes and the sweep

**Methodology.** `code/ch187/bench_stream_throughput.py`.
Loopback TCP, 100 MB bulk transfers and 5,000 4-byte round trips, `min` of 3; 3.13 shown. Loopback runs at memory speed, so stack costs are *fully visible*, the point, not a distortion; a real wire hides them behind itself.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Bulk throughput, 100 MB echoed.**

| stack | throughput |
|---|---|
| blocking sockets + thread | 7,060 MB/s |
| asyncio streams | 2,286 MB/s (**~3x tax**) |

**b. The read-size sweep (asyncio streams).**

| receive chunk | throughput |
|---|---|
| `read(1 KB)` | 1,052 MB/s |
| `read(16 KB)` | 1,841 MB/s |
| `read(256 KB)` | **2,485 MB/s** |
| `read(1 MB)` | 2,228 MB/s |

**c. Concurrency-one latency, 4-byte ping-pong.**

| stack | per round trip |
|---|---|
| blocking sockets | 15.8 us |
| asyncio streams | 54.4 us (**3.4x**) |

**The taxes are the stack, itemised by the previous chapters.**
Bulk pays per-chunk Python callbacks, buffer copies, and wakeup futures; latency pays Chapter 101's loop iteration on top of the syscalls the blocking pair also makes. Both are honest prices for the layer cake, and both are invisible behind a 10 Gb wire (1,250 MB/s) or a 1 ms network round trip, which is most of why production asyncio services never see them, and why loopback microbenchmarks of async frameworks routinely mislead people into thread nostalgia.

**The sweep is the actionable table.**
A factor of 2.4 between 1 KB and 256 KB reads, from nothing but the second argument to `read()`: small reads multiply wakeups and buffer operations per byte, Chapter 102's suspension arithmetic applied to sockets, Chapter 88's batching rule at the byte layer. The dip at 1 MB is the buffer-management cost of oversized chunks. **Read big, frame with the reader's tools, and let `drain()` handle the other direction**; this is the cheapest I/O optimisation in the book.

**Book I**'s gateway measured the same three tables with smaller constants and identical shapes, and its conclusion transfers: the reactor's throughput is won or lost in chunk sizing and allocation discipline, not in the polling mechanism, and latency-critical single connections bypass the reactor entirely, which is Chapter 108's escape row waiting.

---

## 106.4 Edges and failure modes

**TCP preserves bytes, never boundaries.** §106.1.
One `write` may arrive as five `data_received` calls or five writes as one. Every message protocol needs explicit framing; the reader tools implement the standard framings; and tests that pass on loopback (where chunks often coincide with writes) and fail in production are this edge, every time.

**`write()` without `drain()` is unbounded buffering.**
`write` never blocks and never fails fast; a producer that skips `drain` accumulates the peer's slowness in process memory (the transport buffers it all). `drain` after every burst is the contract; the high/low water marks are tunable per transport when the defaults chatter.

**`read()` returning `b''` means gone, permanently.**
EOF is not "no data yet", it is the peer's half-close. Retrying reads after `b''` spins; the loop idiom in the listing handles it; and `readexactly` raising `IncompleteReadError` on a mid-frame EOF is the framed variant of the same truth, catch it and treat the connection as dead.

**Streams are not thread-safe, and neither are transports.**
Same rule as Chapter 105, same bridge as Chapter 107. One writer coroutine per stream is also the practical rule *within* the loop: interleaved `write`s from two tasks produce interleaved bytes, which framing does not survive.

**Closing is a protocol, not an event.**
`writer.close()` begins teardown; `await writer.wait_closed()` finishes it; dropping a writer without either leaks the socket until GC (and on 3.14t, until *collection*, Chapter 95's timing). Servers add `server.close(); await server.wait_closed()`. The listing's ceremony is the production ceremony.

**The proactor exception.**
Windows' default loop (IOCP) implements the same transport/protocol contract over completion-based I/O rather than readiness; streams code ports untouched, but selector-level tricks (`loop.add_reader` on arbitrary fds) do not. Cross-platform code stays at the transport layer or above.

**And `sendfile`, TLS, and UDP each bend one layer.**
`loop.sendfile` bypasses userspace copies where the OS allows; TLS inserts a transport that owns framing below your framing; UDP swaps the stream contract for datagrams (`DatagramProtocol`), where message boundaries *are* preserved and this chapter's first edge inverts. Each is Deep R's territory at the socket level; the asyncio surface stays shaped as shown here.

---

## 106.5 Connections

**Backward.**
The selector and the loop iteration whose cost the latency table contains are Chapter 101; the suspension arithmetic the sweep applies is Chapter 102; `drain` is Chapter 105's backpressure at the byte layer; batching as a universal rule is Chapter 88. Sockets themselves, options, and the OS story are Deep R.

**Forward.**
Blocking libraries that need this stack's shape without rewriting are Chapter 107's executors. Chapter 108 builds the server patterns, accept loops in task groups, per-connection tasks, bounded pipelines, on exactly the pieces this chapter priced.

**Across books.**
The three-layer cake is Berkeley sockets, readiness APIs, and buffered adapters in every language; **Book I** implements layer two by hand for its gateway and skips layer three entirely, paying in code what Python pays in nanoseconds. The chunk-size sweep is the one table that is numerically similar in both books, because past the framework tax, both are measuring the same kernel.

---

## 106.6 Exercises

**1. Break the boundary assumption.** Write a client that sends three 10-byte messages back-to-back and a protocol server that logs `data_received` sizes. Run on loopback and across a real network; compare the chunkings. Then fix the server with length-prefix framing via `readexactly`.

**2. Reproduce the sweep** on your platform, then repeat over a real link (another machine, or `tc`/Network Link Conditioner shaping). Report where the read-size effect disappears into the wire.

**3. Sever the backpressure.** Build producer, unbounded queue, slow socket consumer; plot memory over time. Bound the queue and plot again. Then remove the consumer's `drain()` and find where the growth moved.

**4. Race two writers.** Have two tasks write framed messages to one stream without coordination; count corrupted frames at the receiver. Fix with a per-stream writer task fed by a queue (Chapter 105), and re-measure the throughput cost of the fix.

**5. Close everything, provably.** Instrument a server with a socket-count probe (via `psutil` or `/proc`); run a thousand connect-transfer-disconnect cycles with and without the full close ceremony; report the leak curve and the 3.14t difference (Chapter 95).

**6. The design question.** Streams could have been the only API, hiding transports entirely; instead both layers are public. Argue the two-layer choice: what protocol-level code buys (`uvloop`'s C transports; framing-heavy protocols that want callbacks; zero extra buffer for pass-through proxies) against the cost (two idioms, migration confusion, this chapter needing a section it would not otherwise need). Then inspect one real library (an HTTP server, a database driver) and report which layer it chose and whether §106.3's tables justify it.

---

## 106.7 Summary and cross-references

- **Three layers**: the selector reports readiness (Chapter 101); transports/protocols turn it into callbacks with kernel-chosen chunking and flow control (`pause_writing`/`resume_writing`); streams turn callbacks into awaitables with framing (`readline`, `readexactly`) and backpressure (`drain`).
- **TCP preserves bytes, not boundaries**, verified by printing only chunking-independent facts; all framing is explicit, and the reader tools are the standard framings. `b''` from `read()` is EOF, permanently.
- **Priced on loopback (where nothing hides)**: the stack costs ~**3x** raw blocking sockets on bulk and **3.4x** on concurrency-one latency, honest layer prices that vanish behind real wires; and the **read-size sweep recovers 2.4x** inside the stack (1,052 to 2,485 MB/s from 1 KB to 256 KB reads), the cheapest I/O optimisation in the book.
- **Backpressure composes end-to-end** through kernel buffer, transport water marks, `drain`, and Chapter 105's queues, until any unbounded link severs it into memory growth.
- **The ceremonies are load-bearing**: `drain` per burst, one writer per stream, `close`+`wait_closed` always, and the proactor/UDP/TLS variants bend single layers without changing the surface.

**Cross-references.** The loop and the selector → Chapter 101. Suspension arithmetic → Chapter 102. Backpressure objects → Chapter 105. Batching → Chapter 88. Sockets and the OS → Deep R. Executors for blocking libraries → Chapter 107. Server patterns → Chapter 108.
