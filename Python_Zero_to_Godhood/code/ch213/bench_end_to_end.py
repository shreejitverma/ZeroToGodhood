"""Benchmark 213.1 - the whole pipeline, priced, and where the time goes.

  213.1a  end-to-end latency of one order through the full stack (auth, route,
          parse, validate, match, serialize, publish) against the matching
          engine alone. The difference is everything the web layer adds around
          the trade - and the ratio is the chapter's closing lesson: the
          plumbing costs more than the matching, which is why the matching
          core is what gets rewritten in C++ (Book I) while the plumbing stays
          in Python.

  213.1b  the layer breakdown: parse, validate, and serialize timed
          separately (from Chapters 130), so the end-to-end number is
          attributed rather than asserted. json dominates; the trade is
          nearly free by comparison.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, provenance, report  # noqa: E402
from ch212.l01_the_matching_engine import OrderBook  # noqa: E402
import ch213.l01_the_capstone as capstone  # noqa: E402


def main():
    ORDER = (b'{"symbol":"ACME","side":"buy","qty":1,"price":200}')

    print("=== 213.1a  end-to-end request vs the trade alone ===")
    print(provenance())
    print("method      : min of 5; a fresh deep book per measurement")
    print()

    def full_request():
        capstone.BOOK = OrderBook()
        capstone.MARKET_DATA = []
        for _ in range(500):
            capstone.BOOK.submit("sell", 300, 1)      # deep resting book
        app = capstone.auth_layer(capstone.order_app)
        asyncio.run(capstone.call(app, "POST", "/orders",
                                  token="trader-key", body=ORDER))

    def trade_only():
        book = OrderBook()
        for _ in range(500):
            book.submit("sell", 300, 1)
        book.submit("buy", 200, 1)                    # rests, no cross

    import time

    def best(fn, repeat=5):
        times = []
        for _ in range(repeat):
            t0 = time.perf_counter()
            fn()
            times.append(time.perf_counter() - t0)
        return min(times)

    full = best(full_request)
    trade = best(trade_only)
    print(f"  full request (7 stages) : {full * 1e6:8.1f} us")
    print(f"  matching engine alone   : {trade * 1e6:8.1f} us")
    print("  (the full request includes building/tearing a loop per call,")
    print("  which a live server amortises - the SHAPE, not the absolute,")
    print("  is the lesson)")

    print()
    SETUP = """
import json
from ch211.l01_the_api_boundary import validate_order
raw = b'{"symbol":"ACME","side":"buy","qty":1,"price":200}'
obj = json.loads(raw)
receipt = {"order_id": 1, "fills": [{"price": 200, "qty": 1}], "resting": 0}
"""
    rows = [
        measure("parse", "json.loads(raw)", SETUP),
        measure("validate", "validate_order(obj)", SETUP),
        measure("serialize", "json.dumps(receipt, separators=(',',':'))", SETUP),
    ]
    report("213.1b  the boundary stages, attributed", rows, baseline="parse")

    print()
    print("Reading this. The web plumbing around a trade costs more than the")
    print("trade: json parsing and serialization, validation, and the async")
    print("machinery dominate, while the matching engine - the part that")
    print("actually determines who trades with whom - is a rounding error in")
    print("the request. That inversion is the whole system's design in one")
    print("measurement: the matching CORE is where nanoseconds are worth")
    print("rewriting in C++ (Book I), because it is on the latency-critical")
    print("path and its determinism is the product; the PLUMBING stays in")
    print("Python because its milliseconds are dominated by json and I/O")
    print("that C++ would not meaningfully speed, and its development cost is")
    print("where Python earns its place. Deep V, and the volume, close on")
    print("the seam every chapter has been drawing: measure, then put each")
    print("piece in the language its requirement demands.")


if __name__ == "__main__":
    main()
