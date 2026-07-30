"""Benchmark 187.1 - the I/O layers priced: throughput, read sizes, round trips.

187.1a  bulk throughput over loopback: 100 MB through an asyncio streams
        echo, against the same transfer over blocking sockets with a thread
        as the echo side. This prices the whole asyncio stack, selector,
        transport, protocol, stream buffer, against read()/sendall() with
        the kernel doing everything.

187.1b  the read-size sweep: the same 100 MB received with read(1 KB) up to
        read(1 MB). Every short read is a potential suspension (Chapter
        102's 27 us unit), so the chunk size decides how many loop trips a
        transfer pays - Chapter 88's batching arithmetic, at the socket.

187.1c  request-response latency at concurrency one: tiny ping-pong round
        trips, streams against blocking sockets. The blocking pair wins on
        raw latency (no loop iteration in the path) - the honest number that
        Chapter 101's handoff table predicts, and the price the loop's
        SCALING (Chapter 101c) is bought with.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

MB = 1024 * 1024
BULK = 100 * MB
ROUNDTRIPS = 5_000


def best(fn, repeat=3):
    return min(fn() for _ in range(repeat))


def blocking_echo_server(sock, chunk=256 * 1024):
    conn, _ = sock.accept()
    with conn:
        while data := conn.recv(chunk):
            conn.sendall(data)


def bench_blocking_bulk():
    server = socket.create_server(("127.0.0.1", 0))
    port = server.getsockname()[1]
    t = threading.Thread(target=blocking_echo_server, args=(server,))
    t.start()
    payload = b"x" * (4 * MB)
    received = 0
    with socket.create_connection(("127.0.0.1", port)) as c:
        def drain():
            nonlocal received
            while received < BULK:
                received += len(c.recv(256 * 1024))
        t0 = time.perf_counter()
        d = threading.Thread(target=drain)
        d.start()
        for _ in range(BULK // len(payload)):
            c.sendall(payload)
        d.join()
        dt = time.perf_counter() - t0
    server.close()
    t.join()
    return dt


async def stream_bulk(read_size):
    async def echo(reader, writer):
        while data := await reader.read(1 * MB):
            writer.write(data)
            await writer.drain()
        writer.close()

    server = await asyncio.start_server(echo, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    payload = b"x" * (4 * MB)

    async def send():
        for _ in range(BULK // len(payload)):
            writer.write(payload)
            await writer.drain()

    received = 0
    t0 = time.perf_counter()
    sender = asyncio.ensure_future(send())
    while received < BULK:
        received += len(await reader.read(read_size))
    dt = time.perf_counter() - t0
    await sender
    writer.close()
    server.close()
    await server.wait_closed()
    return dt


def bench_blocking_latency():
    server = socket.create_server(("127.0.0.1", 0))
    port = server.getsockname()[1]
    t = threading.Thread(target=blocking_echo_server, args=(server,))
    t.start()
    with socket.create_connection(("127.0.0.1", port)) as c:
        t0 = time.perf_counter()
        for _ in range(ROUNDTRIPS):
            c.sendall(b"ping")
            c.recv(64)
        dt = time.perf_counter() - t0
    server.close()
    t.join()
    return dt


async def stream_latency():
    async def echo(reader, writer):
        while data := await reader.read(64):
            writer.write(data)
            await writer.drain()
        writer.close()

    server = await asyncio.start_server(echo, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    t0 = time.perf_counter()
    for _ in range(ROUNDTRIPS):
        writer.write(b"ping")
        await writer.drain()
        await reader.read(64)
    dt = time.perf_counter() - t0
    writer.close()
    server.close()
    await server.wait_closed()
    return dt


def main():
    print("=== 187.1a  100 MB through a loopback echo ===")
    print(provenance())
    print("method      : min of 3 runs per row")
    print()
    b = best(bench_blocking_bulk)
    s = best(lambda: asyncio.run(stream_bulk(256 * 1024)))
    print(f"  blocking sockets + thread : {BULK / b / MB:7,.0f} MB/s")
    print(f"  asyncio streams           : {BULK / s / MB:7,.0f} MB/s")

    print()
    print("=== 187.1b  the read-size sweep (asyncio streams) ===")
    for size in (1024, 16 * 1024, 256 * 1024, MB):
        dt = best(lambda s=size: asyncio.run(stream_bulk(s)))
        label = f"{size // 1024} KB" if size < MB else "1 MB"
        print(f"  read({label:>6}) : {BULK / dt / MB:7,.0f} MB/s")

    print()
    print("=== 187.1c  4-byte ping-pong, concurrency one ===")
    lb = best(bench_blocking_latency)
    ls = best(lambda: asyncio.run(stream_latency()))
    print(f"  blocking sockets : {lb / ROUNDTRIPS * 1e6:6.1f} us per round trip")
    print(f"  asyncio streams  : {ls / ROUNDTRIPS * 1e6:6.1f} us per round trip")

    print()
    print("Reading this. Loopback runs at memory speed, so the asyncio")
    print("stack's per-byte and per-wakeup costs are fully visible: about a")
    print("3x throughput tax against raw blocking sockets, and 3-4x on")
    print("round-trip latency. On a real network the wire is the bound and")
    print("both taxes disappear into it; on loopback-fast links they are the")
    print("honest price of the layer cake. The sweep is the actionable row:")
    print("small reads multiply loop trips (Chapter 102's suspension unit)")
    print("and halve the pipe, making read-size the cheapest I/O optimisation")
    print("that exists. And concurrency-one latency belongs to blocking")
    print("sockets, as Chapter 101's handoff table predicted - the loop's")
    print("business is ten thousand sockets, not the lowest latency on one.")


if __name__ == "__main__":
    main()
