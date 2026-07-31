# Chapter 119: CSV and the Quoting Grammar

Chapter 118 drew the line where `split(',')` stops being safe; this chapter is the format on the other side of that line. The moment a field can *contain* the delimiter, delimited text acquires a quoting grammar, quotes around fields, quotes doubled inside quotes, newlines legal inside quoted fields, and that grammar cannot be parsed line-by-line or by any regex over lines, which is why `csv.reader` consumes an *iterable of lines* and owns the recombination.

The listing runs the argument as equality checks. The motivating failure: `'widget,"Acme, Inc.",1999'` splits into four fields where there are three, while the reader returns the honest `['widget', 'Acme, Inc.', '1999']`. The round trip: rows containing quotes, commas, and an embedded newline go through writer and reader and come back `== True`, with the wire form printed so the doubling and the mid-field line break are visible. The edges: `DictReader` *describes* ragged rows rather than dropping them (extras under a `None` key, missing as `None`), and the quoting policies differ on exactly one thing worth knowing, `QUOTE_NONNUMERIC` is the only place csv does types.

The benchmark retires the last excuse: the C reader parses the full grammar at **~180 ns a row**, quoted rows cost the *same* as unquoted (1.02x, the state machine prices the grammar, not the quotes), and `DictReader`'s dict-per-row costs 2.85x, an edges-of-the-program convenience, not an inner-loop tool.

**This is a Deep P chapter.**
Chapter 42 (Deep R) owns JSON and pickle, serialisation with types; Deep U owns tabular data at scale. This chapter owns the delimited-text grammar and the module that speaks it.

## Section index

- **119.1** The grammar, exercised
- **119.2** The model: a state machine over an iterable of lines
- **119.3** Measurement: the grammar's price
- **119.4** Edges and failure modes
- **119.5** Connections
- **119.6** Exercises
- **119.7** Summary and cross-references

Listings live under `code/ch200/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 119.1 The grammar, exercised

```python
# code/ch200/l01_csv_and_quoting.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- why split(',') is a correctness bug, not a style choice ---
  the record : widget,"Acme, Inc.",1999
  split(',') : ['widget', '"Acme', ' Inc."', '1999']  <- 4 fields from 3
  csv.reader : ['widget', 'Acme, Inc.', '1999']
  a quoted field may contain the delimiter, the quote (doubled),
  and even newlines - the grammar cannot be regexed line-by-line,
  which is why the reader consumes an ITERABLE of lines, not a line
--- the round trip: writer and reader are inverses ---
  on the wire (escapes visible):
    'name,quote,note'
    'disk,"the ""fast"" one","usable, mostly"'
    'tape,"multi'
    'line",legacy'
  round-trip equality : True
  quotes double inside quotes, embedded newlines survive inside a
  quoted field, and \r\n is the format's native line ending -
  which is why files open with newline='' (the module handles EOLs)
--- dialects: describing the files the world emits ---
  tab-separated : ['a', 'b 1', 'c']
  semicolon+comma-decimal : ['3,14', '2,71']
  Sniffer guessed delimiter : ';'
  delimiter, quotechar, escapechar, quoting policy: a dialect is a
  parser configuration, and Sniffer is a HEURISTIC for unknown
  files - useful interactively, a gamble in pipelines (declare
  your dialect; sniff only what you must)
--- DictReader: rows with names, and the rules at the edges ---
  {'name': 'bolt', 'qty': '3'}
  {'name': 'nut', 'qty': '4', None: ['EXTRA']}
  {'name': 'washer', 'qty': None}
  extra fields land in a None-keyed list (restkey), missing ones
  become None (restval): ragged rows are DESCRIBED, not dropped -
  detecting them is your validation's job, and the None key is
  the tell
--- the quoting policies, on one value ---
  QUOTE_MINIMAL    : "a,b",7,plain
  QUOTE_ALL        : "a,b","7","plain"
  QUOTE_NONNUMERIC : "a,b",7,"plain"
