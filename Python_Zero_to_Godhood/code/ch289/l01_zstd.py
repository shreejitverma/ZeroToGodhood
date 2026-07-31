# requires: 3.14+
"""Listing 289.1 - Python 3.14 (2025): compression.zstd, Zstandard in the standard library.

The stdlib shipped gzip, bzip2, and lzma - but not Zstandard (zstd), the modern
compressor that became the default across the industry (it backs many package
formats, filesystems, and databases) because it hits a far better speed/ratio
balance than the older codecs. Using it from Python meant a third-party wheel.
Python 3.14's PEP 784 added compression.zstd (and folded the existing modules
under a new `compression` package): compress() and decompress() with tunable
levels, matching the gzip/lzma API shape. Deep volumes own no compression
mechanism; this is the release that brought the industry-standard compressor into
the standard library. This listing reports sizes and round-trip correctness (not
raw compressed bytes), so it is stable. Verified on 3.14 builds.
"""

from compression import zstd


def main() -> None:
    # Repetitive, compressible data - like real logs or JSON.
    data = (b"the quick brown fox jumps over the lazy dog. " * 200)
    original_size = len(data)

    print("--- compress() then decompress() round-trips exactly ---")
    compressed = zstd.compress(data)
    restored = zstd.decompress(compressed)
    print(f"  original size    : {original_size} bytes")
    print(f"  decompressed matches original : {restored == data}")
    print("  zstd.compress/decompress are a lossless round trip: the bytes you")
    print("  get back are byte-for-byte the input. same contract as gzip/lzma,")
    print("  now for the modern codec")

    print("--- it actually compresses: highly repetitive data shrinks a lot ---")
    ratio = original_size / len(compressed)
    print(f"  compressed smaller than original : {len(compressed) < original_size}")
    print(f"  compression ratio over 10x on this repetitive data : {ratio > 10}")
    print("  repetitive text (logs, JSON, telemetry) compresses dramatically.")
    print("  the exact bytes depend on the zstd version, so we report the RATIO")
    print("  band, not a raw size - the point is that it works well")

    print("--- the level knob trades ratio against speed ---")
    fast = zstd.compress(data, level=1)          # fast, lower ratio
    high = zstd.compress(data, level=19)         # slow, higher ratio
    print(f"  a higher level compresses at least as small : "
          f"{len(high) <= len(fast)}")
    print("  level is the speed/ratio dial (roughly 1..22): low is fast with a")
    print("  looser ratio, high spends CPU for smaller output. zstd's whole appeal")
    print("  is that even its FAST levels beat the old codecs' ratios at speed")

    print("--- the API mirrors gzip/lzma, so it drops into existing code ---")
    print(f"  zstd has compress()   : {hasattr(zstd, 'compress')}")
    print(f"  zstd has decompress() : {hasattr(zstd, 'decompress')}")
    print(f"  and streaming compressor classes exist : "
          f"{hasattr(zstd, 'ZstdCompressor')}")
    print("  same shape as the other compression modules, so swapping a codec is")
    print("  a near drop-in. 3.14 also gathered gzip/bz2/lzma under the new")
    print("  `compression` package alongside zstd")

    print("--- the constraint answered ---")
    print("  zstd is the industry-standard modern compressor - better speed/ratio")
    print("  than gzip/bzip2/lzma - yet reaching it from Python needed a third-")
    print("  party package. compression.zstd (3.14, PEP 784) put it in the stdlib")
    print("  with the familiar compress/decompress API and level tuning. the")
    print("  default compressor of the ecosystem is finally batteries-included")


if __name__ == "__main__":
    main()
