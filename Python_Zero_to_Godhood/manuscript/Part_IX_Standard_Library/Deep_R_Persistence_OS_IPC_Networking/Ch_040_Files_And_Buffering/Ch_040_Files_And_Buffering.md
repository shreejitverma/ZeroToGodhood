# Chapter 40: Files and Buffering

A logging service writes each log line to a file and flushes it, and under load the service spends most of
its time not computing but *waiting on the disk*. The code looks innocent, `f.write(line)` in a loop, but
someone opened the file line-buffered "so logs appear immediately," and now every newline is a separate
write syscall into the kernel. Switching to the default block buffering, the identical loop, the identical
100,000 writes, runs about **34 times faster**, because the writes are batched into a few dozen ~8 KB
syscalls instead of 100,000 one-line ones. The lines still land; they just do not each pay a trip across
the user/kernel boundary.

That gap is what the `buffering` parameter controls, and understanding it is the difference between an I/O
loop that scales and one that melts under load. This chapter opens **Deep R** (persistence, OS, IPC,
networking) with the file object itself: text versus binary, encoding, the `with`-block contract, and the
buffering that decides how many syscalls your writes become. Chapter 7 covered what text *is* (`str`,
encodings); this chapter covers how it gets to and from disk.

## Section index

- **40.1** The file object: mode, encoding, buffering, `with`
- **40.2** Buffering: user space, kernel, and disk
- **40.3** Measurement: block vs line buffering
- **40.4** Edges and failure modes
- **40.5** Connections
- **40.6** Exercises
- **40.7** Summary and cross-references

Listings live under `code/ch040/` and are re-executed by `make verify` on both interpreters.

---

## 40.1 The file object: mode, encoding, buffering, `with`

```python
# code/ch040/l01_fileio.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- text mode: str in, str out, via an encoding ---
  read back           : 'café\nnaïve\n'
  on disk (bytes)     : b'caf\xc3\xa9\nna\xc3\xafve\n'
--- binary mode: bytes in, bytes out, no encoding ---
  read back           : b'\x00\x01\x02\xff'
--- the buffering parameter: what is batched before a syscall ---
  unbuffered write    : 10 bytes, no batching
  line-buffered       : flushes to the OS on every newline
--- newline translation is a text-mode behavior ---
  newline='' bytes    : b'a\nb\n'
--- with-block guarantees flush + close even on error ---
  StringIO value      : 'in-memory file'
```

`open()` returns a file object layered over an OS file descriptor, and three choices define its behavior.
**Mode**: `'t'` (text, the default) versus `'b'` (binary). In text mode you read and write `str` and the
file applies an **encoding** (`café` becomes the five UTF-8 bytes `caf\xc3\xa9` on disk); in binary mode you
read and write `bytes` and there is no encoding, `b"\x00\x01\x02\xff"` round-trips exactly. Always pass
`encoding=` explicitly for text, relying on the platform default is a portability bug (Chapter 7).

**Buffering** is the `buffering` parameter, and it is the chapter's subject: it decides how much is batched
before a write syscall. **The `with`-block** is the safety contract: it guarantees the buffer is flushed
and the descriptor closed even if the body raises, which is why every file should be opened in a `with`
statement. Text mode also translates newlines (`newline=''` disables it, needed for the `csv` module and
for exact byte control), and `io.StringIO`/`BytesIO` are in-memory files with the same protocol, useful for
tests and for building content without touching disk.

---

## 40.2 Buffering: user space, kernel, and disk

There are three places your data can sit, and three transfers between them, and conflating them is the
source of most I/O performance and durability confusion.

1. **Application buffer -> kernel** is a `write()` *syscall*. Python's file object holds a user-space buffer
   (default ~8 KB in binary, and a text layer on top); when it fills, one syscall hands it to the kernel.
   The `buffering` parameter controls this buffer: the default block-buffers, `buffering=1` line-buffers
   (flush on every newline, text mode only), and `buffering=0` is unbuffered (binary only, every write is a
   syscall). `f.flush()` forces this transfer now.
2. **Kernel page cache -> disk** is durability, forced by `os.fsync(f.fileno())`. Until this happens, the
   data is in the OS's cache and a power loss can lose it, even though the syscall returned.

The chapter-opening bug conflates these: line buffering makes transfer (1) happen per newline (many
syscalls, the cost §40.3 measures), and `flush()`+`fsync()` per line adds transfer (2) per newline (a disk
trip, even more expensive). The right pattern for throughput is to let the buffer batch transfer (1), and
to do transfer (2) deliberately, once per checkpoint, not per record. "Logs appear immediately" almost
never requires either per line.

---

## 40.3 Measurement: block vs line buffering

**Methodology.** `code/ch040/bench_buffering.py`. The *same* loop of 100,000 `f.write(line)` calls, under
default block buffering versus `buffering=1` line buffering. Only the buffering parameter differs. `min`
over repeated runs; no `fsync` (this isolates the syscall-batching effect from durability). File I/O timing
is noisier than in-process microbenchmarks, so the `min` discipline matters here; RSD ran high and the
harness flagged runs machine-busy, which is why the ratio, not the absolute times, is the finding. CPython
3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 100,000 line writes | min per run | per line | ratio |
|---|---|---|---|
| block-buffered (default) | **~5.8 ms** | **~58 ns** | 1.00x |
| line-buffered (`buffering=1`) | **~198 ms** | **~1980 ns** | **~34x** |

Both do the identical 100,000 `write()` calls. Block buffering batches them into a few dozen ~8 KB
syscalls, so the OS sees a few dozen writes and the per-line cost is dominated by the Python call, **~58
ns**. Line buffering issues a `write()` *syscall* on every newline, so the OS sees 100,000 writes, and the
per-line cost is dominated by the syscall, **~1980 ns**, about **34x** more. The difference is entirely the
number of user/kernel crossings.

