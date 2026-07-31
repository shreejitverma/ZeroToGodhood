"""Listing 209.1 - routing: turning a method and a path into a handler.

A gateway (WSGI/ASGI) hands you a method and a path; SOMETHING must map
'GET /orders/42' to the right function with `order_id=42` extracted. That
something is a router, and every framework's router is one of two designs:
a linear list of compiled patterns tried in order (simple, O(routes)), or a
prefix tree / trie (fast, O(path segments)). This listing builds the linear
kind - the one most frameworks actually ship, because routes are few and the
match is cheap - with typed path parameters, and shows the three decisions a
router makes that shape an API: match order, parameter extraction, and what
'no match' vs 'wrong method' mean (404 vs 405, Chapter 125's status classes).
"""

import re


class Route:
    """One compiled route: method, a pattern with {name} or {name:int}, handler."""

    def __init__(self, method, template, handler):
        self.method = method
        self.handler = handler
        self.converters = {}
        regex = "^"
        for part in re.split(r"(\{[^}]+\})", template):
            if part.startswith("{"):
                name, _, kind = part[1:-1].partition(":")
                self.converters[name] = int if kind == "int" else str
                regex += f"(?P<{name}>[0-9]+)" if kind == "int" \
                    else f"(?P<{name}>[^/]+)"
            else:
                regex += re.escape(part)
        self.regex = re.compile(regex + "$")

    def match(self, path):
        m = self.regex.match(path)
        if not m:
            return None
        return {k: self.converters[k](v) for k, v in m.groupdict().items()}


class Router:
    def __init__(self):
        self.routes = []

    def add(self, method, template, handler):
        self.routes.append(Route(method, template, handler))

    def dispatch(self, method, path):
        path_matched = False
        for route in self.routes:                 # linear: first match wins
            params = route.match(path)
            if params is None:
                continue
            path_matched = True
            if route.method == method:
                return 200, route.handler(**params)
        if path_matched:
            return 405, "method not allowed"       # path exists, verb wrong
        return 404, "not found"                    # no such path


def main() -> None:
    router = Router()
    router.add("GET", "/orders/{order_id:int}",
               lambda order_id: f"order {order_id} (int {type(order_id).__name__})")
    router.add("DELETE", "/orders/{order_id:int}",
               lambda order_id: f"cancelled {order_id}")
    router.add("GET", "/users/{name}/orders",
               lambda name: f"orders for {name}")
    router.add("GET", "/health", lambda: "ok")

    print("--- dispatch: method + path -> handler + extracted params ---")
    for method, path in (("GET", "/orders/42"),
                         ("DELETE", "/orders/42"),
                         ("GET", "/users/alice/orders"),
                         ("GET", "/health")):
        status, result = router.dispatch(method, path)
        print(f"  {method:<6} {path:<22} -> {status}  {result}")
    print("  {order_id:int} both MATCHES only digits and CONVERTS the string")
    print("  to an int before your handler sees it - routing is the first")
    print("  layer of validation, and typed params are the cheapest kind")

    print("--- the two failure modes are different status codes ---")
    print(f"  GET /orders/abc  -> {router.dispatch('GET', '/orders/abc')[0]}"
          f"  (int route did not match 'abc' -> no path -> 404)")
    print(f"  POST /orders/42  -> {router.dispatch('POST', '/orders/42')[0]}"
          f"  (path exists, POST not registered -> 405)")
    print(f"  GET /nope        -> {router.dispatch('GET', '/nope')[0]}"
          f"  (no such path -> 404)")
    print("  404 = 'no such resource', 405 = 'that resource, wrong verb':")
    print("  conflating them (returning 404 for a bad method) hides a client")
    print("  bug the status class was designed to name (Chapter 125)")

    print("--- match order is a decision, not an accident ---")
    ambiguous = Router()
    ambiguous.add("GET", "/orders/new", lambda: "the new-order form")
    ambiguous.add("GET", "/orders/{order_id}", lambda order_id: f"order {order_id}")
    print(f"  GET /orders/new  -> {ambiguous.dispatch('GET', '/orders/new')[1]!r}")
    print("  the LITERAL route was registered first, so it wins over the")
    print("  parameter route - reverse the order and '/orders/new' becomes")
    print("  order_id='new'. static-before-dynamic is the rule every router")
    print("  needs, whether by registration order (here) or by trie priority")

    print("--- why linear is usually right, and when it is not ---")
    print("  routes are tens, the regex match is microseconds, so O(routes)")
    print("  is fine for almost every service. a trie (O(segments)) wins only")
    print("  at hundreds-to-thousands of routes or when routing is the proven")
    print("  hot path (Chapter 86) - which for a service that then hits a")
    print("  database is essentially never. the benchmark shows the crossover")


if __name__ == "__main__":
    main()
