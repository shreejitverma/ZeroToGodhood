# Chapter 118: The Text Toolbox

Chapter 117 ended with regex earning its keep only on structure; this chapter is the toolbox for everything else, and it opens by pricing the boundary: `str.replace` beats `re.sub` on a literal by **12x**, `startswith` beats `re.match` by 6x, because the `str` verbs are C scans over the buffer (Chapter 76) while the regex rows pay the engine's ceremony for zero added expressiveness.

The listing is a tour of verbs chosen for *correctness*, not just speed. `partition` never raises and always returns three parts (the parse-a-config-line idiom in two calls); `removesuffix` strips an *exact* affix where slicing `[-4:]` and the classic `strip('my')` character-set trap corrupt silently; `splitlines` sees the Unicode line breaks `split('\n')` is blind to (`['a','b','c']` vs 2 parts on the same string); and `casefold` is the comparison normaliser, `'ß'.casefold() == 'ss'`, where `lower` is only the display one. Then `difflib`, similarity as greedy longest-block matching (`ratio 0.842`, the blocks printed), `get_close_matches` as every CLI's did-you-mean, and `unified_diff` yielding the exact format git popularised, and `textwrap`, prose as a layout problem (`wrap`, `shorten`'s collapse-then-truncate, `dedent`'s common-margin rule).

The benchmark's second half carries a falsified expectation, kept per house rules: `SequenceMatcher`'s autojunk heuristic showed *nothing* on distinct tokens (its junk threshold is items commoner than 1%), and then saved **2.2x** (19.5 vs 43.8 ms) the moment the data took the real-document shape of every-third-line-blank. The instrument taught the mechanism.

**This is a Deep P chapter.**
Deep D owns what characters and case *are*; Chapter 117 owns the regex engine this chapter keeps off literal work. This chapter owns the non-regex text verbs and the two workhorses, `difflib` and `textwrap`.

## Section index

- **118.1** The verbs, demonstrated for correctness
- **118.2** The model: exact affixes, matching blocks, layout rules
- **118.3** Measurement: the boundary priced, and autojunk found
- **118.4** Edges and failure modes
- **118.5** Connections
- **118.6** Exercises
- **118.7** Summary and cross-references

Listings live under `code/ch199/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 118.1 The verbs, demonstrated for correctness

```python
# code/ch199/l01_the_text_toolbox.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- str's verbs: the questions that never needed a regex ---
  partition twice     : key='timeout', value='45', comment='seconds'
  removesuffix        : 'v2.report'   (slicing [-4:] would eat 'txt' from 'v2.report')
  removeprefix chain  : 'net:timeout'
  splitlines          : ['a', 'b', 'c']
  split('\n')         : 2 parts (blind to the Unicode break splitlines saw)
  casefold vs lower   : True / True  (both true; but casefold also folds ß -> ss)
    'ß'.casefold() : 'ss'   'ß'.lower() : 'ß'
  partition never raises and always returns three parts; the
  remove* pair strips EXACT affixes (strip() strips a CHARACTER
  SET - the classic 'mystring'.strip('my') surprise); casefold is
  the comparison normaliser, lower the display one (Deep D)
--- difflib: similarity as longest matching blocks ---
  ratio('the quick brown fox', 'the quiet brown fax') : 0.842
  matching blocks     : [(0, 0, 7), (9, 9, 8), (18, 18, 1)]
  get_close_matches('timout') : ['timeout', 'time_out']
  ratio = 2*matched/total, from greedy longest-block matching -
  fast and usually right, not an edit distance; close_matches is
  the did-you-mean in every CLI, three lines from the stdlib
--- difflib: the diff every tool renders ---
    --- old.cfg
    +++ new.cfg
    @@ -1,3 +1,3 @@
    -retries = 3
    +retries = 5
     timeout = 45
    -verbose = false
    +log_level = info
  unified_diff yields the format git popularised; ndiff adds
  intra-line detail; HtmlDiff renders review pages - the stdlib
  ships the whole diff stack, and it streams (Chapter 91)
