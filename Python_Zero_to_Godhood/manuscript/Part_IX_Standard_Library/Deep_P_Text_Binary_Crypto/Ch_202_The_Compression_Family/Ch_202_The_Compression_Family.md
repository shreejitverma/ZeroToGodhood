# Chapter 121: The Compression Family

Chapter 120 priced text encoding's expansion; this chapter is the opposite trade. The standard library ships three general-purpose compressors, `zlib`'s DEFLATE, `bz2`'s Burrows-Wheeler, `lzma`'s LZMA, and, more bug-productively, **three framings of one DEFLATE**: zlib-wrapped (`789c...`, adler32 tail), gzip-wrapped (`1f8b` magic, crc32 tail), and raw (`wbits=-15`, no framing at all). The listing prints their leading bytes side by side because the confusion between them, not the algorithms, is what actually ships as bugs, and `decompressobj(wbits=47)`'s auto-detection is named as the defensive reader's setting.

Two laws get demonstrated rather than asserted. **Entropy in, entropy out**: the listing's first draft used a linear byte sequence as "random" and zlib compressed it to 4%, the compressor is an entropy meter that cannot be fooled, and the shipped version uses a sha256 chain, which comes back at **100.1%** and *grows again* (9,011 to 9,022) under a second pass. The corollary is stated where it belongs: compress-then-encrypt is the only order that compresses at all. And **streaming is exact**: chunked `compressobj` output is byte-identical to one-shot, and chunked decompression round-trips, gigabytes through fixed memory, Chapter 91's shape with state carried across feeds.

The benchmark is the money table: DEFLATE **decompresses above 1 GB/s at every level** (ratio bought at write time is free to every reader forever); level 1 keeps 400 MB/s for wire work; level 9 buys two points over 6 at 3.5x cost; **lzma crawls at 6 MB/s writing and reads at 639** (the archive profile, 0.8% on log-like text); and bz2, slow both directions, survives as legacy.

**This is a Deep P chapter.**
Chapter 40 owns file layering (`gzip.open` as a file object); Deep N used `zipfile` as the wheel's container. This chapter owns the compressors themselves: algorithms, framings, streams, and the trade table.

## Section index

- **121.1** The family, the law, the framings, the streams
- **121.2** The model: dictionaries, windows, and wrappers
- **121.3** Measurement: the money table
- **121.4** Edges and failure modes
- **121.5** Connections
- **121.6** Exercises
- **121.7** Summary and cross-references

Listings live under `code/ch202/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 121.1 The family, the law, the framings, the streams

```python
# code/ch202/l01_compression_family.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- one compressible payload (9,000 bytes), the family ---
  zlib level 1 :   130 bytes ( 1.4%)
  zlib level 6 :    96 bytes ( 1.1%)
  zlib level 9 :    96 bytes ( 1.1%)
  bz2          :   139 bytes ( 1.5%)
  lzma         :   152 bytes ( 1.7%)
  levels trade time for ratio INSIDE one algorithm; algorithms
  trade differently (the benchmark prices the time axis). on this
  highly repetitive payload even level 1 finds the structure
--- the law: entropy in, entropy out ---
  entropy bytes, level 9 : 9,011 bytes for 9,000 in (100.1%)
  compressing the compressed : 9,011 -> 9,022 bytes (grew)
  incompressible input comes back larger (framing overhead), and
  compressed output is itself near-entropy, so a second pass only
  adds wrapper bytes. corollary: 'compress then encrypt' is the
  only order that compresses at all - ciphertext is entropy too
--- three framings of one DEFLATE ---
  zlib : starts 789c  (96 B)   2-byte header, adler32 tail
  gzip : starts 1f8b  (108 B)   file header (magic 1f8b), crc32 tail
  raw  : starts edca  (90 B)   no framing at all (wbits=-15)
  same DEFLATE inside; the wrappers differ in header, checksum,
  and negotiation - HTTP 'deflate' historically meant either of
  two of these, and zlib.decompressobj(wbits=47) auto-detects
  zlib-or-gzip, which is the defensive reader's setting
--- streaming: chunked in, chunked out, byte-identical ---
  chunked compress == one-shot : True
  chunked decompress round-trips : True