```

**The wire dump is the grammar made visible.**
`"the ""fast"" one"`: quotes escape by doubling, not backslashes. `"multi` ending one physical line and `line"` starting the next: a logical record spanning two physical lines, legal, common in exported spreadsheets, and fatal to every line-oriented shortcut (including reading the file with `splitlines` first). The `round-trip equality : True` line is the module's contract: writer and reader are inverses over arbitrary field content.

**The dialect rows are parser configuration, not new parsers.**
Tab-separated, semicolon-delimited-with-comma-decimals (the European spreadsheet default), and `Sniffer` guessing `';'` from a sample: a *dialect* bundles delimiter, quote character, escaping, and policy. The listing's stance on `Sniffer` is the operational one, a heuristic for unknown files at a prompt, a gamble inside a pipeline; production code declares its dialect.

**And `DictReader`'s ragged-row semantics are description, not repair.**
Extra fields collect under the `None` key; missing fields surface as `None` values. Nothing is dropped and nothing raises, which makes the `None` key the *tell* your validation looks for, ragged input is a data-quality fact the module reports and your code adjudicates.

---

## 119.2 The model: a state machine over an iterable of lines

**The reader is a small state machine**, at each character in one of: outside-field, in-unquoted-field, in-quoted-field, quote-seen-inside-quoted-field (which resolves to either an escaped quote or end-of-field). Records end at a newline *only* in the first two states, which is the whole embedded-newline story, and the machine is implemented in C (`_csv`), which is §119.3's speed story. Every dialect knob parameterises a transition: `delimiter` and `quotechar` are the alphabet, `escapechar` adds a state, `doublequote=False` swaps the escape rule, `strict` decides whether grammar violations raise or get repaired silently.

**The iterable-of-lines interface is a consequence, not a convenience.**
Because a record may span physical lines, the reader must own line recombination, so it takes any iterator of strings, a file, a `StringIO`, a generator decompressing on the fly (Chapter 121's composition), and yields *records*. Two file-mode rules follow: open with `newline=''` so the csv layer, not the io layer, interprets `\r\n` (the format's native ending, which the writer emits); and encode/decode at the file boundary per Deep D, csv is a *text* protocol here, with bytes handled before it.

**The type model is deliberately absent.**
Every field is `str`, except under `QUOTE_NONNUMERIC`, where unquoted fields parse as `float` (and writing requires non-strings to *be* numbers). That single exception is the module's entire type system, and its narrowness is correct: delimited text carries no schema, so types are the consumer's assertion, applied in a validation layer (or by reaching for formats that carry types, Chapter 42's JSON, Deep U's columnar files).

**`DictReader`/`DictWriter` are a naming layer over the same machine**: first row (or `fieldnames`) becomes the schema, rows become dicts, `restkey`/`restval` describe raggedness, and `DictWriter.writeheader` closes the loop. The layer buys self-describing code at a measured dict-per-row price, the classic edges-vs-inner-loop trade this book keeps meeting.

---

## 119.3 Measurement: the grammar's price

**Methodology.** `code/ch200/bench_csv_throughput.py`.
100,000 three-field rows; `min` of 7; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Parsing:**

| parser | time | vs reader |
|---|---|---|
| `split(',')` [wrong] | 5.7 ms | 0.32x |
| `csv.reader`, no quotes | 17.7 ms | 1.00x |
| `csv.reader`, quoted fields | 18.0 ms | **1.02x** |
| `DictReader`, quoted | 50.6 ms | 2.85x |

**b. Writing:** `QUOTE_MINIMAL` 23.3 ms; `QUOTE_ALL` 23.9 ms (**1.02x**).

**The 1.02x rows are the table's teaching.**
The state machine prices the *grammar*, not the quotes: a quoted row transitions through more states but the per-character work is the same C loop, so correctness carries **no per-quote surcharge**. With the full grammar at 3.1x the incorrect split, ~180 ns a row, ~110 ns of which is honest parsing, the split shortcut has no engineering defence left; it was only ever a correctness bug with good latency.

**`DictReader`'s 2.85x is exactly one allocation story**: a dict per row (plus the zip of names to values). The composition advice writes itself: name columns at the boundaries where humans read the code; index positions in the loops where profiles point; and when rows become *millions*, leave csv entirely, this module's ceiling is the on-ramp to Deep U's columnar formats, where types, compression, and vectorised reads live.

**Book I** parses delimited text with the same state machine hand-rolled over `string_view`, hits the same embedded-newline lesson, and its chapter ends at the same ceiling with Arrow where this one ends with Deep U, the format's simplicity is a floor, not a destination, in both languages.

---

## 119.4 Edges and failure modes

**Excel dialects are regional.**
The semicolon delimiter with comma decimals is the default in much of Europe; files cross regions and pipelines guess wrong. Declare dialects per *source*, and treat delimiter detection as data provenance, not parsing.

**`Sniffer` fails confidently.**
It infers from a sample and has no notion of "not CSV at all"; headers of prose, single-column files, and consistent-looking coincidences all mislead it. Interactive use, fine; pipelines, declare (§119.1's stance, promoted to a rule).

**`newline=''` or corrupted round trips.**
Without it, the io layer translates `\r\n`, and quoted fields containing newlines gain phantom `\r`s on some platforms. It is the single most-forgotten argument in the module's use, and the listing's file-free `StringIO` demos dodge it only because memory has no platform.

**Injection: fields beginning with `=`, `+`, `-`, `@`.**
Spreadsheet applications *execute* such fields as formulas on open, csv-injection, a real exfiltration vector for any export fed to Excel. Escaping policy (prefix a `'`) belongs at the export boundary of anything user-generated; the module, correctly, does not decide this for you.

