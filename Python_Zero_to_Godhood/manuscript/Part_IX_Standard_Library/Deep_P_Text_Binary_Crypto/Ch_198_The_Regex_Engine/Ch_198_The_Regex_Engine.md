# Chapter 117: The Regex Engine

Deep P opens with the standard library's most-used little language, and treats it the way this book treats every language: as an engine with observable mechanics and measurable costs. Three facts anchor `re`. A pattern is **compiled to a program**, an object you can hold, inspect (`.groups`, `.groupindex`), and reuse. The engine **executes by backtracking**, and the listing proves it from captured groups alone: `(a+)(ab)` on `'aaab'` settles at `('aa', 'ab')` (the greedy `a+` grabbed all three, hit the wall, and *gave back* one), and `(.*)(\d+)` on `'build4711'` settles at `('build471', '1')` while the lazy variant settles at `('build', '4711')`, each settlement the visible residue of a trail of retries. And **alternation is ordered**: `(cat|category)` matches `'cat'` where `(category|cat)` matches `'category'`, first success wins, not longest, unlike POSIX tools.

The benchmark then locates the costs, and its middle table is the chapter's trophy because it falsified the author's prediction: the engine **pre-scans for required literals** with a fast substring search, so a bare literal *and even the `.*`-dressed pattern* ride that optimised path, while the innocent-looking `\b` word boundary **defeats the skip and costs 5.85x**. An earlier draft predicted the `.*` row would be the slow one; the machine disagreed; the honest table shipped. Meanwhile `'ERROR' in line` beats every regex by 2.7x, regex earns its keep on *structure*, never on literal lookup.

**This is a Deep P chapter.**
Chapter 82 (Deep O) owns the pathological blowup, ReDoS and nested quantifiers; Deep D owns what characters *are*. This chapter owns the engine's ordinary behaviour: the program, the backtracking, the verbs, and the optimisations that decide real scan costs.

## Section index

- **117.1** The engine, proven from its outputs
- **117.2** The model: a backtracking VM with a literal pre-scanner
- **117.3** Measurement: invocations, the skip path, and streams
- **117.4** Edges and failure modes
- **117.5** Connections
- **117.6** Exercises
- **117.7** Summary and cross-references

Listings live under `code/ch198/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 117.1 The engine, proven from its outputs

```python
# code/ch198/l01_the_regex_engine.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- a pattern is a compiled program ---
  type(re.compile(...)) : Pattern
  groups declared       : 2, named ['key', 'value']
  first match           : 'retries=3' at (0, 9)
  by name               : key='retries', value='3'
  compile once, hold the object: the module-level functions do this
  through a cache, but the OBJECT is the honest interface - a
  pattern is a program, and programs are values
--- backtracking, proven by where the groups settled ---
  (a+)(ab)  on 'aaab'   -> groups ('aa', 'ab')
  a+ grabbed 'aaa', hit the wall, GAVE BACK one 'a' so (ab) could
  match: the retry is invisible in the result except right here
  (.*)(\d+)  greedy     -> groups ('build471', '1')
  (.*?)(\d+) lazy       -> groups ('build', '4711')
  greedy .* swallowed the digits and surrendered ONE, leaving '1';
  lazy .*? stopped at the first digit, leaving '4711'. neither is
  wrong and neither is free: each settlement is a trail of retries,
  and the pathological trails are Chapter 82's subject
--- alternation order is semantics, not style ---
  (cat|category) on 'category:9' -> 'cat'
  (category|cat) on 'category:9' -> 'category'
  the engine tries alternatives LEFT TO RIGHT and keeps the first
  success at each position - longest-match is not the rule here
  (unlike POSIX tools), so order alternations longest-first
--- the verbs are different questions ---
  fullmatch 'a=1'   : True    'a=1,' : False
  findall           : [('a', '1'), ('b', '22'), ('c', '333')]
  finditer spans    : [(0, 3), (5, 9), (11, 16)]
  sub with function : 'a:1, b:22, c:333'
