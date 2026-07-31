"""Listing 211.1 - the API boundary: parse, validate, negotiate, serialize, err.

Between the router (Chapter 128) and the handler lies the boundary where
untrusted bytes become trusted objects and back. Four jobs live here, and
skipping any one is a class of bug: PARSE the body into structure, VALIDATE
that structure against a schema (untrusted input is guilty until proven), and
on the way out NEGOTIATE the content type the client asked for and SERIALIZE
to it - with ERRORS themselves being valid, machine-readable responses, not
stack traces. This listing implements a minimal but honest boundary over
stdlib json, showing the round trip, the validation that rejects with a 422
and a field-level reason, and the Accept-driven negotiation.
"""

import json


def validate_order(data):
    """A schema check by hand: types, required fields, ranges. Returns
    (value, errors) - never raises on bad INPUT, only reports."""
    errors = {}
    if not isinstance(data, dict):
        return None, {"": "expected an object"}
    symbol = data.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        errors["symbol"] = "required non-empty string"
    side = data.get("side")
    if side not in ("buy", "sell"):
        errors["side"] = "must be 'buy' or 'sell'"
    qty = data.get("qty")
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        errors["qty"] = "must be a positive integer"
    if errors:
        return None, errors
    return {"symbol": symbol, "side": side, "qty": qty}, {}


def negotiate(accept, available):
    """Pick the best available type for an Accept header (simplified)."""
    wanted = [a.split(";")[0].strip() for a in accept.split(",")]
    for w in wanted:
        if w in available:
            return w
        if w == "*/*":
            return available[0]
    return None                                   # 406: cannot satisfy


def handle(body_bytes, accept):
    """The boundary: parse -> validate -> (handler) -> negotiate -> serialize."""
    try:
        data = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        return error_response(400, "invalid JSON", {"detail": str(exc)}, accept)

    value, errors = validate_order(data)
    if errors:
        return error_response(422, "validation failed", {"fields": errors},
                              accept)

    result = {"accepted": value, "order_id": 1001}   # the "handler"
    return ok_response(result, accept)


def serialize(obj, content_type):
    if content_type == "application/json":
        return json.dumps(obj, separators=(",", ":")).encode()
    if content_type == "text/plain":
        return repr(obj).encode()
    raise ValueError(content_type)


def ok_response(obj, accept):
    ct = negotiate(accept, ["application/json", "text/plain"])
    if ct is None:
        return 406, "text/plain", b"not acceptable"
    return 200, ct, serialize(obj, ct)


def error_response(status, message, extra, accept):
    ct = negotiate(accept, ["application/json"]) or "application/json"
    payload = {"error": message, **extra}
    return status, ct, serialize(payload, ct)


def main() -> None:
    print("--- the happy path: parse, validate, serialize ---")
    status, ct, body = handle(b'{"symbol":"ACME","side":"buy","qty":100}',
                              "application/json")
    print(f"  {status} {ct}")
    print(f"  {body.decode()}")
    print("  untrusted bytes -> validated object -> handler -> json out. the")
    print("  handler never sees an unvalidated field, which is the boundary's")
    print("  whole job (Chapter 128's routing was the first check; this is the")
    print("  deep one)")

    print("--- bad JSON is a 400, with a reason ---")
    status, ct, body = handle(b'{not json', "application/json")
    print(f"  {status} : {body.decode()}")

    print("--- a schema violation is a 422, with FIELD-LEVEL errors ---")
    status, ct, body = handle(b'{"symbol":"","side":"hold","qty":-5}',
                              "application/json")
    print(f"  {status} : {body.decode()}")
    print("  every bad field is named with why: a client can FIX the request")
    print("  from the response. 'validation failed' with no detail is the")
    print("  API equivalent of a bare except - true and useless")

    print("--- content negotiation: the client asks, the server chooses ---")
    for accept in ("application/json", "text/plain", "application/xml"):
        status, ct, body = handle(b'{"symbol":"ACME","side":"buy","qty":1}',
                                  accept)
        print(f"  Accept: {accept:<18} -> {status} {ct}  {body[:40]!r}")
    print("  the same resource, rendered per the client's Accept header; a")
    print("  type the server cannot produce is a 406, not a guess. one")
    print("  handler, many representations - the REST idea made concrete")

    print("--- the boundary's contract, stated ---")
    print("  in:  bytes -> parse (400 on garbage) -> validate (422 on bad")
    print("       shape, field-level) -> typed object the handler trusts")
    print("  out: object -> negotiate (406 if impossible) -> serialize ->")
    print("       bytes, with the right Content-Type")
    print("  errors are RESPONSES: a status class (Chapter 125) plus a")
    print("  machine-readable body, never a leaked traceback (Chapter 124's")
    print("  don't-reveal-internals meets Chapter 129's error middleware)")


if __name__ == "__main__":
    main()
