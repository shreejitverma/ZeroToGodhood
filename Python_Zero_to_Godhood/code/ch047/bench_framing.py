"""Benchmark 47.1 - many small sends vs few large sends: a syscall per send().

Sending the same 1 MB total over a socketpair, as many tiny send()s versus a few
large ones. Each sendall of a small buffer is (at least) one send() syscall, so
1 MB in 64-byte pieces is ~15,600 syscalls, while 1 MB in 64 KB pieces is ~16.
For a stream socket the cost is dominated by the per-send syscall, the same
user/kernel-crossing story as file buffering (Chapter 40). A background thread
drains the receiving end so the send side never blocks; join has a timeout so
this can never hang.

This benchmark does its own timing (it needs a draining thread), so it does not
use the harness measure(). min is the headline. See _harness/bench.py.
"""

import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

TOTAL = 1_000_000


def run_once(chunk_size):
    a, b = socket.socketpair()
    received = [0]

    def drain():
        while True:
            c = b.recv(65536)
            if not c:
                break
            received[0] += len(c)

    t = threading.Thread(target=drain)
    t.start()
    payload = b"x" * chunk_size
    n = TOTAL // chunk_size
    t0 = time.perf_counter()
    for _ in range(n):
        a.sendall(payload)
    a.close()
    dt = time.perf_counter() - t0
    t.join(timeout=5)
    b.close()
    return dt, n


def best(chunk_size, repeat=7):
    times = []
    sends = 0
    for _ in range(repeat):
        dt, sends = run_once(chunk_size)
        times.append(dt)
    return min(times), sends


def main():
    print("=== 47.1  sending 1 MB: many small sends vs few large sends ===")
    print(provenance())
    print()

    big_t, big_n = best(65536)     # ~16 sends of 64 KB
    small_t, small_n = best(64)    # ~15600 sends of 64 B

    print(f"  1 MB in {big_n:>6} sends of 64 KB : {big_t * 1000:>8.2f} ms")
    print(f"  1 MB in {small_n:>6} sends of 64 B  : {small_t * 1000:>8.2f} ms")
    print(f"  ratio (small / big)            : {small_t / big_t:>8.0f}x")

    print()
    print("Reading this. Each sendall of a small buffer is at least one send()")
    print("syscall, so a megabyte in 64-byte pieces is thousands of user/kernel")
    print("crossings, while the same megabyte in 64 KB pieces is a handful. The")
    print("per-send syscall dominates, exactly the file-buffering story (Chapter")
    print("40) on a socket. Batch your writes: build up a buffer (or a framed")
    print("message) and send it in few large calls, not byte-by-byte.")


if __name__ == "__main__":
    main()
