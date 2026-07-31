"""Listing 210.1 - middleware: the onion, and why order is a correctness property.

Chapter 126 noted that because an app is a callable, middleware is 'an app that
wraps an app'. This listing makes the pattern concrete and proves its two
governing facts. First, the ONION: a request descends through the layers
outside-in and the response ascends inside-out, so each middleware sees the
request on the way down and the response on the way up - one wrapper, two
hooks. Second, ORDER IS SEMANTIC: authentication must wrap outside the
handler (reject before work), compression must wrap outside logging-of-size
but inside auth, and swapping two layers can change behaviour, security, or
both. Demonstrated with an explicit trace so the onion is visible, not
narrated.
"""


def make_app(handler):
    """The innermost layer: run the handler, return (status, body)."""
    def app(request):
        return handler(request)
    return app


def timing(inner, trace):
    def middleware(request):
        trace.append("timing:in")
        status, body = inner(request)
        trace.append("timing:out")
        return status, body
    return middleware


def auth(inner, trace):
    def middleware(request):
        trace.append("auth:in")
        if not request.get("token"):
            trace.append("auth:reject")
            return 401, b"unauthorized"          # short-circuit: inner never runs
        status, body = inner(request)
        trace.append("auth:out")
        return status, body
    return middleware


def gzip_body(inner, trace):
    def middleware(request):
        trace.append("gzip:in")
        status, body = inner(request)
        compressed = b"GZ(" + body + b")"        # stand-in for real compression
        trace.append("gzip:out")
        return status, compressed
    return middleware


def stack(handler, *layers):
    """Compose: layers[0] is OUTERMOST (sees the request first)."""
    app = make_app(handler)
    trace = []
    for layer in reversed(layers):               # wrap inside-out to build...
        app = layer(app, trace)                   # ...an outside-in call order
    return app, trace


def handler(request):
    return 200, f"hello {request.get('user', 'world')}".encode()


def main() -> None:
    print("--- the onion: request descends, response ascends ---")
    app, trace = stack(handler, timing, auth, gzip_body)
    status, body = app({"token": "ok", "user": "alice"})
    print(f"  response : {status}  {body!r}")
    print(f"  order    : {' -> '.join(trace)}")
    print("  every :in precedes its :out, and they nest: timing wraps auth")
    print("  wraps gzip wraps the handler. one function, two hooks (before and")
    print("  after the inner call), and the nesting IS the execution order")

    print("--- short-circuit: an outer layer can stop the descent ---")
    app, trace = stack(handler, timing, auth, gzip_body)
    status, body = app({})                        # no token
    print(f"  response : {status}  {body!r}")
    print(f"  order    : {' -> '.join(trace)}")
    print("  auth rejected on the way DOWN, so gzip and the handler never ran")
    print("  and only timing's :out fired: this is why auth must be OUTSIDE")
    print("  expensive work - it saves the work it rejects")

    print("--- order is semantic: swap two layers, change behaviour ---")
    app1, t1 = stack(handler, gzip_body, timing)  # gzip outside timing
    app1({"user": "x"})
    app2, t2 = stack(handler, timing, gzip_body)  # timing outside gzip
    app2({"user": "x"})
    print(f"  gzip-outside-timing : {' -> '.join(t1)}")
    print(f"  timing-outside-gzip : {' -> '.join(t2)}")
    print("  in the first, timing measures the handler WITHOUT compression; in")
    print("  the second, it measures handler PLUS compression. same layers,")
    print("  different meaning - the stack order is a design decision with")
    print("  performance and security consequences, not a list to shuffle")

    print("--- the rules the onion imposes ---")
    print("  outermost: things that should reject/handle before work (auth,")
    print("    rate limiting, request-id assignment)")
    print("  middle: things that transform (compression, content negotiation)")
    print("  innermost: things measuring the real work (timing the handler)")
    print("  and: a layer that raises must be caught by a layer OUTSIDE it, so")
    print("  the error-handling middleware goes near the top (Chapter 130)")


if __name__ == "__main__":
    main()
