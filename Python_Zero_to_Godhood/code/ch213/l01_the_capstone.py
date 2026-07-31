"""Listing 213.1 - the capstone: the whole system, one request, end to end.

Deep V closes by wiring its chapters into the system they describe. An order
arrives as an HTTP request; it descends the middleware onion (auth, Chapter
129), is routed (Chapter 128), crosses the API boundary (parse+validate,
Chapter 130), reaches the matching engine (Chapter 131), and its fills return
as a response while a market-data event is published to subscribers. Every
piece is a prior chapter's code, imported and composed - the volume is not a
tour of parts, it is one system taken apart to be understood and here put
back together, driven in-process (the ASGI test-is-a-call of Chapter 127) so
the whole flow verifies deterministically.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ch211.l01_the_api_boundary import validate_order   # Chapter 130
from ch212.l01_the_matching_engine import OrderBook      # Chapter 131

BOOK = OrderBook()
MARKET_DATA = []                 # the published tape subscribers would receive


def auth_layer(inner):
    """Chapter 129's onion, outermost: reject before any work."""
    async def middleware(scope, receive, send):
        if scope.get("token") != "trader-key":
            await send({"type": "http.response.start", "status": 401})
            await send({"type": "http.response.body",
                        "body": b'{"error":"unauthorized"}'})
            return
        await inner(scope, receive, send)
    return middleware


async def order_app(scope, receive, send):
    """The handler: route, boundary, match, respond, publish."""
    if scope["path"] != "/orders" or scope["method"] != "POST":   # Chapter 128
        await send({"type": "http.response.start", "status": 404})
        await send({"type": "http.response.body", "body": b'{"error":"not found"}'})
        return

    event = await receive()                                       # Chapter 127
    data = json.loads(event["body"])
    value, errors = validate_order(data)                          # Chapter 130
    if errors:
        await send({"type": "http.response.start", "status": 422})
        await send({"type": "http.response.body",
                    "body": json.dumps({"fields": errors}).encode()})
        return

    oid, fills, resting = BOOK.submit(                            # Chapter 131
        value["side"], data["price"], value["qty"])
    for fill_id, price, qty in fills:                             # Chapter 91
        MARKET_DATA.append({"price": price, "qty": qty})          # publish tape

    receipt = {"order_id": oid,
               "fills": [{"price": p, "qty": q} for _, p, q in fills],
               "resting": resting}
    body = json.dumps(receipt, separators=(",", ":")).encode()
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})


async def call(app, method, path, token, body=b""):
    """Drive the ASGI stack in-process - Chapter 127's test-is-a-call."""
    scope = {"type": "http", "method": method, "path": path, "token": token}
    incoming = [{"type": "http.request", "body": body, "more_body": False}]
    sent = []

    async def receive():
        return incoming.pop(0)

    async def send(ev):
        sent.append(ev)

    await app(scope, receive, send)
    status = next(e["status"] for e in sent if e["type"] == "http.response.start")
    payload = b"".join(e.get("body", b"") for e in sent
                       if e["type"] == "http.response.body")
    return status, payload


async def main_async() -> None:
    app = auth_layer(order_app)                  # the composed system

    print("--- seed the book with resting liquidity ---")
    for side, price, qty in (("sell", 102, 8), ("sell", 103, 20)):
        BOOK.submit(side, price, qty)
    print(f"  best ask {BOOK.best_ask()}, resting asks in place")

    print("--- an unauthenticated order is rejected at the edge ---")
    status, body = await call(app, "POST", "/orders", token="wrong",
                              body=b'{"symbol":"ACME","side":"buy",'
                                   b'"qty":5,"price":102}')
    print(f"  {status} : {body.decode()}")
    print("  the onion's outermost layer stopped it before routing, parsing,")
    print("  or matching ran (Chapter 129's short-circuit, in the system)")

    print("--- a malformed order is rejected at the boundary ---")
    status, body = await call(app, "POST", "/orders", token="trader-key",
                              body=b'{"symbol":"ACME","side":"hold",'
                                   b'"qty":-5,"price":102}')
    print(f"  {status} : {body.decode()}")
    print("  auth passed, routing matched, but validation caught the bad")
    print("  side and qty (Chapter 130) - the matching engine never saw it")

    print("--- a good order flows all the way through ---")
    status, body = await call(app, "POST", "/orders", token="trader-key",
                              body=b'{"symbol":"ACME","side":"buy",'
                                   b'"qty":10,"price":103}')
    print(f"  {status} : {body.decode()}")
    print(f"  market-data tape now : {MARKET_DATA}")
    print("  auth -> route -> validate -> match -> respond -> publish, six")
    print("  chapters in one request: the order crossed the spread, filled")
    print("  8@102 and 2@103, and the fills were published to the tape a")
    print("  websocket subscriber (Chapter 127) would stream")

    print("--- the system, and the two books ---")
    print("  this Python system is complete and correct at microsecond")
    print("  latency - right for a backtester (Deep W), an analytics venue,")
    print("  and the non-latency-critical tier. Book I's C++ runs the same")
    print("  design at nanosecond latency for the exchange core, and the")
    print("  seam between them is every boundary this volume drew: HTTP at")
    print("  the edge (Chapter 125), the API contract (130), the matching")
    print("  algorithm (131) - one system, two languages, chosen by need.")
    print("  Deep V closed; the carried-through system has landed.")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
