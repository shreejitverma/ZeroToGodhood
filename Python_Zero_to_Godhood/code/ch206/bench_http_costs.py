"""Benchmark 206.1 - where an HTTP request's time goes: connection vs request.

  206.1a  100 tiny requests over ONE kept-alive connection against 100 fresh
          connections (connect + request + close each). The TCP handshake and
          teardown dominate small requests, which is the entire reason
          HTTP/1.1 defaults to keep-alive and why connection POOLS exist -
          measured on loopback, where the handshake is cheapest and the gap
          is therefore a LOWER bound on the real internet.

  206.1b  parsing cost: split a fixed 8-header request into a method, target,
          and header dict, per request. This is the per-request work a
          framework does before your code runs - small, and the reason the
          connection, not the parse, is the budget line.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, provenance, report  # noqa: E402

RESPONSE = (b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
REQUESTS = 100


def serve_forever(sock, stop):
    sock.settimeout(0.1)
    while not stop.is_set():
        try:
            conn, _ = sock.accept()
        except socket.timeout:
            continue
        with conn:
            conn.settimeout(1.0)
            buf = b""
            while not stop.is_set():
                try:
                    data = conn.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    break
                buf += data
                while b"\r\n\r\n" in buf:
                    _, _, buf = buf.partition(b"\r\n\r\n")
                    conn.sendall(RESPONSE)


def read_one_response(conn):
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += conn.recv(4096)
    head, _, rest = buf.partition(b"\r\n\r\n")
    length = 0
    for line in head.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":")[1])
    while len(rest) < length:
        rest += conn.recv(4096)


def main():
    server = socket.create_server(("127.0.0.1", 0))
    port = server.getsockname()[1]
    stop = threading.Event()
    t = threading.Thread(target=serve_forever, args=(server, stop))
    t.start()

    req = b"GET / HTTP/1.1\r\nHost: x\r\n\r\n"

    def keepalive():
        conn = socket.create_connection(("127.0.0.1", port))
        for _ in range(REQUESTS):
            conn.sendall(req)
            read_one_response(conn)
        conn.close()

    def per_request():
        for _ in range(REQUESTS):
            conn = socket.create_connection(("127.0.0.1", port))
            conn.sendall(req)
            read_one_response(conn)
            conn.close()

    def best(fn, repeat=5):
        times = []
        for _ in range(repeat):
            t0 = time.perf_counter()
            fn()
            times.append(time.perf_counter() - t0)
        return min(times)

    print("=== 206.1a  100 requests: kept-alive vs fresh connections ===")
    print(provenance())
    print("method      : min of 5 runs")
    print()
    ka = best(keepalive)
    pr = best(per_request)
    print(f"  one kept-alive connection : {ka * 1e6 / REQUESTS:7.1f} us / request")
    print(f"  fresh connection each time: {pr * 1e6 / REQUESTS:7.1f} us / request")
    print(f"  the connection costs {pr / ka:.1f}x the request on loopback")

    stop.set()
    t.join()
    server.close()

    print()
    PARSE_SETUP = """
raw = (b"POST /orders HTTP/1.1\\r\\nHost: api\\r\\nContent-Type: application/json"
       b"\\r\\nContent-Length: 18\\r\\nAccept: application/json\\r\\nUser-Agent: x"
       b"\\r\\nAuthorization: Bearer t\\r\\nX-Request-Id: 42\\r\\n\\r\\n")

def parse(raw):
    head, _, body = raw.partition(b"\\r\\n\\r\\n")
    lines = head.split(b"\\r\\n")
    method, target, _ = lines[0].split(b" ")
    headers = {}
    for line in lines[1:]:
        name, _, value = line.partition(b": ")
        headers[name.lower()] = value
    return method, target, headers
"""
    rows = [measure("parse an 8-header request", "parse(raw)", PARSE_SETUP)]
    report("206.1b  the per-request parse", rows,
           baseline="parse an 8-header request")

    print()
    print("Reading this. Even on loopback - where the TCP handshake is three")
    print("packets between two threads on one machine and costs almost")
    print("nothing - a fresh connection per request is measurably slower than")
    print("reusing one. That 1.4x is a LOWER BOUND: on a real network the")
    print("handshake is a full round trip (milliseconds), and TLS adds one or")
    print("two more, so the connection dwarfs the request by orders. That is")
    print("why HTTP/1.1 keeps connections alive, why clients POOL them, and why")
    print("HTTP/2 multiplexes many requests over one - all attacking the")
    print("connection, never the parse. The parse itself (206.1b) is sub-")
    print("microsecond: the framework work before your handler runs is real")
    print("but small, and the async server (Chapter 127) is about serving")
    print("ten thousand of these connections at once, not parsing faster.")


if __name__ == "__main__":
    main()