--- textwrap: prose as a layout problem ---
    |The engine backtracks, the groups record the|
    |settlement, and the benchmark keeps everyone|
    |honest.|
  shorten to 40       : 'The engine backtracks, the groups ...'
  dedent removes the common margin : ['def f():', '    return 1']
```

**Each `str` line pairs a verb with the bug it retires.**
`partition("=")` then `partition("#")` parses key, value, and comment with no exceptions, no index arithmetic, and defined behaviour when the separator is absent (everything lands in the first part). `removesuffix('.txt')` on `'v2.report.txt'` yields `'v2.report'`, where the slicing habit `[:-4]` applied unconditionally eats real data, and where `strip('.txt')` would strip *any* of those four characters from both ends, the `'mystring'.strip('my')` surprise that every code reviewer eventually meets. `splitlines` honours the Unicode line-break set (U+2028 in the listing), which matters exactly when text arrives from the world rather than from your own files. And the `casefold` pair is Deep D's case model operationalised: fold for comparison, lower for display, and `'ß'` is the one-character proof they differ.

**The `difflib` blocks show the algorithm, not just the API.**
`ratio` is `2 * matched / total` over greedy longest-matching-block extraction, the blocks themselves printed, `(0,0,7)` is `'the qui'`, and it is *not* an edit distance: fast, order-sensitive, usually right, occasionally surprising (§118.4). `get_close_matches` wraps the same matcher into three-line did-you-mean; `unified_diff` streams the git-popularised format (a generator, Chapter 91's shape, no materialised document).

**And `textwrap`'s three verbs have three distinct contracts**: `wrap` breaks at whitespace and never inside words by default; `shorten` collapses runs of whitespace *first*, then truncates at a word boundary with a placeholder; `dedent` removes only the *common* leading whitespace, the docstring and heredoc normaliser, with the mixed-tabs caveat parked in §118.4.

---

## 118.2 The model: exact affixes, matching blocks, layout rules

**The `str` verb family divides by contract, and choosing by contract prevents the bugs.**
Exact-affix verbs (`removeprefix`/`removesuffix`, `startswith`/`endswith`): match whole substrings, never character sets. Set verbs (`strip`/`lstrip`/`rstrip`): take *character sets*, right for whitespace and wrong for affixes. Structural verbs (`partition`/`rpartition` vs `split`/`rsplit`): partition is total (three parts, always) where split's list length varies, which is why partition composes into parsers and split composes into surprises. The 3.9 addition of the `remove*` pair closed the last gap that pushed people to slicing.

**`SequenceMatcher` is Ratcliff-Obershelp, and its character is set by greed.**
Find the longest matching block, recurse left and right of it, sum the matches. Strengths: near-linear on similar inputs, intuitive blocks, junk-awareness. Weaknesses: order sensitivity (transposed halves score low), no triangle-inequality guarantees, and superlinear cost on dissimilar inputs, §118.3's curve. The **junk machinery** is the practical half: explicit junk predicates (ignore whitespace lines) and *autojunk*, which auto-demotes any item occurring in more than 1% of a 200+-item sequence, blank lines being the canonical case, so that ubiquitous filler cannot anchor matching blocks everywhere and blow up the recursion.

**`textwrap` treats text as tokens with widths**, splitting on whitespace (and optionally hyphens), then packing greedily to the width. It is a *character-count* packer: no font metrics, no East-Asian double-width awareness, no ANSI-escape awareness, the honest scope statement that separates it from terminal-UI libraries, and within that scope its options (`initial_indent`, `subsequent_indent`, `break_long_words`) cover the README-and-log-message territory completely.

**The chapter's meta-rule is verb-first design**: every block in the listing states a *question* (parse this line, is this the same word, what changed, fit this width) and the tool built for it. The regex chapter's discipline, choose the verb before the pattern, generalises to the whole text toolbox, and most improvised text bugs are a verb mismatch, not a logic error.

---

## 118.3 Measurement: the boundary priced, and autojunk found

**Methodology.** `code/ch199/bench_text_tools.py`.
`min` of 15 batches (3 runs for difflib); 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. `str` verbs against their regex spellings** (1 KB text):

| operation | `str` | `re` | ratio |
|---|---|---|---|
| replace literal | 314 ns | 3,872 ns | **12.3x** |
| split on `';'` | 1,983 ns | 2,429 ns | 1.2x |
| prefix test | 10.6 ns | 61.7 ns | 5.8x |

**b. `SequenceMatcher.ratio()` scaling, and autojunk's territory:**

| shape | cost |
|---|---|
| distinct tokens, n=100 / 400 / 1,600 | 0.06 / 0.38 / 3.40 ms (~9x per 4x) |
| every 3rd line blank, n=1,600, autojunk **on** | 19.5 ms |
| same, autojunk **off** | **43.8 ms** |

**Table a is Chapter 117's rule, priced from the other side.**
The 12x on replace is the whole argument for verb-first design in one row; the split rows nearly tie because both do the same buffer walk (the regex's literal path, Chapter 117's pre-scanner, at work); the prefix rows are a 6x reminder that even the *cheapest* regex call carries fixed ceremony. None of this indicts `re`, it prices using a VM where a verb exists.

**Table b's story is the falsified expectation, kept.**
The draft expected autojunk to matter on generic data; on distinct tokens it is a no-op *by definition* (nothing exceeds the 1% commonness threshold), and the growth curve (~9x per 4x, superlinear) belongs to the algorithm itself. Reshape the data to the blank-heavy profile of real documents and autojunk halves the cost (2.2x), which converts the parameter from folklore ("some heuristic, leave it alone") into a mechanism with a known trigger. The operational rules follow directly: diff *lines*, not characters, for documents; leave autojunk on; and pass an explicit junk predicate when domain filler (timestamps, indentation) plays the blank line's role.

**Book I**'s text chapter prices `std::string` verbs against `std::regex` with the same 10x-class gaps and a worse regex engine, and its diff tooling wraps the same Ratcliff-Obershelp under `git diff`'s Myers alternative, the cross-book lesson being that diff *algorithm choice* (blocks vs shortest-edit-script) is a product decision about which changes should look atomic.

---

## 118.4 Edges and failure modes

**`strip` takes a set; the bug is silent and eventually famous.**
`'mystring'.strip('my')` yields `'string'` for the wrong reason and `'trs'`-class surprises on other inputs. Affix removal is `removeprefix`/`removesuffix`, full stop; every `strip` call with a multi-character argument deserves a second look in review.

**`split()` and `split(' ')` are different functions.**
Bare `split()` collapses whitespace runs and drops edge empties; `split(' ')` preserves them (`'a  b'.split(' ')` has an empty middle element). Parsing columnar text wants the first; round-tripping delimited data wants the second plus Chapter 119's `csv` the moment quoting exists.

**`ratio()` is not a metric.**
`SequenceMatcher` gives no symmetry-with-caching guarantees (`ratio` depends on argument order via junk handling), no triangle inequality, and low scores for transpositions that humans call similar. For fuzzy *lookup*, `get_close_matches` with a cutoff is calibrated; for true edit distance, that is an algorithm you import or write, not coax from difflib.

**`quick_ratio` and `real_quick_ratio` are bounds, not estimates.**
They upper-bound `ratio` cheaply, correct as a filter cascade (Chapter 110's shape: cheap gate before expensive truth), wrong as a substitute, they can say 0.9 where `ratio` says 0.3.

**`dedent` requires *identical* whitespace, not equivalent.**
A file mixing tabs and spaces has no common prefix to strip, and `dedent` correctly does nothing, the "why is my heredoc still indented" bug. `expandtabs()` first, or fix the source; `inspect.cleandoc` handles the docstring-specific variant (first line unindented).

**`shorten` collapses before it measures.**
Internal newlines and spacing vanish (`shorten` is for single-line summaries by design); truncating *formatted* text needs `wrap` plus your own ellipsis logic.

**And `textwrap` counts characters, not display cells.**
Wide CJK glyphs, combining marks, and ANSI colour codes all break the visual alignment while satisfying the width; the moment output is a *terminal UI* rather than prose, this is the wrong layer (Deep D for the character model; third-party for cell arithmetic).

---

## 118.5 Connections

**Backward.**
The regex engine these verbs displace, and the pre-scanner that makes the split rows tie, Chapter 117. The C-loop speed of the `str` verbs, Chapter 76; the case model under `casefold` and the Unicode line-break set under `splitlines`, Deep D. Streaming diffs, Chapter 91; the falsified-instrument discipline, Chapter 85.

**Forward.**
Chapter 119 takes the one text format this chapter's verbs cannot safely parse, delimited data with quoting, where `split(',')` becomes a correctness bug rather than a style choice. Chapter 120's codecs are the binary boundary of the same toolbox.

**Across books.**
Every language grows this same drawer, exact-affix verbs arriving late (C++20's `starts_with`, Python 3.9's `removeprefix`) after decades of sliced-off-by-one bugs, and **Book I**'s chapter tells the identical story with `string_view` in the partition role. Convergent evolution toward *total, exact, contract-named* verbs is the drawer's lesson in both languages.

---

## 118.6 Exercises

**1. Retire a strip bug.** Find a real `strip(affix)` misuse (grep any large codebase for `.strip('` with multi-character arguments); demonstrate its failure input and convert to the `remove*` verb.

**2. Build the config parser.** Using only `partition`, `removeprefix`, and `casefold`, write a 20-line parser for `key = value # comment` files with case-insensitive keys, and enumerate the inputs on which a `split('=')` version differs.

**3. Calibrate close matches.** For a command-vocabulary of 50 names, tune `get_close_matches`' `cutoff` against a set of 20 real typos: report false-accept and false-reject at 0.5, 0.6, 0.8.

**4. Find autojunk's trigger in your data.** Diff two versions of a real document line-wise with autojunk on and off; measure, then identify which line value crossed the 1% threshold (count it). Repeat with an explicit `isjunk` for your domain's filler.

**5. The bounds cascade.** Implement fuzzy search over 10,000 strings as `real_quick_ratio` -> `quick_ratio` -> `ratio` filter stages; measure against `ratio`-only and report the speedup and the (empty) accuracy loss.

**6. The design question.** `difflib` chose Ratcliff-Obershelp (intuitive blocks, junk-aware, no optimality) where git chose Myers (shortest edit script, optimal, occasionally inhuman hunks). Argue which belongs in a *standard library*: the API-stability constraint (blocks are exposed via `get_matching_blocks`), the junk machinery's dependence on the algorithm, and what "readable diff" optimises for. Then specify the smallest additional API that would let `unified_diff` take a pluggable matcher, and what it would break.

---

## 118.7 Summary and cross-references

- **Verb-first design**: `partition` (total, three parts) for parsing; `removeprefix`/`removesuffix` for *exact* affixes (`strip` takes character sets, the classic trap); `splitlines` for real-world line breaks; `casefold` for comparison, `lower` for display (`'ß' -> 'ss'` is the proof).
- **Priced**: `str.replace` **12x** over literal `re.sub`, `startswith` 6x over `re.match`; the regex engine is for structure, and the split rows tie only because its literal pre-scanner (Chapter 117) is doing the same walk.
- **`difflib`**: greedy longest-block matching (`ratio = 2*matched/total`, blocks inspectable), `get_close_matches` as three-line did-you-mean, `unified_diff` streaming git's format. Superlinear core (~9x per 4x); **autojunk is a no-op on distinct data and a 2.2x saver on blank-heavy documents**, its 1% threshold now a mechanism, not folklore.
- **`textwrap`**: `wrap` packs words to a width, `shorten` collapses then truncates at word boundaries, `dedent` strips only the *common* margin (mixed tabs defeat it; `expandtabs` first), all in character units, not display cells.
- **The recurring edges**: `split()` vs `split(' ')`, `ratio` is not a metric, `quick_ratio` is a bound for cascades, and formatted text outgrows `shorten`.

**Cross-references.** The regex engine and pre-scanner → Chapter 117. C-loop `str` verbs → Chapter 76. Case and line-break models → Deep D. Streaming → Chapter 91. Delimited data with quoting → Chapter 119. Codecs → Chapter 120.
