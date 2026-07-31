"""Listing 206.1 - HTTP from the socket up: a request is text, a response is text.

Deep V opens where every web framework bottoms out: a TCP socket (Chapter 106)
carrying a text grammar. An HTTP request is a request line, headers, a blank
line, and an optional body; a response is a status line, headers, a blank
line, and a body. This listing speaks that grammar BY HAND over a real
loopback socket - no http.client, no framework - so the protocol has nowhere
to hide, then shows the one rule that makes framing possible (Content-Length
or chunked, because a stream has no natural end) and the parser's own
security edges. Deterministic: only structural facts are printed.
"""

import socket
import threading


def raw_server(sock, response_body):
    """A one-shot server that reads a request and returns a fixed response."""
    conn, _ = sock.accept()
    with conn:
        request = b""
        while b"\r\n\r\n" not in request:            # headers end at blank line
            request += conn.recv(4096)
        header_blob, _, _ = request.partition(b"\r\n\r\n")
        conn.sendall(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/plain\r\n"
            b"Content-Length: " + str(len(response_body)).encode() + b"\r\n"
            b"Connection: close\r\n"
            b"\r\n" + response_body)
    return header_blob


def main() -> None:
    print("--- a request is a text grammar over a socket ---")
    server = socket.create_server(("127.0.0.1", 0))
    port = server.getsockname()[1]
    captured = {}

    def run():
        captured["request"] = raw_server(server, b"pong")

    t = threading.Thread(target=run)
    t.start()

    client = socket.create_connection(("127.0.0.1", port))
    client.sendall(
        b"GET /ping?n=1 HTTP/1.1\r\n"
        b"Host: 127.0.0.1\r\n"
        b"Accept: text/plain\r\n"
        b"\r\n")
    response = b""
    while chunk := client.recv(4096):
        response += chunk
    client.close()
    t.join()
    server.close()

    req_lines = captured["request"].decode().split("\r\n")
    print(f"  request line   : {req_lines[0]!r}")
    print(f"  header count   : {len(req_lines) - 1}")
    status, _, rest = response.partition(b"\r\n")
    resp_headers, _, body = rest.partition(b"\r\n\r\n")
    print(f"  status line    : {status.decode()!r}")
    print(f"  response body  : {body!r}")
    print("  request line = METHOD SP TARGET SP VERSION; headers are")
    print("  Name: value lines; a blank line ends the head. that is the whole")
    print("  syntax every framework parses back into request objects")

    print("--- the framing rule: a stream has no natural end ---")
    print("  the reader looped recv() until \\r\\n\\r\\n for the head, then must")
    print("  read exactly Content-Length body bytes (or de-chunk a chunked")
    print("  body). without a length, 'the response' and 'the next response'")
    print("  on a kept-alive connection are indistinguishable - which is why")
    print("  Content-Length is mandatory-in-spirit and chunked exists for")
    print("  streaming (Chapter 91's shape, at the protocol layer)")

    print("--- methods and status classes carry the semantics ---")
    print("  GET (safe, idempotent) / POST (neither) / PUT, DELETE (idempotent)")
    print("  2xx success  3xx redirect  4xx YOUR fault  5xx MY fault")
    print("  idempotency is a CONTRACT the network relies on: a proxy may")
    print("  retry a GET or PUT safely and must never retry a POST - the")
    print("  method is a promise about what a repeat does")

    print("--- the parser is an attack surface (flagged, owned by Deep O) ---")
    print("  header injection via CRLF in a value, request smuggling from")
    print("  Content-Length/Transfer-Encoding disagreement, slowloris from")
    print("  never sending the blank line: parsing untrusted protocol text is")
    print("  exactly Chapter 82's ReDoS lesson generalised - validate lengths,")
    print("  bound reads, reject ambiguity, and let a hardened server (not")
    print("  this listing) face the internet")


if __name__ == "__main__":
    main()
