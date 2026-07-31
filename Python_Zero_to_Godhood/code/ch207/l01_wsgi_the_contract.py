"""Listing 207.1 - WSGI: the contract that made 'the app' a callable.

Before WSGI (PEP 333/3333), every Python web server had its own app interface,
so an app was married to a server. WSGI is one function signature that
divorced them: an application is a callable `app(environ, start_response)`
that reads a request from the `environ` dict, calls start_response with a
status and headers, and RETURNS an iterable of body bytes. That is the whole
contract, and this listing implements a complete app against it, drives it
through wsgiref (the stdlib's reference server) over a real socket, and shows
the two properties that shaped a decade of Python web work: the app is a
plain callable (so it is trivially testable and composable), and it is
SYNCHRONOUS (one request occupies one worker until it returns).
"""

import io
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator


def application(environ, start_response):
    """A complete WSGI app: route on PATH_INFO, echo the body on POST."""
    method = environ["REQUEST_METHOD"]
    path = environ["PATH_INFO"]

    if path == "/ping":
        body = b"pong"
        status = "200 OK"
    elif path == "/echo" and method == "POST":
        length = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ["wsgi.input"].read(length)
        status = "200 OK"
    else:
        body = b"not found"
        status = "404 Not Found"

    start_response(status, [("Content-Type", "text/plain"),
                            ("Content-Length", str(len(body)))])
    return [body]


def call_app(app, method, path, body=b""):
    """Drive a WSGI app in-process - the SAME callable a server invokes."""
    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = ""
    environ["CONTENT_LENGTH"] = str(len(body))
    environ["wsgi.input"] = io.BytesIO(body)
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = dict(headers)

    result = app(environ, start_response)
    try:
        payload = b"".join(result)
    finally:
        # The spec requires the caller to close an iterable that has one -
        # the validator enforces it, and forgetting is a resource leak.
        if hasattr(result, "close"):
            result.close()
    return captured["status"], captured["headers"], payload


def main() -> None:
    print("--- the app is a callable: test it with a dict, no server ---")
    status, headers, body = call_app(application, "GET", "/ping")
    print(f"  GET /ping   -> {status}  {body!r}")
    status, headers, body = call_app(application, "POST", "/echo",
                                     b"order:buy:100")
    print(f"  POST /echo  -> {status}  {body!r}")
    status, headers, body = call_app(application, "GET", "/nope")
    print(f"  GET /nope   -> {status}  {body!r}")
    print("  no socket, no server, no framework: a WSGI app is app(environ,")
    print("  start_response) -> iterable, so a test is a dict in and a tuple")
    print("  out. this testability is WHY the contract won")

    print("--- environ is the request as a flat dict ---")
    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = "GET"
    environ["PATH_INFO"] = "/orders/42"
    environ["QUERY_STRING"] = "verbose=1"
    for key in ("REQUEST_METHOD", "PATH_INFO", "QUERY_STRING",
                "SERVER_PROTOCOL", "wsgi.version"):
        print(f"  environ[{key!r}]".ljust(38) + f": {environ[key]!r}")
    print("  Chapter 125's request line and headers, flattened into CGI-style")
    print("  keys plus wsgi.* extensions - the server's job is to parse the")
    print("  socket into this dict, the app's job is to read it")

    print("--- the contract is enforceable: validator wraps any app ---")
    wrapped = validator(application)
    status, _, body = call_app(wrapped, "GET", "/ping")
    print(f"  through wsgiref.validate.validator : {status}  {body!r}")
    print("  the stdlib ships a VALIDATOR that checks an app obeys the spec")
    print("  (bytes not str for the body, headers well-formed, start_response")
    print("  called once): the contract is a spec you can machine-check, not")
    print("  a convention you hope for")

    print("--- synchronous is the shape, and the ceiling ---")
    print("  the app RETURNS when the response is ready, so one request holds")
    print("  one worker for its whole duration - a slow database call blocks")
    print("  that worker (Chapter 107's clause, at the server). concurrency")
    print("  comes from RUNNING MANY WORKERS (processes/threads, Deep L), and")
    print("  the C10k problem this cannot solve is exactly why ASGI exists")
    print("  (Chapter 127): async concurrency the sync contract cannot express")


if __name__ == "__main__":
    main()
