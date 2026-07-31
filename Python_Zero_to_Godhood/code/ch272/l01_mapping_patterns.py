"""Listing 272.1 - Python 3.10 (2021): mapping patterns in match/case.

Dispatching on the contents of a dict - a JSON message, a config block, an event
record - was a tangle of `if 'type' in d and d['type'] == ...` checks with
manual key access. Mapping patterns match a value by the KEYS it contains and
bind their values. The defining rule is SUBSET semantics: `{"type": "move"}`
matches any mapping that HAS a 'type' key equal to 'move', regardless of what
OTHER keys it has. That fits real data - messages carry fields you do not care
about - and a **rest capture collects the leftovers. Deep B owns matching; this
chapter is the mapping-pattern facet of the 3.10 release. Verified on current
interpreters.
"""


def handle(event):
    """Dispatch on a dict event by its keys - classic mapping matching."""
    match event:
        case {"type": "move", "x": x, "y": y}:
            return f"move to ({x}, {y})"
        case {"type": "click", "button": button}:
            return f"click with {button}"
        case {"type": "key", "code": code}:
            return f"key {code}"
        case {"type": t}:                        # any dict with a 'type', bind it
            return f"unhandled event type {t!r}"
        case _:
            return "not an event"


def main() -> None:
    print("--- match a dict by the keys it contains, binding the values ---")
    events = [
        {"type": "move", "x": 3, "y": 4},
        {"type": "click", "button": "left"},
        {"type": "key", "code": 27},
    ]
    for e in events:
        print(f"  handle({e}) : {handle(e)}")
    print("  `{'type': 'move', 'x': x, 'y': y}` matches a mapping that has those")
    print("  keys, checks 'type' equals 'move', and binds x and y from their")
    print("  values. dispatch on structure, not a chain of `in` checks")

    print("--- SUBSET semantics: extra keys are allowed ---")
    rich = {"type": "move", "x": 1, "y": 2, "timestamp": 999, "source": "mouse"}
    print(f"  handle({{...move with extra keys...}}) : {handle(rich)}")
    print("  the event has timestamp and source too, but the pattern only names")
    print("  type/x/y - and it STILL matches. a mapping pattern requires the")
    print("  named keys to be PRESENT, not that they are the ONLY keys. real")
    print("  messages always carry fields you ignore, so subset matching is right")

    print("--- a missing named key means NO match ---")
    incomplete = {"type": "move", "x": 5}        # no 'y'
    print(f"  handle({incomplete}) : {handle(incomplete)}")
    print("  this move is missing 'y', so `{'type':'move','x':x,'y':y}` does NOT")
    print("  match - it needs ALL its named keys. it falls to `{'type': t}`,")
    print("  which only requires a 'type'. patterns are ordered specific->general")

    print("--- capture the leftovers with **rest ---")
    def split(record):
        match record:
            case {"id": id, **rest}:             # bind id, collect the other keys
                return f"id={id}, other fields={sorted(rest)}"
            case _:
                return "no id"
    r = {"id": 42, "name": "Ada", "role": "admin"}
    print(f"  split({r}) : {split(r)}")
    print("  `{'id': id, **rest}` binds id and collects every OTHER key/value")
    print("  into rest (a dict). the mapping analogue of *rest for sequences -")
    print("  pull out the fields you name, keep the remainder")

    print("--- keys are usually literals; values are full patterns ---")
    def route(msg):
        match msg:
            case {"status": 200, "body": str() as body}:
                return f"ok, body is text of length {len(body)}"
            case {"status": int() as code}:
                return f"status {code}"
        return "unrecognised"
    print(f"  route(200 + text) : {route({'status': 200, 'body': 'hello'})}")
    print(f"  route(404)        : {route({'status': 404})}")
    print("  the KEY is a literal to look up; the VALUE position is a full")
    print("  pattern - a literal (200), a type (int()), a capture, anything. so")
    print("  you match on both which keys exist AND what their values look like")

    print("--- the constraint answered ---")
    print("  dispatching on dict contents was `if 'k' in d and d['k']==...`")
    print("  chains with manual access. mapping patterns (3.10) match by the")
    print("  keys present (subset semantics: extra keys fine, missing named keys")
    print("  fail), bind their values with full sub-patterns, and collect the")
    print("  rest with **. dict dispatch became structural and declarative")


if __name__ == "__main__":
    main()