```

**The family table on a tiny repetitive payload shows the ordering, not the truth.**
Nine thousand bytes of one repeated sentence: even level 1 finds the structure, levels 6 and 9 tie, and the heavyweight algorithms *lose* to zlib because their framing overhead dominates at this size. Ratios only mean something at scale on realistic data, which is exactly why §121.3 exists, and the listing's own caption redirects there.

**The entropy block carries its confession in the code.**
`entropy_bytes`' docstring records the first draft's failure: `(i*197+91) % 256` "looked random" and compressed to 4%. The sha256 chain does not, 100.1%, framing overhead as pure growth, and the double-compression line completes the law: compressed output is near-entropy, so second passes buy only wrapper bytes. Every "zip the zip" pipeline and every encrypt-before-compress design fails against this block.

**The framings block is three first-bytes that resolve years of interop pain.**
`789c` (zlib), `1f8b` (gzip), neither (raw): same DEFLATE inside, different headers, checksums, and negotiation, and HTTP's `deflate` token historically meant either of two of them, which is why robust readers use the auto-detecting `wbits=47` and why "it decompresses locally but not from the server" is always this block.

**And the streaming equalities are the license for pipelines**: `compressobj` chunked at 512 bytes equals one-shot *byte-for-byte*, and a decompressor fed arbitrary splits round-trips. State lives in the object, memory stays fixed, and `gzip.open` wraps the same machinery in Chapter 40's file layering.

---

## 121.2 The model: dictionaries, windows, and wrappers

**DEFLATE is LZ77 plus Huffman**: back-references into a sliding window (32 KB) replace repeats, then symbol frequencies get entropy-coded. The *level* dial spends effort searching for better back-references, which is why it moves compression cost a lot, ratio somewhat, and decompression cost almost nothing, decoding a reference is cheap regardless of how hard it was found. That asymmetry is §121.3's first rule, and the 32 KB window is why repeats farther apart than that compress as if unseen (and why `zdict` priming exists for many-small-similar-payload protocols).

**bz2 and lzma are different bets.**
Burrows-Wheeler (bz2) block-transforms then entropy-codes, symmetric-ish and superseded in practice. LZMA is LZ77's idea with a huge window (up to gigabytes), range coding, and heavy modelling: spectacular ratios on structured data, expensive to compress, *reasonable* to decompress, the distribution-artifact profile (`.xz`, sdists), with memory footprints (dictionary size) that are part of the format's parameters and can surprise small machines.

**Framings answer "who checks, and how do we meet?"**
zlib's wrapper: minimal header (window bits), adler32, for protocols that negotiate out-of-band. gzip's: magic, flags, optional filename/mtime, crc32+length, for *files*, self-identifying on disk. Raw: nothing, for containers that carry their own metadata, which is exactly zipfile's case (Chapter 109's wheels store raw DEFLATE per entry; the archive's central directory is the framing). Choosing a framing is declaring where integrity and identification live; double-checking (crc in gzip *and* your own hash, Chapter 114) is fine and common.

**The streaming objects are the composition surface.**
`compressobj`/`decompressobj` (and bz2/lzma's equivalents) accept feeds and return what is ready; `flush` has modes (`Z_SYNC_FLUSH` to emit a byte-aligned point mid-stream, the websocket/per-message trick, vs finalising). Everything above, `gzip.open`, `tarfile`'s compressed modes, HTTP bodies, is these objects behind a fitting interface, and knowing that collapses the family's API surface to one pattern.

---

## 121.3 Measurement: the money table

**Methodology.** `code/ch202/bench_compression_trades.py`.
10 MB of log-like text (repeated structure, varying fields, the realistic middle between the listing's extremes); `min` of 3 per cell; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| codec | ratio | compress | decompress |
|---|---|---|---|
| zlib -1 | 15.1% | 400 MB/s | 1,174 MB/s |
| zlib -6 | 10.4% | 171 MB/s | 1,418 MB/s |
| zlib -9 | 8.3% | 49 MB/s | 1,332 MB/s |
| bz2 | 4.0% | 20 MB/s | 114 MB/s |
| lzma | **0.8%** | 6 MB/s | 639 MB/s |

**Rule one: DEFLATE reads above a gigabyte per second at every level.**
Ratio bought at write time is free to every reader forever, the compress-once-read-many rule in one column, and the reason logs, wheels, and HTTP responses deflate by default.

**Rule two: the level dial has a shape.**
Level 1 keeps 400 MB/s, wire-protocol territory, giving up five ratio points; 9 buys two points over 6 at 3.5x the write cost, a batch-job trade only. The default is the default for a reason, and tuning away from it should quote this table's columns, not folklore.

**Rule three: the heavies split.**
lzma's 0.8% on structured text is why distribution artifacts went `.xz`, and its 639 MB/s *read* speed means consumers barely pay, all its cost sits with the producer, the correct place for archives. bz2 is slow in both directions and survives as a legacy format to read, not a choice to make. (GIL note for this volume's matrix: all these C cores release the GIL during work, so compression threads scale on every build, one of the oldest Chapter 80 wins in the stdlib.)

**Book I** adds zstd and lz4 to the same table and the frontier moves, but the *shape* survives translation exactly: read-cheap, write-priced, level-dials with knees, and archives versus wires as different professions.

---

## 121.4 Edges and failure modes

**Framing mismatches are the family's number-one bug.** §121.1.
zlib-vs-gzip-vs-raw errors present as `incorrect header check` or garbage; the defensive read is `wbits=47` (auto zlib/gzip) or explicit raw when the container owns framing. Name the framing in every protocol document.

**Decompression bombs are an input-validation problem.**
A few KB can decompress to gigabytes; anything decompressing untrusted data must bound output (`decompressobj().decompress(data, max_length)` loops, or `lzma`'s filters caps) and treat "still more output" as a decision, not a surprise. The streaming interface is the safety interface.

**`zlib.crc32`/adler32 are integrity against noise, not adversaries.**
Chapter 120's CRC note applies verbatim; the family's checksums detect corruption, and content trust remains Chapter 122's digests (wheels carry both: gzip-member CRCs and RECORD sha256s, different jobs).

**Concatenated gzip members are legal and half-supported.**
`gzip` files may be several members back-to-back (log rotation appends); `gzip.open` reads them all, raw `zlib.decompressobj` stops at the first, check `.eof` and `.unused_data`, which is also the multi-stream detection idiom.

**`mtime` in gzip headers breaks reproducibility.**
`gzip.compress(data)` stamps the current time into the header, two runs differ by bytes, the Deep N lesson (Chapter 114's byte-identical artifacts) recurring one layer down. `gzip.compress(data, mtime=0)` (or the `GzipFile` argument) is the reproducible spelling; the listing's zlib-based demos dodge it because zlib's framing carries no time.

**Text must become bytes first, and the pair must agree.**
Compressors eat bytes; the encode step (Deep D) is part of the format contract, and utf-8-then-deflate at one end with latin-1 assumptions at the other corrupts *after* a successful decompress, the errors arrive one layer late.

**And `Z_SYNC_FLUSH` costs ratio.**
Flushing at every message boundary (interactive protocols) emits alignment overhead and resets match opportunities; the trade is latency versus ratio, made explicit per protocol (websocket permessage-deflate's parameters are exactly this dial).

---

## 121.5 Connections

**Backward.**
Encoding's expansion, the trade this chapter reverses, Chapter 120. File layering (`gzip.open`), Chapter 40; the wheel's zipfile container carrying raw DEFLATE per entry, Chapter 109; byte-reproducibility of artifacts, Chapter 114; streams and fixed memory, Chapter 91; GIL release during C work, Chapter 80.

**Forward.**
Digests over compressed artifacts and the two-checksums-two-jobs point, Chapter 122. Compress-then-encrypt's ordering, restated where encryption lives, Chapter 124. Tar-and-compress composition belongs to Deep R's archive handling.

**Across books.**
**Book I** benchmarks zstd/lz4/deflate with the same three rules and adds dictionaries-as-deployment-artifacts; the shared system compresses its wire protocol with a low level and its archives with a high one, per this chapter's table, decided once, in both languages, from one measurement file.

---

## 121.6 Exercises

**1. Frame forensics.** Collect five compressed artifacts from your own systems (HTTP body, wheel entry, `.gz` log, git object, PNG); identify each framing from leading bytes and container docs.

**2. Bound a bomb.** Write the safe decompressor: max output, max ratio, streaming, with tests including a crafted 10,000:1 input. Measure its overhead against naive `decompress` on honest data.

**3. Prime a dictionary.** For 10,000 similar small JSON messages, measure per-message DEFLATE with and without a shared `zdict` built from samples. Report ratio and the operational cost of shipping the dictionary.

**4. Reproduce the artifact.** Make `gzip.compress` output byte-identical across runs and machines; verify with sha256; state every field you had to pin (Chapter 114's discipline, one layer down).

**5. The level sweep on your data.** Re-run §121.3 on a corpus you actually ship; find your knee, and write the two-line policy (wire level, archive level) the sweep justifies.

**6. The design question.** The stdlib froze at deflate/bz2/lzma while zstd became the industry's workhorse (better ratios at deflate speeds, dictionaries, frames). Argue the inclusion question: the maintenance bar for a compression format in the stdlib (decades of format stability, security surface of decoders), the cost of absence (everyone vendors bindings), and what the `hashlib`-style approach (guaranteed algorithms plus OpenSSL passthrough) would look like for compression. Then check what PEPs exist and why the answer has been "not yet".

---

## 121.7 Summary and cross-references

- **Three algorithms, three framings**: DEFLATE inside zlib (`789c`, adler32), gzip (`1f8b`, crc32, file metadata), or raw (`wbits=-15`, container-framed); the confusions are the bug class, and `wbits=47` is the defensive reader.
- **The law, demonstrated**: entropy in, entropy out, a sha256 chain compresses to 100.1% and grows on the second pass; the first draft's "looks random" sequence compressed to 4% and was kept as the docstring's warning. Compress, *then* encrypt.
- **Streams are exact**: chunked equals one-shot byte-for-byte; state lives in the objects; gigabytes flow through fixed memory, and everything higher is these objects in Chapter 40's clothing.
- **The money table**: DEFLATE reads >1 GB/s at every level (spend at write time); level 1 = 400 MB/s wire work, 9 buys 2 points at 3.5x over 6; **lzma: 0.8% ratio, 6 MB/s write, 639 MB/s read**, the archive profile; bz2 legacy. C cores release the GIL, compression threads scale everywhere.
- **The edges that ship**: bombs need bounded streaming reads; gzip's `mtime` breaks reproducibility (`mtime=0`); concatenated members; checksums are anti-noise, not anti-adversary; and the text/bytes contract sits under everything.

**Cross-references.** Encoding's expansion → Chapter 120. File layering → Chapter 40. Wheels' raw-DEFLATE entries → Chapter 109. Reproducible artifacts → Chapter 114. Streams → Chapter 91. GIL release → Chapter 80. Digests → Chapter 122. Encryption ordering → Chapter 124.
