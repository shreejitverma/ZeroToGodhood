# Chapter 289: Zstd

## The constraint

Python's standard library shipped compression for the classic codecs: `gzip`, `bz2`, and `lzma`.
It did not ship Zstandard - `zstd` - the modern compressor developed at Facebook that, over the 2010s, became the *de facto* industry default.
Zstd backs package formats, filesystems, databases, and network protocols across the industry, for one reason: it hits a dramatically better *balance* of speed and ratio than the older codecs.
Its fast levels compress about as well as gzip's best while being far quicker, and its high levels rival `lzma`'s ratio - so it replaced the older codecs almost everywhere performance mattered.

Yet reaching zstd from Python meant installing a third-party wheel.
For a language whose standard library shipped three older compressors, the absence of the one that had become the ecosystem default was a conspicuous gap - the same shape of gap that `tomllib` (Chapter 277) filled for TOML.

The constraint Python 3.14 (2025, PEP 784) answered: **bring the industry-standard compressor into the standard library**, with the familiar compress/decompress API.

This chapter owns no Deep-Volume mechanism; compression is a standard-library capability.
What it owns is the release: the day zstd became batteries-included.

## What shipped

`compression.zstd` provides `compress`/`decompress` with tunable levels and streaming compressor/decompressor classes, matching the shape of the existing compression modules - and 3.14 also gathered `gzip`, `bz2`, and `lzma` under a new `compression` package.
Listing 289.1 shows it on the 3.14 builds (gated to 3.14+, since the module is new), reporting sizes and round-trip correctness rather than raw compressed bytes so the output is stable.

Verified output (CPython 3.14.6):

```text
--- compress() then decompress() round-trips exactly ---
  original size    : 9000 bytes
  decompressed matches original : True
  zstd.compress/decompress are a lossless round trip: the bytes you
  get back are byte-for-byte the input. same contract as gzip/lzma,
  now for the modern codec
--- it actually compresses: highly repetitive data shrinks a lot ---
  compressed smaller than original : True
  compression ratio over 10x on this repetitive data : True
  repetitive text (logs, JSON, telemetry) compresses dramatically.
  the exact bytes depend on the zstd version, so we report the RATIO
  band, not a raw size - the point is that it works well
--- the level knob trades ratio against speed ---
  a higher level compresses at least as small : True
  level is the speed/ratio dial (roughly 1..22): low is fast with a
  looser ratio, high spends CPU for smaller output. zstd's whole appeal
  is that even its FAST levels beat the old codecs' ratios at speed
--- the API mirrors gzip/lzma, so it drops into existing code ---
  zstd has compress()   : True
  zstd has decompress() : True
  and streaming compressor classes exist : True
  same shape as the other compression modules, so swapping a codec is
  a near drop-in. 3.14 also gathered gzip/bz2/lzma under the new
  `compression` package alongside zstd
--- the constraint answered ---
  zstd is the industry-standard modern compressor - better speed/ratio
  than gzip/bzip2/lzma - yet reaching it from Python needed a third-
  party package. compression.zstd (3.14, PEP 784) put it in the stdlib
  with the familiar compress/decompress API and level tuning. the
  default compressor of the ecosystem is finally batteries-included
```

## Why each part answers the constraint

**Lossless round trip.**
The first block shows `zstd.compress(data)` followed by `zstd.decompress(...)` returning the input byte-for-byte.
This is the fundamental contract - lossless compression - and it is the same contract as `gzip` and `lzma`, now available for the modern codec.

**It compresses well.**
The second block shows the payoff on repetitive data - the logs, JSON, and telemetry that make up so much of what programs actually compress: the output is much smaller than the input, over a 10x ratio here.
The listing reports the ratio *band* rather than an exact size, because the precise compressed bytes depend on the zstd library version; the point is that it works, and works well.

**The level dial.**
The third block shows the speed/ratio knob: a higher level compresses at least as small as a lower one.
`level` (roughly 1 to 22) is the trade - low is fast with a looser ratio, high spends CPU for smaller output.
Zstd's defining appeal is that even its *fast* levels beat the older codecs' ratios at comparable or better speed, which is why it displaced them.

**Familiar API.**
The fourth block shows `zstd` mirroring the other compression modules: `compress`, `decompress`, and streaming compressor classes.
This matching shape means swapping a codec - `gzip` to `zstd`, say - is nearly a drop-in change.
And 3.14 organized `gzip`, `bz2`, and `lzma` under the new `compression` package alongside `zstd`, giving the compression codecs a coherent home.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; `compression.zstd` is a standard-library binding to the zstd library.
What the timeline records is the release act: in 3.14, PEP 784 added `compression.zstd` and reorganized the compression modules under a `compression` package.
The modern consequence, verified above, is that the ecosystem's default compressor is now in the standard library with a familiar API, so Python code can produce and consume zstd - the format package managers, databases, and filesystems already speak - without a third-party dependency.

## Where this lands

`compression.zstd` closed the gap between Python's standard library and the compression format the rest of the industry had standardized on.
Reach for it when you compress data and want the modern speed/ratio balance - logs, telemetry, serialized payloads, cache entries, anything where the older codecs were the only stdlib option before.
Tune `level` to your speed/size needs, use the streaming classes for large or incremental data, and note that the reorganized `compression` package is where the codecs now live.
Remember the compatibility direction: this requires 3.14+, so code supporting older Pythons still needs the third-party binding.
No Deep Volume owns a compression mechanism; this chapter is the record of the release that made the industry-standard compressor batteries-included.
