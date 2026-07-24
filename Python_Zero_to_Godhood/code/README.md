# code/ — listings, verification, benchmarks

Every code block in Book II's prose comes from a file here, and `make verify` proves it still
produces what the book says it produces.

## Layout

```
code/
  Makefile              entry points
  _harness/
    verify.py           re-runs listings, diffs against expected/<ver>/
    bench.py            measurement: min/median/RSD, provenance, build guards
    interpreters.py     reports whether two builds are timing-comparable
  chNNN/
    lNN_<name>.py       listings, numbered as the chapter numbers them
    bench_<name>.py     benchmarks
    expected/
      3.13/lNN_<name>.out
      3.14/lNN_<name>.out
  seams/
    book1_cpp/          the C++ interop path (Book I)
    book3_index/        the retrieval pipeline (Book III)
  capstone/             the trading system, grown across the book
```

Chapter directories use the **stable ID** from `CANONICAL_TOC.md` (`ch018`), not the chapter's
display number. A chapter can be renumbered in the book without touching this tree.

## Commands

```bash
make verify              # every listing, both interpreters
make verify CH=ch18      # one chapter
make verify-313          # one interpreter
make record              # regenerate expected output  <-- see warning
make bench               # benchmarks
make interpreters        # build fingerprints and comparability
```

### `make record` is deliberately not automatic

Nothing depends on it and it is never run by `verify`. Re-recording expected output is exactly how
a drifted transcript gets silently blessed, so it has to be an explicit act followed by reading the
diff. A change in `expected/` means either the interpreter changed or the listing did, and you
should know which before committing.

## Adding a listing

1. Write `chNNN/lNN_<name>.py`. It must be runnable standalone and print observable output.
2. If it needs a newer interpreter, put `# requires: 3.14+` in the first three lines.
3. `make record CH=chNNN`, then read the diff.
4. Paste the recorded output into the prose as the "Verified output" block.

Output is normalised before comparison: memory addresses become `0xADDR` and file paths become
`<path>`, since neither carries pedagogical content and both vary per run.

## Benchmark conventions

`bench.py` enforces these mechanically so a chapter cannot quietly break them.

- **`min` is the headline statistic.** Microbenchmark noise is one-sided: preemption and
  interrupts can only make a batch slower. The fastest batch is the best estimate of the work's
  cost. Median and RSD are reported as diagnostics for how quiet the machine was.
- **Every table carries its provenance**: interpreter version, `OPT`, computed gotos, PGO/LTO,
  GIL state, CPU, platform.
- **Ratios are within-interpreter only.** Comparing timings across two differently-configured
  builds measures the builds. `make interpreters` tells you whether a comparison is legitimate;
  on this machine 3.13 and 3.14 are **not** comparable (`OPT` and `USE_COMPUTED_GOTOS` differ).
- **One decimal place.** Repeated runs reproduce a ratio to about 10%, so cite "about 2.7x", never
  "2.70x".

To compare CPython versions properly, build both from source with identical flags. Until that
exists, report each version's table separately and draw no cross-version conclusion.

## Dependencies

None. Standard library only, and that is a design constraint rather than an accident: a reader
should be able to clone this and run `make verify` without resolving a dependency tree that will
itself have drifted by the time they read the book.
