"""Listing 202.1 - the compression family: one payload, three algorithms, three framings.

Chapter 120 priced the 4/3 expansion of text encoding; this chapter is the
other direction. The stdlib ships three general-purpose compressors (zlib's
DEFLATE, bz2's Burrows-Wheeler, lzma's LZMA) and three FRAMINGS of DEFLATE
(raw, zlib-wrapped, gzip-wrapped) whose confusion causes more bugs than the
algorithms ever will. The listing measures ratios deterministically on a
fixed payload, distinguishes the framings by their leading bytes, proves the
streaming interfaces chunk-safe (Chapter 91's shape), and states the law the
random-data row enforces: entropy in, entropy out.
"""

import bz2
import gzip
import hashlib
import lzma
import zlib

TEXT = (b"the quick brown fox jumps over the lazy dog. " * 200)


def entropy_bytes(n: int) -> bytes:
    """Deterministic incompressible bytes: a sha256 chain (a first draft used
    a linear sequence and zlib compressed it to 4% - 'looks random' is not
    'is random', and the compressor is an entropy meter that cannot be fooled)."""
    out, block = [], b"seed"
    while sum(len(b) for b in out) < n:
        block = hashlib.sha256(block).digest()
        out.append(block)
    return b"".join(out)[:n]


RANDOM = entropy_bytes(len(TEXT))


def main() -> None:
    print(f"--- one compressible payload ({len(TEXT):,} bytes), the family ---")
    for name, packed in (("zlib level 1", zlib.compress(TEXT, 1)),
                         ("zlib level 6", zlib.compress(TEXT, 6)),
                         ("zlib level 9", zlib.compress(TEXT, 9)),
                         ("bz2", bz2.compress(TEXT)),
                         ("lzma", lzma.compress(TEXT))):
        print(f"  {name:<13}: {len(packed):>5,} bytes "
              f"({len(packed) / len(TEXT):5.1%})")
    print("  levels trade time for ratio INSIDE one algorithm; algorithms")
    print("  trade differently (the benchmark prices the time axis). on this")
    print("  highly repetitive payload even level 1 finds the structure")

    print("--- the law: entropy in, entropy out ---")
    packed = zlib.compress(RANDOM, 9)
    print(f"  entropy bytes, level 9 : {len(packed):,} bytes for "
          f"{len(RANDOM):,} in ({len(packed) / len(RANDOM):6.1%})")
    twice = zlib.compress(packed, 9)
    print(f"  compressing the compressed : {len(packed):,} -> {len(twice):,}"
          f" bytes (grew)")
    print("  incompressible input comes back larger (framing overhead), and")
    print("  compressed output is itself near-entropy, so a second pass only")
    print("  adds wrapper bytes. corollary: 'compress then encrypt' is the")
    print("  only order that compresses at all - ciphertext is entropy too")

    print("--- three framings of one DEFLATE ---")
    z = zlib.compress(TEXT)
    g = gzip.compress(TEXT)
    raw = zlib.compressobj(wbits=-15)
    r = raw.compress(TEXT) + raw.flush()
    print(f"  zlib : starts {z[:2].hex()}  ({len(z):,} B)   2-byte header,"
          f" adler32 tail")
    print(f"  gzip : starts {g[:2].hex()}  ({len(g):,} B)   file header"
          f" (magic 1f8b), crc32 tail")
    print(f"  raw  : starts {r[:2].hex()}  ({len(r):,} B)   no framing at all"
          f" (wbits=-15)")
    print("  same DEFLATE inside; the wrappers differ in header, checksum,")
    print("  and negotiation - HTTP 'deflate' historically meant either of")
    print("  two of these, and zlib.decompressobj(wbits=47) auto-detects")
    print("  zlib-or-gzip, which is the defensive reader's setting")

    print("--- streaming: chunked in, chunked out, byte-identical ---")
    compressor = zlib.compressobj()
    chunks = [compressor.compress(TEXT[i:i + 512])
              for i in range(0, len(TEXT), 512)]
    chunks.append(compressor.flush())
    streamed = b"".join(chunks)
    print(f"  chunked compress == one-shot : {streamed == zlib.compress(TEXT)}")
    decompressor = zlib.decompressobj()
    out = b"".join(decompressor.decompress(piece)
                   for piece in (streamed[:100], streamed[100:]))
    print(f"  chunked decompress round-trips : {out == TEXT}")
    print("  compressobj/decompressobj carry state across feeds: gigabytes")
    print("  flow through fixed memory (Chapter 91), and gzip.open wraps the")
    print("  same machinery as a file object (Chapter 40's layering)")


if __name__ == "__main__":
    main()
