"""Listing 47.1 - a TCP/stream socket is a byte stream, not a message channel.

The single most common networking bug: treating a stream socket as if send()
and recv() exchange whole messages. They do not. A stream socket delivers a
continuous stream of bytes with NO message boundaries: three send() calls can
arrive as one recv(), or one send() can arrive split across several recv()s. To
send discrete messages you must frame them yourself, most simply with a length
prefix. This listing shows the problem and the fix over a socketpair (two
connected sockets in one process, so no network is needed and the output is
deterministic).
"""

import socket
import struct


def main() -> None:
    print("--- the problem: message boundaries are NOT preserved ---")
    a, b = socket.socketpair()
    a.sendall(b"HELLO")            # three logical "messages",
    a.sendall(b"WORLD")            # three send() calls
    a.sendall(b"!!!")
    a.close()                      # EOF after sending
    stream = b""
    while True:
        chunk = b.recv(4096)
        if not chunk:
            break
        stream += chunk
    b.close()
    print(f"  three sends arrived as   : {stream!r}")
    print(f"  boundaries preserved?    : {False} (a stream has none)")

    print("--- the fix: length-prefixed framing ---")
    c, d = socket.socketpair()

    def send_msg(sock, payload):
        sock.sendall(struct.pack(">I", len(payload)) + payload)   # 4-byte length, then body

    def recv_exactly(sock, n):
        buf = b""
        while len(buf) < n:                # recv may return fewer bytes than asked
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("peer closed mid-message")
            buf += chunk
        return buf

    def recv_msg(sock):
        (length,) = struct.unpack(">I", recv_exactly(sock, 4))
        return recv_exactly(sock, length)

    send_msg(c, b"HELLO")
    send_msg(c, b"WORLD")
    send_msg(c, b"!!!")
    messages = [recv_msg(d) for _ in range(3)]
    c.close()
    d.close()
    print(f"  framed messages recovered: {messages}")
    print(f"  recv_exactly loops until it has the full length (recv can short-read)")


if __name__ == "__main__":
    main()
