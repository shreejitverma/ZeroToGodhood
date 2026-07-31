"""Listing 212.1 - the matching engine: the carried-through system, in Python.

Every 'Across books' note in this volume has pointed at a shared trading
system. This chapter builds its heart: a price-time-priority limit order book
and matching engine. An order book holds resting bids and asks; an incoming
order MATCHES against the best opposite prices until filled or resting. The
rules are exact and the outcomes deterministic, so the whole engine verifies
byte-for-byte - which is itself the point: a matching engine that is not
deterministic is not auditable, and an unauditable exchange is a fraud
investigation waiting to happen. This is the container decision (Chapter 88)
and the memory model (Chapter 89) of the whole book, made load-bearing.
"""

import heapq
from dataclasses import dataclass, field


@dataclass(order=True)
class RestingOrder:
    # price-time priority: the sort key is (price-signed, sequence)
    sort_key: tuple = field(compare=True)
    order_id: int = field(compare=False)
    qty: int = field(compare=False)


class OrderBook:
    """Bids in a max-heap (best = highest price), asks in a min-heap
    (best = lowest). Ties broken by arrival sequence: price-TIME priority."""

    def __init__(self):
        self.bids = []          # heap of RestingOrder, key = (-price, seq)
        self.asks = []          # heap of RestingOrder, key = (price, seq)
        self.seq = 0
        self.next_id = 1

    def _take(self, book, sign, limit_price, incoming_qty, is_buy):
        fills = []
        while book and incoming_qty > 0:
            best = book[0]
            best_price = sign * best.sort_key[0]
            crosses = (best_price <= limit_price) if is_buy \
                else (best_price >= limit_price)
            if not crosses:
                break
            traded = min(incoming_qty, best.qty)
            fills.append((best.order_id, best_price, traded))
            incoming_qty -= traded
            best.qty -= traded
            if best.qty == 0:
                heapq.heappop(book)
        return fills, incoming_qty

    def submit(self, side, price, qty):
        """Match against the opposite side, rest the remainder. Returns
        (order_id, fills, resting_qty) - a deterministic receipt."""
        oid = self.next_id
        self.next_id += 1
        if side == "buy":
            fills, remaining = self._take(self.asks, +1, price, qty, True)
            if remaining > 0:
                self.seq += 1
                heapq.heappush(self.bids,
                               RestingOrder((-price, self.seq), oid, remaining))
        else:
            fills, remaining = self._take(self.bids, -1, price, qty, False)
            if remaining > 0:
                self.seq += 1
                heapq.heappush(self.asks,
                               RestingOrder((price, self.seq), oid, remaining))
        return oid, fills, remaining

    def best_bid(self):
        return -self.bids[0].sort_key[0] if self.bids else None

    def best_ask(self):
        return self.asks[0].sort_key[0] if self.asks else None


def main() -> None:
    book = OrderBook()

    print("--- resting orders build the book ---")
    for side, price, qty in (("buy", 100, 10), ("buy", 99, 5),
                             ("sell", 102, 8), ("sell", 103, 20)):
        oid, fills, resting = book.submit(side, price, qty)
        print(f"  {side} {qty}@{price:<4} -> id {oid}, {len(fills)} fills, "
              f"{resting} resting")
    print(f"  best bid {book.best_bid()}, best ask {book.best_ask()}"
          f"  (the SPREAD: no trade until someone crosses it)")
    print("  bids sort highest-first, asks lowest-first, ties by arrival: a")
    print("  heap gives O(log n) insert and O(1) best (Chapter 88's exact")
    print("  cost model - the right container is the whole design)")

    print("--- a crossing order matches at the RESTING price ---")
    oid, fills, resting = book.submit("buy", 102, 5)
    print(f"  buy 5@102 -> id {oid}")
    for fill_id, fill_price, fill_qty in fills:
        print(f"    filled {fill_qty}@{fill_price} against resting id {fill_id}")
    print(f"    {resting} resting")
    print("  the buyer offered 102 and the best ask was 102: they trade at")
    print("  102 (the resting order's price - price improvement goes to the")
    print("  order that was there FIRST). the taker crossed the spread")

    print("--- a large order walks the book, filling at multiple levels ---")
    oid, fills, resting = book.submit("buy", 103, 25)
    print(f"  buy 25@103 -> id {oid}")
    for fill_id, fill_price, fill_qty in fills:
        print(f"    filled {fill_qty}@{fill_price} against resting id {fill_id}")
    print(f"    {resting} resting at 103 (unfilled remainder becomes a bid)")
    print("  25 shares swept the 3@102 remainder then 20@103, and the last 2")
    print("  found no more asks, so they REST as a new bid. one order, many")
    print("  fills, a deterministic sequence - the receipt an exchange must")
    print("  be able to reproduce on demand (Chapter 85's honesty, as law)")

    print("--- why determinism is the requirement, not a nicety ---")
    print("  same orders in the same sequence ALWAYS produce the same fills")
    print("  at the same prices: this listing's output is identical on three")
    print("  interpreters BECAUSE the engine is deterministic. an exchange")
    print("  that cannot replay its tape cannot be audited, and price-time")
    print("  priority is the rule that makes the replay unambiguous")


if __name__ == "__main__":
    main()