The rule: **batch writes; do not line-buffer or flush per record unless you truly need each record handed
to the OS immediately.** The times to reach for line buffering or per-write flush are narrow, an
interactive prompt, a log you tail live during a short-lived crash window, and even then it is a
throughput/latency trade you should make on purpose. For bulk output (a report, a data export, high-volume
logs) let the block buffer do its job, and if durability matters, `fsync` once at the end, not per line.

---

## 40.4 Edges and failure modes

**Line buffering or `flush` per record.** §40.3. A syscall per newline is ~34x the batched cost. Use it
only when you truly need each record in the kernel immediately.

**`flush()` is not `fsync()`.** §40.2. `f.flush()` moves data to the *kernel* (out of Python's buffer); it
does *not* guarantee it reached *disk*. For durability across power loss, call `os.fsync(f.fileno())` after
flushing. Conflating the two gives a false sense of durability.

**Missing `encoding=`.** Opening a text file without `encoding=` uses the platform default (UTF-8 on modern
systems, but not guaranteed everywhere, and historically not on Windows). Always pass `encoding="utf-8"`
explicitly (Chapter 7). PEP 686 makes UTF-8 the default in 3.15, but explicit is still correct today.

**Not using `with`.** A file opened without `with` (or an explicit `close()`) relies on the garbage
collector to flush and close it, which is nondeterministic and can lose buffered data or leak descriptors.
Always use `with`.

**`buffering=0` in text mode.** Unbuffered mode is only legal in *binary* mode; `open(path, "w",
buffering=0)` raises `ValueError`. Text mode needs its buffer for the encoding layer.

**Newline translation surprising `csv` and binary-exact writers.** Text mode translates `\n` to the
platform newline on write. For `csv` (which manages its own line endings) and any exact-bytes text output,
open with `newline=''` to disable translation, or you get doubled or wrong line endings.

**Reading a huge file with `.read()`.** `f.read()` loads the whole file into memory. For large files iterate
line by line (`for line in f:`) or read in chunks, exactly the laziness discipline of Chapter 9.

---

## 40.5 Connections

**Backward.** What text *is*, `str` versus `bytes` and the encode/decode boundary the text layer applies,
is Chapter 7. The binary `bytes`/`memoryview` the binary layer moves is Chapter 37. Iterating a file lazily
instead of reading it whole is the generator discipline of Chapter 9. The `with`-block protocol is the
context-manager machinery of Chapter 5.

**Forward.** The rest of **Deep R** builds on this: `pathlib` for paths, `json`/`pickle` for structured
serialization, `sqlite3` for durable structured storage (with its own transaction/`fsync` story), and
`mmap` for memory-mapped file access. The syscall boundary this chapter names is the OS-interface theme of
**Deep R** throughout.

**Across books.** Buffered, explicitly-encoded, `with`-managed file I/O is how Book II reads and writes the
data that crosses into **Book III**. A **Book III** pipeline reading a large corpus iterates files lazily
(not `.read()`), writes outputs in batched blocks (not flushed per record), and `fsync`es at checkpoints,
so ingest throughput is bounded by real work, not by syscalls. The §40.3 measurement is why the ingest loop
does not line-buffer. **Deep U** owns the storage seam.

---

## 40.6 Exercises

**1. Reproduce the buffering gap.** Run §40.3's benchmark and confirm block buffering is ~34x faster than
line buffering for the same write loop. Explain, in terms of syscalls, where the time goes, and why the
line count (not the byte count) drives the line-buffered cost.

**2. Separate flush from fsync.** Write data, `flush()` it, and (before `fsync`) reason about where the data
is (kernel cache, not disk). Then `fsync` and explain what changed for durability. Explain why a benchmark
that flushes but does not fsync measures buffering, not durability.

**3. Encoding round-trip.** Write a string with non-ASCII characters in UTF-8 and read the raw bytes to see
the multi-byte encoding. Then write it in a different encoding and show the bytes differ. Explain why
`encoding=` must be explicit and must match on read and write.

**4. Newline control.** Write `"a\nb\n"` in default text mode and with `newline=''`, and compare the bytes
on a platform where they differ (or reason about Windows). Explain why `csv` requires `newline=''`.

**5. The design question.** Python defaults files to block buffering rather than unbuffered or line-
buffered. Argue why that default is right for most code. Your answer must address the syscall cost the
§40.3 benchmark measures, the durability question buffering does *not* answer (fsync), and the narrow cases
where line buffering or per-write flush actually earns its cost.

---

## 40.7 Summary and cross-references

- `open()` layers a file object over an OS descriptor. Choose **mode** (`'t'`/`'b'`), pass **`encoding=`**
  explicitly for text, and always use a **`with`-block** (it guarantees flush + close).
- **Buffering** decides how writes become syscalls. Default **block buffering** batches into ~8 KB
  syscalls; **line buffering** (`buffering=1`) makes a syscall per newline; **`buffering=0`** (binary only)
  is a syscall per write.
- **`flush()` is not `fsync()`:** flush moves data to the kernel; only `os.fsync` forces it to disk
  (durability).
- **Measured:** the same 100,000-write loop is **~34x faster** block-buffered than line-buffered (~58 ns vs
  ~1980 ns per line), entirely because of the number of user/kernel crossings. Batch writes; flush/fsync
  deliberately, not per record.

**Cross-references.** Text and encodings → Chapter 7. Binary data → Chapter 37. Lazy file iteration →
Chapter 9. Context managers → Chapter 5. `pathlib`, serialization, `sqlite3`, `mmap` → the rest of Deep R.
The storage seam → Deep U.
