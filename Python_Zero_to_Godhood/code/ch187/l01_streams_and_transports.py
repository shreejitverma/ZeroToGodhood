"""Listing 187.1 - the I/O layer: selector, transports, streams, one cake.

Chapter 101 put the selector at step 2 of the loop; this chapter is the stack
built on it. Three layers, oldest to newest: the SELECTOR reports readiness;
TRANSPORTS AND PROTOCOLS turn readiness into callbacks (data_received, with
chunking decided by the kernel); and STREAMS turn callbacks back into
awaitables (readline, readexactly) with buffering and backpressure built in.

Everything here runs over real loopback sockets and prints only
chunking-independent facts, so the output is deterministic across the matrix:
byte equality, reader contracts at EOF, and totals rather than chunk counts.
"""

import asyncio


def main() -> None:
    print("--- streams: an echo round trip over a real socket ---")

    async def handle_echo(reader, writer):
        while data := await reader.read(64 * 1024):
            writer.write(data)
            await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def stream_demo():
        server = await asyncio.start_server(handle_echo, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        request = b"ping:" + bytes(range(64)) * 100
        writer.write(request)
        await writer.drain()
        writer.write_eof()
        response = await reader.read()
        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()
        return request, response

    request, response = asyncio.run(stream_demo())
    print(f"  sent {len(request):,} bytes, echoed back identical : "
          f"{response == request}")
    print("  write() buffers, drain() awaits the flow control, read() awaits")
    print("  readiness: the awaitable surface over Chapter 101's selector")

    print("--- reader contracts: framed, exact, and ended ---")

    async def contracts():
        server = await asyncio.start_server(
            lambda r, w: serve_fixed(w), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        async def serve_fixed(writer):
            writer.write(b"line-one\nline-two\nRAWPAYLOAD")
            await writer.drain()
            writer.close()

        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        first = await reader.readline()
        second = await reader.readline()
        raw = await reader.readexactly(10)
        rest = await reader.read()
        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()
        return first, second, raw, rest

    first, second, raw, rest = asyncio.run(contracts())
    print(f"  readline x2   : {first!r}, {second!r}")
    print(f"  readexactly(10): {raw!r}")
    print(f"  read() at EOF : {rest!r}  (empty bytes IS the EOF signal)")
    print("  framing is the reader's job, not the socket's: TCP hands the")
    print("  stack arbitrary chunks, and readline/readexactly reassemble your")
    print("  frames from the stream buffer, suspending only when short")

    print("--- one layer down: transports and protocols ---")

    class CountingEcho(asyncio.Protocol):
        def connection_made(self, transport):
            self.transport = transport
            self.received = 0

        def data_received(self, chunk):
            self.received += len(chunk)     # chunk sizes are the KERNEL'S whim
            self.transport.write(chunk)

        def eof_received(self):
            self.transport.close()

    async def protocol_demo():
        loop = asyncio.get_running_loop()
        server = await loop.create_server(CountingEcho, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]

        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        payload = b"x" * 200_000
        writer.write(payload)
        writer.write_eof()
        echoed = await reader.read()
        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()
        return len(payload), len(echoed)

    sent, echoed = asyncio.run(protocol_demo())
    print(f"  protocol echo, sent == echoed : {sent == echoed} ({sent:,} bytes)")
    print("  data_received fires with whatever chunks the kernel delivers -")
    print("  the count of calls is not printable in a verified book, and any")
    print("  code that assumes one write means one callback is already wrong")

    print("--- the cake, labelled ---")
    print("  selector   : which fds are ready          (Chapter 101, step 2)")
    print("  transport  : buffered writes, flow control, the socket's owner")
    print("  protocol   : callbacks per event: connection_made, data_received")
    print("  streams    : awaitables + framing over a protocol, for humans")
    print("  servers use streams until a profiler says otherwise (Chapter 106's")
    print("  benchmark prices the layers); protocols are for framing-heavy or")
    print("  callback-native designs, not for speed vanity")


if __name__ == "__main__":
    main()