**Very large fields are a memory-shaped denial of service.**
`csv.field_size_limit()` caps a single field (default ~128 KB); untrusted input wants the cap considered, since one unterminated quote can otherwise swallow the file into one "field".

**Round trips preserve text, not meaning.**
`None` writes as empty string and reads back as `''`; `7` writes as `'7'` and reads as `'7'`; dates were never there. Symmetric *typed* round trips need a schema layer of your own or a format with types, the absence is the design, and forgetting it is the source of every "csv corrupted my data" report that is actually "csv preserved my strings".

**And the GIL-era note for this volume's matrix**: the `_csv` state machine is C and releases nothing mid-record; parsing is single-threaded per reader on every build. Parallel ingest shards by *file or byte-range at record boundaries*, Deep U's territory again, not by threads over one reader.

---

## 119.5 Connections

**Backward.**
The line where `split` stopped being safe, Chapter 118; the regex engine that also cannot parse this grammar (nested quoting defeats line-oriented patterns), Chapter 117; text-vs-bytes at the file boundary, Deep D; files and buffering, Chapter 40.

**Forward.**
Binary-to-text codecs, where the payload itself must survive a text channel, Chapter 120. Compression around csv streams, Chapter 121's composition. Typed serialisation, Chapter 42 (Deep R); tabular scale, Deep U, this chapter's stated ceiling.

**Across books.**
Every systems language re-learns that "comma-separated" names a grammar, not a `split`; **Book I**'s parser chapter builds this exact state machine as its worked example, and both books route gigabyte tables to columnar formats with the same sentence about floors and destinations.

---

## 119.6 Exercises

**1. Break line-orientation.** Construct a file where `len(list(reader))` differs from the line count by 3; explain each difference from the state machine's rules.

**2. Dialect forensics.** Collect three real CSV exports (bank, spreadsheet, SaaS); write the explicit dialect for each and the one-line provenance comment saying why.

**3. Injection audit.** Build an export function hardened against formula injection; test with `=1+1`, `@SUM`, and a legitimate negative number, and document the escaping trade you chose.

**4. The validation layer.** Wrap `DictReader` in a generator that enforces a schema (names, required fields, int columns), routing ragged rows (the `None`-key tell) to an error stream. Measure its overhead against bare `DictReader`.

**5. Find the ceiling.** Time csv parsing of a 1 GB synthetic file against a columnar read of the same data (any Deep U tool); report the ratio and the memory profiles, and write the migration sentence for your own largest CSV.

**6. The design question.** The module returns strings and refuses schemas; pandas' `read_csv` infers types and pays for it in silent coercions (leading zeros, mixed columns). Argue the stdlib's refusal: what inference costs in correctness at library scale, why `QUOTE_NONNUMERIC`'s float-only exception is the narrowest possible type system, and where inference *belongs* (the consumer's declared schema). Then design the minimal `types=` parameter you would add, and defend its behaviour on a column containing `'007'`.

---

## 119.7 Summary and cross-references

- **Delimited text with quoting is a grammar**: quotes double inside quotes, records span physical lines, and the reader therefore consumes an iterable of lines and owns recombination, `split(',')` is a correctness bug (4 fields from 3), and the writer/reader pair is a proven inverse (`round-trip equality : True`).
- **Dialects are parser configuration** (delimiter, quotechar, escaping, policy); declare them per source; `Sniffer` is for prompts, not pipelines. Open files with `newline=''`; the format's native ending is `\r\n`.
- **Types are absent by design**: everything is `str` except `QUOTE_NONNUMERIC`'s float exception; `DictReader` *describes* ragged rows (`None` key as the tell) and never repairs them.
- **Priced**: the full grammar at ~180 ns/row, 3.1x the wrong split, with **no per-quote surcharge** (1.02x); `DictReader` at 2.85x (a dict per row, for the program's edges); `QUOTE_ALL` ~2% (choose policies for consumers). The ceiling is real: millions of rows belong to columnar formats.
- **The edges that ship bugs**: regional dialects, forgotten `newline=''`, formula injection on export, field-size limits on untrusted input, and round trips that preserve strings while callers imagine types.

**Cross-references.** The split boundary → Chapter 118. Regex's inability here → Chapter 117. Text/bytes at the file → Deep D, Chapter 40. Codecs → Chapter 120. Compression composition → Chapter 121. Typed serialisation → Chapter 42. Tabular scale → Deep U.
