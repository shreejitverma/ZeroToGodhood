# Chapter 131: The Matching Engine

Every "Across books" note in this volume, and in most of the book, has pointed at a shared trading system. This chapter builds its heart in Python: a **price-time-priority limit order book and matching engine**. An order book holds resting bids and asks; an incoming order matches against the best opposite prices until filled or resting. The rules are exact and the outcomes deterministic, so the whole engine verifies byte-for-byte on three interpreters, and *that determinism is the point*: a matching engine that is not reproducible is not auditable, and an unauditable exchange is a fraud investigation waiting to happen.

The listing builds the book, four resting orders establishing a **spread** (best bid 100, best ask 102, no trade until someone crosses it), then exercises the three matching cases. A crossing order **matches at the resting price**: `buy 5@102` against a resting `sell ...@102` trades at 102, price improvement to the order that was there first. A large order **walks the book**: `buy 25@103` sweeps the 3@102 remainder, then 20@103, and rests the last 2 as a new bid, one order, many fills, a deterministic receipt an exchange must be able to reproduce on demand.

This is the whole book made load-bearing. The container is Chapter 88's heap (O(log n) insert, O(1) best); the benchmark shows submit throughput **flat to the noise across a 100-fold-deeper book** (504 → 491 ns/order), the exact scalability that container choice buys. And it prices the book's central seam: Python matches at **411 ns/order**, fast enough for backtesting and most venues, while Book I's C++ core matches in tens of nanoseconds for the latency-critical exchange, the two languages chosen by measured latency need (Chapter 84), never by taste.

**This is a Deep V chapter.**
Chapters 126-130 own the web layer that fronts this engine; Chapter 132 runs the whole system end to end. This chapter owns the matching engine: the algorithm, the determinism, and the language seam.

## Section index

- **131.1** The book, the spread, and the three matching cases
- **131.2** The model: price-time priority, heaps, and determinism as law
- **131.3** Measurement: the container's scalability, the language seam
- **131.4** Edges and failure modes
- **131.5** Connections
- **131.6** Exercises
- **131.7** Summary and cross-references

Listings live under `code/ch212/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 131.1 The book, the spread, and the three matching cases

```python
# code/ch212/l01_the_matching_engine.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- resting orders build the book ---
  buy 10@100  -> id 1, 0 fills, 10 resting
  buy 5@99   -> id 2, 0 fills, 5 resting
  sell 8@102  -> id 3, 0 fills, 8 resting
  sell 20@103  -> id 4, 0 fills, 20 resting
  best bid 100, best ask 102  (the SPREAD: no trade until someone crosses it)
  bids sort highest-first, asks lowest-first, ties by arrival: a
  heap gives O(log n) insert and O(1) best (Chapter 88's exact
  cost model - the right container is the whole design)
--- a crossing order matches at the RESTING price ---
  buy 5@102 -> id 5
    filled 5@102 against resting id 3
    0 resting
  the buyer offered 102 and the best ask was 102: they trade at
  102 (the resting order's price - price improvement goes to the
  order that was there FIRST). the taker crossed the spread
