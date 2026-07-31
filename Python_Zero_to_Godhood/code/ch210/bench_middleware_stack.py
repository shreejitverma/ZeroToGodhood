"""Benchmark 210.1 - what a middleware stack costs, and what short-circuiting saves.

  210.1a  per-layer overhead: dispatch through a bare handler, then through
          stacks of 1, 4, and 8 pass-through middlewares. Each layer is a
          function call around the inner call (Chapter 55), so the cost is
          linear in depth and small - the onion is cheap to make deep.

  210.1b  the short-circuit dividend: a stack whose OUTER layer rejects half
          the requests (auth failure) against one whose rejecting layer is
          INNERMOST. Rejecting early skips every layer below it, so an
          expensive stack pays nothing for the requests it turns away - the
          measured reason auth and rate-limiting go on the outside.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402


def main():
    SETUP = """
def handler(request):
    return 200, b"ok"

def passthrough(inner):
    def mw(request):
        return inner(request)
    return mw

def expensive(inner):
    def mw(request):
        _ = sum(i * i for i in range(200))     # stand-in for real work per layer
        return inner(request)
    return mw

def reject(inner):
    def mw(request):
        if not request.get("ok"):
            return 401, b"no"
        return inner(request)
    return mw

def build(handler, *layers):
    app = handler
    for layer in reversed(layers):
        app = layer(app)
    return app

bare = handler
one = build(handler, passthrough)
four = build(handler, *([passthrough] * 4))
eight = build(handler, *([passthrough] * 8))

# reject OUTSIDE 8 expensive layers vs reject INSIDE them
reject_outer = build(handler, reject, *([expensive] * 8))
reject_inner = build(handler, *([expensive] * 8), reject)
bad = {}
"""
    rows = [
        measure("bare handler", "handler({})", SETUP),
        measure("1 middleware", "one({})", SETUP),
        measure("4 middlewares", "four({})", SETUP),
        measure("8 middlewares", "eight({})", SETUP),
    ]
    report("210.1a  per-layer overhead", rows, baseline="bare handler")

    print()
    rows = [
        measure("reject OUTSIDE 8 expensive", "reject_outer(bad)", SETUP),
        measure("reject INSIDE 8 expensive", "reject_inner(bad)", SETUP),
    ]
    report("210.1b  short-circuit: rejecting a bad request", rows,
           baseline="reject OUTSIDE 8 expensive")

    print()
    print("Reading this. Each middleware is a function call wrapping the inner")
    print("call, so a deep stack costs linearly and cheaply - tens of ns per")
    print("layer (Chapter 55), which is why frameworks stack a dozen without")
    print("thought. 210.1b is the design lesson with a number: when the")
    print("rejecting layer is OUTERMOST, a bad request pays for one layer and")
    print("stops; when it is innermost, the same request pays for all eight")
    print("expensive layers first. Put auth, rate-limiting, and validation on")
    print("the OUTSIDE so the stack does no work for the requests it will")
    print("refuse - the onion's order is not style, it is the difference")
    print("between rejecting an attack for free and paying full price to")
    print("reject it (Chapter 129's short-circuit, measured).")


if __name__ == "__main__":
    main()