```

**The Pattern object is the honest interface.**
`re.search(pattern, text)` compiles through a module-level cache; the object you get from `re.compile` *is* that cached program, held explicitly: introspectable groups, reusable across calls, passable as a value. The design lesson generalises across Deep P: the stdlib's little languages (regexes, format specs, struct strings) all compile to programs, and holding the program beats re-parsing the source.

**The groups are the backtracking VM's flight recorder.**
No instrumentation was possible, the first draft tried counting character probes through a `str` subclass, and the C engine, reading the underlying buffer directly, ignored it entirely (an instrument must touch the layer it claims to measure, the listing's docstring keeps the failure). But none was needed: where the groups *settled* is a complete proof of the retry semantics, greedy consumes and surrenders, lazy grows reluctantly, and both settle wherever the first overall success lies.

**And the verb table is the API disambiguated by question.**
`match`/`search`/`fullmatch` answer *where* (with `fullmatch` as validation: the whole string or nothing, `'a=1,'` correctly rejected); `findall`/`finditer` answer *what* (with `finditer` streaming `Match` objects, spans and groups without a giant list, Chapter 91's shape); `sub` answers *instead*, taking a function when replacement needs logic. Half of regex clarity is choosing the verb before writing the pattern.

---

## 117.2 The model: a backtracking VM with a literal pre-scanner

**Compilation lowers the pattern to opcodes** (`sre_compile`'s output, inspectable via `re.DEBUG`): literals, character classes, repeats, branches, group marks. The engine is a VM over that program with a backtracking stack: each quantifier and branch pushes a choice point; failure pops and retries. This is why regex features compose so freely, everything is just more opcodes, and why cost analysis is control-flow analysis: the trails the listing's groups recorded are the VM's stack discipline made visible.

**Ordered alternation and leftmost-first are the VM's honest semantics.**
The engine reports the *first* success in its depth-first exploration from the leftmost viable position, not the longest match. Consequences: alternations must be ordered longest-first when overlap exists (`(category|cat)`); optional suffixes belong *inside* the pattern's tail, not as competing branches; and translating from POSIX-longest-match tools (grep, lex) requires re-thinking, not transliterating.

**The literal pre-scanner is the optimisation that shapes real costs.**
Before running the VM, the engine extracts required literal fragments from the compiled program and uses fast substring search to find candidate positions, only *then* does the VM run. A bare literal is *all* pre-scan (74 ns of `in`-like speed plus API overhead); a `.*ERROR.*` still pre-scans for `ERROR` (hence its modest 1.27x); but constructs that invalidate a clean literal anchor, the `\b` boundary's per-position context check being the measured example, force the VM to attempt at every offset, which is the 5.85x. The practical compass: **think about what literal the engine can lock onto**, and be suspicious of decorations around it.

**What the engine is not**: not a DFA (no linear-time guarantee, Chapter 82's whole subject), not Unicode-naive (classes like `\w` are Unicode-aware on `str`, per Deep D, with `re.ASCII` to opt out), and not the only tool, §117.3's first table keeps `str` methods in the race, and Chapter 118 gives the non-regex text toolbox its own chapter.

---

## 117.3 Measurement: invocations, the skip path, and streams

**Methodology.** `code/ch198/bench_regex_costs.py`.
`min` of 15 batches (7 for the big-haystack rows); 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. One question, three invocations** (196-char line):

| invocation | time | vs `str` |
|---|---|---|
| `'ERROR' in line` | 74.4 ns | 1.00x |
| `re.search(r'ERROR', line)` (cache) | 197.2 ns | 2.65x |
| precompiled `.search` | 100.8 ns | 1.35x |

**b. The literal-skip path, and what defeats it:**

| pattern | time | vs literal |
|---|---|---|
| `r'ERROR'` | 198.3 ns | 1.00x |
| `r'.*ERROR.*=(\d+)'` | 252.7 ns | 1.27x |
| `r'\bERROR\b'` | **1,159.8 ns** | **5.85x** |

**c. 20,000 matches: list vs stream:**

| verb | time | vs findall |
|---|---|---|
| `findall` (materialise) | 1.61 ms | 1.00x |
| `finditer`, fully consumed | 1.86 ms | 1.16x |
| `finditer`, first 10 only | **1.2 us** | ~0 |

**Table a keeps the baseline honest**: for substring questions, `str` wins by 2.7x over even the cached module call, and the cache-vs-precompiled gap (~96 ns) is the dict lookup plus argument handling, worth removing in hot paths, not a superstition to apply everywhere.

**Table b is the falsified prediction, kept.**
The draft predicted `.*` would be the villain; the measurement crowned `\b` instead, because the boundary check defeats the pre-scanner's clean literal anchor. The row is preserved with its confession in the benchmark's reading, this book's method applied to its own folklore, and the transferable rule is stated above: reason about the engine's *lockable literal*, and measure anything decorating it.

**Table c is Chapter 91 inside one API**: the stream ties the list when fully consumed (1.16x, the Match objects' cost), and wins absolutely on early exit (first-10 at ~0) and on memory (no 20,000-element list). `finditer` is the default for large inputs; `findall` is the convenience for small ones.

---

## 117.4 Edges and failure modes

**`match` is not `search`, and neither is `fullmatch`.**
`match` anchors at position 0 only, the classic silent bug is using it as containment; `fullmatch` is the validation verb. The listing's `'a=1,'` rejection is the test to copy.

**`findall`'s return type depends on the pattern's groups.**
Zero groups: list of strings; one group: list of *that group* (not the match!); two or more: list of tuples. Code that adds a group to a working pattern silently changes downstream types, `finditer`, whose `Match` objects are shape-stable, is the refactoring-safe verb.

**Backslashes demand raw strings, always.**
`'\b'` is a backspace character; `r'\b'` is a boundary. The convention, raw strings for every pattern, no exceptions, costs nothing and retires the whole bug class (the listing's own first draft double-escaped a pattern inside an f-string and matched nothing, the error class is not hypothetical).

**The cache is finite and clearable.**
`re`'s module cache holds ~512 patterns; a workload generating patterns dynamically (per-user filters) can thrash it, re-paying compilation per call. Dynamic patterns argue for explicit compilation and your own lifetime management, or for questioning why patterns are dynamic at all (user input in patterns is also Chapter 82's ReDoS door).

**`re.VERBOSE` is the maintainability flag.**
Whitespace-insensitive patterns with comments turn write-only line noise into reviewable programs; the flag belongs on every pattern longer than one concept. Flags generally (`IGNORECASE`, `MULTILINE`, `DOTALL`, `ASCII`) change semantics enough that they belong *in* the pattern (`(?imsx:...)`) when the pattern travels without its call site.

**Unicode classes are correct and slower.**
On `str`, `\w`/`\d`/`\b` consult Unicode properties (Deep D); `re.ASCII` restores byte-era semantics and some speed when the data is genuinely ASCII, an *assertion about the data*, to be made honestly. On `bytes` patterns, ASCII semantics are the only semantics.

**And `sub` with a function is the escape from replacement-string escaping.**
`\1` and `\g<name>` in replacement templates have their own escaping rules and their own bugs; a callable receives the `Match` and returns the text, no sublanguage involved, the listing's reversed-digits replacement is the pattern to remember.

---

## 117.5 Connections

**Backward.**
The pathological engine, nested quantifiers, ReDoS, and the linear-time alternatives, is Chapter 82 (Deep O), and this chapter's VM model is its prerequisite. Character semantics under `\w` and friends are Deep D. The streaming trade in table c is Chapter 91; the honest-instrument lesson (the failed probe counter) is Chapter 85's discipline; string interning and `in`'s speed are Deep D and Chapter 76's C-loop story.

**Forward.**
Chapter 118 is the non-regex text toolbox, `str` methods, `difflib`, `textwrap`, including the decision table for when a regex is the wrong tool (table a's first row, expanded to a chapter). CSV's quoting engine (119) and the binary-to-text codecs (120) are Deep P's other little languages, each compiled, each with the same hold-the-program advice.

**Across books.**
**Book I** wraps RE2, guaranteed-linear, no backtracking, no backreferences, and its regex chapter is one long meditation on the same trade this chapter's tables expose: Python chose expressiveness (backreferences, lookarounds) at the price of worst-case time, C++ infrastructure chose bounded time at the price of features. Both chapters end identically: know which engine you hold, and never feed either one untrusted patterns.

---

## 117.6 Exercises

**1. Read the opcodes.** Compile three of the listing's patterns with `re.DEBUG` and annotate each opcode line with the VM-model concept it implements (choice point, literal, group mark).

**2. Find the lockable literal.** For five patterns from a codebase you know, predict which fragment the pre-scanner can anchor on, then measure each against a literal-only control on matching and non-matching lines. Report the `\b`-class surprises.

**3. Break `findall`'s type.** Take working `findall` code, add a group for logging, and follow the type change downstream. Convert to `finditer` and show the refactor is now shape-stable.

**4. Thrash the cache.** Generate 2,000 distinct patterns, cycle through them with module-level `re.search`, and measure against precompiled objects held in your own dict. Find the cache's cliff.

**5. The VERBOSE rewrite.** Rewrite a real 80-character pattern in `re.VERBOSE` with comments; diff review-comprehension time with a colleague. (The measurement is social; the result is repeatable anyway.)

**6. The design question.** `re` guarantees features (backreferences, lookaround) but not time; RE2 guarantees time but not features; hybrid engines (Rust's, .NET's non-backtracking mode) pick per pattern. Argue what CPython should ship as `re`'s future: the compatibility constraint (every existing pattern must keep matching identically, alternation *order* included), the security pull (Chapter 82), and where the pre-scanner already sits on this spectrum. Then specify the smallest API addition (`re.compile(..., linear=True)`?) that would let callers choose, and its failure mode on unsupported features.

---

## 117.7 Summary and cross-references

- **A pattern is a compiled program**; hold the object (`.groups`, `.groupindex`, reuse), and let the module cache be a convenience, not an architecture.
- **The engine is a backtracking VM, proven from group settlements**: greedy consumes and gives back (`('aa','ab')`), lazy grows reluctantly (`('build','4711')`), and **alternation is ordered, first-success**, not longest-match, order overlapping branches longest-first.
- **Measured**: `str`'s `in` beats regex 2.7x on literal questions; precompiling saves the ~96 ns cache lookup; the **literal pre-scanner** makes bare and even `.*`-dressed literals fast while **`\b` defeats it at 5.85x**, a falsified prediction, kept as the method demands; and `finditer` streams (early exit ~free, constant memory) where `findall` materialises.
- **The verbs are different questions**: where (`match`/`search`/`fullmatch`-as-validation), what (`findall`/`finditer`), instead (`sub`, with a function to escape the template sublanguage). `findall`'s group-dependent return type is the API's one trap.
- **Raw strings always; VERBOSE for anything nontrivial; ASCII only as an honest data assertion; dynamic patterns are a smell and untrusted ones are Chapter 82's door.**

**Cross-references.** ReDoS and linear engines → Chapter 82. Character classes' semantics → Deep D. Streams → Chapter 91. Honest instruments → Chapter 85. The non-regex toolbox → Chapter 118. CSV's quoting engine → Chapter 119. Codecs → Chapter 120.