--- a large order walks the book, filling at multiple levels ---
  buy 25@103 -> id 6
    filled 3@102 against resting id 3
    filled 20@103 against resting id 4
    2 resting at 103 (unfilled remainder becomes a bid)
  25 shares swept the 3@102 remainder then 20@103, and the last 2
  found no more asks, so they REST as a new bid. one order, many
  fills, a deterministic sequence - the receipt an exchange must
  be able to reproduce on demand (Chapter 85's honesty, as law)
--- why determinism is the requirement, not a nicety ---
  same orders in the same sequence ALWAYS produce the same fills
  at the same prices: this listing's output is identical on three
  interpreters BECAUSE the engine is deterministic. an exchange
  that cannot replay its tape cannot be audited, and price-time
  priority is the rule that makes the replay unambiguous
```

**The spread is the book's resting state, and it is where no trade happens.**
Four orders rest without trading because the highest bid (100) is below the lowest ask (102): buyers and sellers disagree on price, and the gap between them is the spread. A trade requires someone to *cross* it, offering to buy at or above the best ask, or sell at or below the best bid. This is the market's fundamental structure, resting liquidity on both sides, a spread between them, and trades only when an aggressor crosses, and every subsequent case is a crossing.

**Matching at the resting price is the rule that rewards being early.**
`buy 5@102` was willing to pay up to 102; the best ask was resting at 102; they trade at **102**, the resting order's price. Had the ask rested at 101, the buy would trade at 101 (price improvement to the buyer). The principle: the *taker* (the aggressor crossing the spread) gets the resting *maker*'s price, so the maker who posted liquidity first is protected. This is why market microstructure rewards posting (maker) over taking (taker), and it is a rule, not a heuristic, the engine has no discretion.

**Walking the book is one order becoming many fills, deterministically.**
`buy 25@103` cannot fill at one level: it takes the 3 remaining @102, then 20 @103, exhausts the asks, and rests its last 2 as a bid. The *sequence* of fills, 3@102 then 20@103, is fixed by price-time priority (best price first, then arrival order), so the receipt is reproducible: the same order against the same book always produces the same fills at the same prices. This receipt is what regulators subpoena, what clearing reconciles, and what a backtest (Deep W) replays, and its determinism is the engine's most important property.

**And the last block states the requirement the whole listing exists to demonstrate.**
The output is byte-identical on three interpreters *because the engine is deterministic*, and that is not a happy accident of the harness but the engine's core requirement. An exchange that cannot replay its tape, feed the same orders in the same sequence and get the same trades, cannot prove it treated participants fairly, cannot reconcile disputes, cannot be audited. Price-time priority is the rule that makes the replay unambiguous, and determinism is the law, not the nicety.

---

## 131.2 The model: price-time priority, heaps, and determinism as law

**Price-time priority is a total order on resting orders.**
Orders rest sorted by price (best first: highest bid, lowest ask) and, at equal price, by arrival time (earliest first). This total order makes matching deterministic: the incoming order always takes the single best resting order, and "best" is never ambiguous. Alternatives exist (pro-rata allocation, size-time priority) but price-time is the dominant rule precisely because it is simple, fair-by-construction (post earlier, fill earlier), and unambiguous, the properties an auditable market needs.

**The heap is the container the access pattern demands, exactly Chapter 88.**
The operations are: insert a resting order (O(log n)), read the best price (O(1)), and remove the best when filled (O(log n)). That is a priority queue, and `heapq` on a `(signed_price, sequence)` key gives it: bids keyed by `(-price, seq)` so the max-price-earliest is the heap's min; asks by `(price, seq)`. Chapter 88's decision procedure, name the access pattern, pick the container with the right exponent, produces the heap here without deliberation, and §131.3 shows it delivering the scalability the choice promises. A list would make "find the best" O(n) and matching O(n) per order, the accidental quadratic Chapter 88 warned against, in the hottest loop of an exchange.

**Determinism is engineered, not assumed.**
The engine uses integer prices and quantities (no float rounding, Chapter 35's money lesson), an explicit arrival sequence (not wall-clock time, which is non-monotonic and non-reproducible), and no randomness anywhere. Every source of nondeterminism, floats, timestamps, hash iteration order, concurrent mutation, is a source of unauditability, so a real engine excludes them all: fixed-point prices (Book I stores them as scaled integers, this listing as plain ints), a monotonic sequence counter, and single-threaded matching (the matching *core* is single-threaded by design even in a multi-threaded system, because determinism requires a total order on events, Chapter 99's lesson at the exchange).

**The engine is the meeting point of the book's threads.**
Container choice (Chapter 88), fixed-point money (Chapter 35), memory layout of the order records (Chapter 89, `__slots__`/dataclass), determinism-as-auditability (Chapter 85's honesty as law), and the single-threaded-core-for-total-order rule (Chapter 99): every one of these appears here not as an example but as a *requirement*. This is why the trading system was the book's carried-through example, it needed all of them at once, and the matching engine is where they become load-bearing rather than illustrative.

---

## 131.3 Measurement: the container's scalability, the language seam

**Methodology.** `code/ch212/bench_matching_throughput.py`.
20,000 non-crossing submits against pre-loaded books; submit latency separately; `min` of 5-9; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Submit throughput vs book depth:**

| book depth | per order | orders/s |
|---|---|---|
| 100 | 504 ns | 1,984,750 |
| 1,000 | 506 ns | 1,975,756 |
| 10,000 | **491 ns** | 2,037,308 |

**b. The language seam:** Python matching engine **411 ns/order**; Book I's C++ core (cited) tens of ns/order, ~14x.

**Table a is Chapter 88's promise kept in its strongest form.**
A hundred-fold deeper book costs *no measurable extra per order*, the row is flat to the noise, because heap operations are O(log n) and log grows so slowly (log 100 to log 10,000 is a factor of 2 in a term that is a small fraction of the total work) that depth stops being a scalability worry. This is the container decision paying off exactly as designed: the engine matches two million orders a second regardless of book depth, and it does so because the access pattern chose the heap. A list-based book would show this row *collapsing* with depth, the accidental quadratic; the heap makes depth free.

**Table b is the book's entire thesis compressed to two numbers.**
Python matches an order in 411 ns, so a Python matching engine handles millions of orders per second, ample for backtesting every strategy (Deep W), for most trading venues, and for the analytics and risk tier of the shared system. Book I's C++ engine matches in tens of nanoseconds, ~14x faster, for the latency-critical exchange core where every nanosecond of matching latency is a competitive edge. **The seam between the two books is drawn at the latency requirement**, not at a language preference: the *same algorithm* and the *same order book* live in both, and the choice of language at each point is a measured response to a stated need (Chapter 84's boundary decision, at the system's heart). A team that put the whole system in Python would be fast enough for everything but the exchange core; a team that put it all in C++ would pay C++'s development cost for the 99% that does not need it. The two-book split is that measurement made into an architecture.

**Book I**'s matching-engine chapter is this one with C++ constants and the same structure, integer prices, a heap (or a more specialised structure, an array of price levels for dense books), single-threaded deterministic matching, and its "Across books" note points *back here*, closing the loop the whole series has been drawing: one system, one algorithm, two languages, the seam at the latency line.

---

## 131.4 Edges and failure modes

**Floats in prices are a determinism bug and a money bug at once.** Chapter 35.
`0.1 + 0.2 != 0.3` in the order book means two runs can produce different fills, and cents can vanish or appear. Prices and quantities are integers (scaled fixed-point: store cents, or ticks), always, and a matching engine that uses floats is both unauditable and wrong about money, the two failure modes this chapter cannot tolerate, in one mistake.

**Wall-clock time is not a sequence.**
Using timestamps for time priority breaks on clock skew, NTP adjustments, and equal-timestamp ties; the engine uses a monotonic *sequence counter* assigned at ingestion, which is reproducible and totally ordered. "Time priority" means *arrival-sequence* priority, and conflating it with the clock is a fairness bug (two orders at the "same" microsecond have an undefined winner).

**The matching core must be single-threaded for a total order.** Chapter 99.
Concurrent matching threads would race on the book and produce interleaving-dependent (nondeterministic, unauditable) fills. Real exchanges make the *matching core* single-threaded, an event loop consuming a totally-ordered order stream, and parallelise everything *around* it (ingestion, risk checks, market-data dissemination). This is the free-threaded build's limit meeting the exchange's requirement: even where threads *could* run, the matching core must not, because determinism needs one writer.

**Partial fills and order states multiply the correctness surface.**
A resting order partially filled, then cancelled, then the cancel racing an incoming match, is where real engines get subtle: an order has a lifecycle (new, partially filled, filled, cancelled, rejected), and every transition must be atomic against matching. The listing shows partial fills (the 25-order's remainder rests); a production engine adds cancel/modify, each a determinism-critical operation.

**Self-trade prevention and market-integrity rules layer on top.**
An order that would match against the same participant's resting order (a wash trade) must be prevented; price bands, minimum tick sizes, and circuit breakers constrain what may rest or trade. These are policy layers above the core matching, each adding rules the deterministic replay must include, and each a regulatory requirement, not an optimisation.

**And the O(1)-best assumes the best is at the heap root, which cancellation complicates.**
Cancelling a resting order that is *not* at the root is O(n) in a plain heap (you must find it), so real engines index orders by id (a dict from order-id to its location) alongside the price heap, the two-container pattern Chapter 88 anticipated. The listing omits cancellation for clarity; adding it is where the data-structure design gets its second half.

---

## 131.5 Connections

**Backward.**
The heap and container-choice decision procedure, Chapter 88; fixed-point money, Chapter 35; memory layout of order records, Chapter 89; determinism-as-honesty elevated to law, Chapter 85; the single-writer-for-total-order rule, Chapter 99; the language-boundary decision, Chapter 84; the web layer that submits orders to this engine, Chapters 126-130; the streaming market data it produces, Chapter 91 and Chapter 127's websockets.

**Forward.**
The capstone that runs the whole system, order submitted over ASGI, validated at the boundary, matched here, filled back to the client, and streamed to market-data subscribers, Chapter 132, closing Deep V and the volume's applied arc.

**Across books.**
This chapter and **Book I**'s matching-engine chapter are the same system in two languages, and the series' central claim, that the exponent and the algorithm are portable while the constants and the language are chosen by measured need, is *this pair of chapters*. The shared order book, the shared price-time rule, the shared determinism requirement, expressed in Python here and C++ there, with the seam at the latency line, is the whole three-book series in one artifact.

---

## 131.6 Exercises

**1. Add cancellation.** Implement O(1) cancel by indexing orders by id (the second container, Chapter 88); handle cancelling a partially-filled resting order and prove the book stays consistent.

**2. Prove determinism.** Feed a random-but-seeded order stream through the engine twice and assert identical fills; then introduce a float price and show the determinism breaking. Keep both as a regression test.

**3. Fixed-point money.** Convert prices to scaled integers (ticks) with a stated tick size; add tick-size validation at submission and show a sub-tick order rejected. Relate to Chapter 35.

**4. Self-trade prevention.** Add participant ids and reject (or cancel-both) orders that would match against the same participant; test the wash-trade case.

**5. Measure the list-based disaster.** Reimplement the book with a sorted list instead of a heap; reproduce §131.3a and show the throughput collapsing with depth (the accidental quadratic, Chapter 88). Report the crossover where the heap's win becomes decisive.

**6. The design question.** This engine is single-threaded for determinism, on a machine (and a free-threaded build) that could run it parallel. Argue why the matching *core* must stay single-threaded (total order for auditability, Chapter 99) even as everything around it parallelises, what a "parallel matching engine" would have to give up (a single total order, hence auditability) or engineer around (deterministic partitioning by instrument, so each instrument's book is single-threaded but different instruments run in parallel), and how that partitioning maps onto Chapter 98's subinterpreters or Chapter 100's process-per-shard. Then locate the shared system's real design on that spectrum.

---

## 131.7 Summary and cross-references

- **The matching engine is a price-time-priority limit order book**: resting bids/asks with a spread between them, and trades only when an order crosses. Crossing orders **match at the resting price** (early liquidity protected), and large orders **walk the book** into multiple deterministic fills.
- **Determinism is the requirement, not a nicety**: same orders, same sequence, same fills, verified byte-identical across three interpreters, because an exchange that cannot replay its tape cannot be audited. Achieved with integer prices (Chapter 35), a monotonic sequence (not the clock), and a single-threaded core (Chapter 99).
- **The heap is the container the access pattern demands** (Chapter 88): O(log n) insert, O(1) best, and measured **flat throughput across a 100-fold-deeper book** (504 → 491 ns/order, ~2M orders/s), the scalability container choice buys, where a list would collapse.
- **The language seam is the book's thesis**: Python matches at **411 ns/order** (ample for backtests, most venues, the analytics tier), Book I's C++ core at tens of ns (~14x, for the latency-critical exchange); the same algorithm and book in both, the seam drawn at the **latency requirement** (Chapter 84), never at taste.
- **The engine is where the book's threads become load-bearing**: containers, fixed-point money, memory layout, determinism-as-law, single-writer-for-total-order, all requirements here, which is why the trading system was the carried-through example.

**Cross-references.** Containers → Chapter 88. Fixed-point money → Chapter 35. Memory layout → Chapter 89. Determinism as honesty → Chapter 85. Single-writer total order → Chapter 99. The language boundary → Chapter 84. The web layer → Chapters 126-130. Market-data streaming → Chapters 91, 127. The capstone → Chapter 132.
