"""Listing 208.1 - ASGI: the async contract that climbs WSGI's ceiling.

Chapter 126's WSGI callable RETURNS its response, so it cannot yield control
while waiting. ASGI replaces the one signature with an async one that
communicates by MESSAGES: `async def app(scope, receive, send)`, where scope
describes the connection, receive() awaits incoming events, and send() emits
outgoing ones. Because the app AWAITS, one event loop (Chapter 101) serves
thousands of connections that are mostly waiting - the C10k wall from
Chapter 126, climbed. This listing implements a complete ASGI app, drives it
in-process with the same test-is-a-function-call ergonomics WSGI had, and
shows why the message shape (not a return value) is what makes streaming,
websockets, and background work expressible in ONE contract.
"""

import asyncio


async def application(scope, receive, send):
    """A complete ASGI HTTP app: route, read the body via messages, reply."""
    assert scope["type"] == "http"
    path = scope["path"]

    body = b""
    more = True
    while more:                              # a request body arrives as events
        event = await receive()
        body += event.get("body", b"")
        more = event.get("more_body", False)

    if path == "/ping":
        status, payload = 200, b"pong"
    elif path == "/echo" and scope["method"] == "POST":
        status, payload = 200, body
    else:
        status, payload = 404, b"not found"

    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"text/plain")]})
    await send({"type": "http.response.body", "body": payload})


async def call_app(app, method, path, body=b""):
    """Drive an ASGI app in-process: build scope, script receive/send."""
    scope = {"type": "http", "method": method, "path": path, "headers": []}
    incoming = [{"type": "http.request", "body": body, "more_body": False}]
    sent = []

    async def receive():
        return incoming.pop(0)

    async def send(event):
        sent.append(event)

    await app(scope, receive, send)
    start = next(e for e in sent if e["type"] == "http.response.start")
    body_events = [e for e in sent if e["type"] == "http.response.body"]
    return start["status"], b"".join(e["body"] for e in body_events)


async def streaming_app(scope, receive, send):
    """A response of unknown length, streamed - impossible to RETURN, natural
    to SEND (Chapter 91 at the protocol layer)."""
    await send({"type": "http.response.start", "status": 200, "headers": []})
    for i in range(3):
        await asyncio.sleep(0)               # yield: other connections run here
        last = i == 2
        await send({"type": "http.response.body", "body": f"chunk{i};".encode(),
                    "more_body": not last})


async def main_async() -> None:
    print("--- the app is an async callable, still test-is-a-call ---")
    for method, path, body in (("GET", "/ping", b""),
                               ("POST", "/echo", b"order:buy:100"),
                               ("GET", "/nope", b"")):
        status, payload = await call_app(application, method, path, body)
        print(f"  {method} {path:<6} -> {status}  {payload!r}")
    print("  scope in, messages out: an ASGI test is still a function call,")
    print("  WSGI's best property kept while the RETURN became a stream of")
    print("  send() events - which is the change that buys everything else")

    print("--- the request body is events, not a blocking read ---")
    print("  receive() is AWAITED, so a slow upload does not pin a worker: the")
    print("  loop runs other connections between chunks. this is Chapter 126's")
    print("  wsgi.input.read(), turned inside out into something the event")
    print("  loop can interleave (Chapter 101)")

    print("--- streaming falls out of send(), and concurrency is proven ---")
    order = []

    async def drive_streaming(tag):
        sent = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(event):
            if event["type"] == "http.response.body":
                order.append(f"{tag}:{event['body'].decode()}")
            sent.append(event)
        await streaming_app({"type": "http"}, receive, send)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(drive_streaming("A"))
        tg.create_task(drive_streaming("B"))
    print(f"  two streaming responses interleaved on one loop:")
    print(f"    {', '.join(order)}")
    print("  A and B alternate because each send() sits behind an await, so")
    print("  the loop serves both connections at once on ONE thread - the")
    print("  C10k wall (Chapter 126) climbed, not by more workers but by")
    print("  not blocking the one worker there is")

    print("--- one contract, three protocols ---")
    print("  scope['type'] is 'http', 'websocket', or 'lifespan': the same")
    print("  app object handles request/response, long-lived bidirectional")
    print("  sockets, and startup/shutdown, because MESSAGES generalise where")
    print("  a return value cannot. WSGI could never express a websocket;")
    print("  ASGI expresses it as more receive()/send() of a different type")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
