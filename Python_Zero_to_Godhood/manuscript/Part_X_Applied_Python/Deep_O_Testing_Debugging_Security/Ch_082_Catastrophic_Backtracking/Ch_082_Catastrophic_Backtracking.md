# Chapter 82: Catastrophic Backtracking (ReDoS)

A service validates usernames with the regex `(a+)+$` (or something structurally like it, common in hand-written
validators), and a single 30-character request string hangs a worker for *minutes*, taking the whole process
down. No bug in the surrounding code; the regex itself is the weapon. Python's `re` is a *backtracking* matcher,
and a pattern with a nested quantifier like `(a+)+` has *exponentially many* ways to split its input. On a
string that *almost* matches but fails at the end, the engine tries every split before giving up. Measured, the
match time **doubles for every added character**: n=14 takes ~1 ms, n=22 takes ~239 ms, and n=30 would take
*minutes*, n=40 *hours*. That is a **ReDoS** (regular-expression denial-of-service): an attacker sends a short
crafted string and consumes unbounded CPU. The de-nested equivalent `a+$`, which accepts the *same* strings,
stays in *microseconds* at the same lengths.

This chapter continues **Deep O** with catastrophic backtracking: why nested quantifiers explode exponentially,
how the same match written safely is fast, and the defenses. It is a security chapter where the vulnerability is
*performance*, an attacker weaponizing the runtime of your own regex.

## Section index

- **82.1** The exponential regex
- **82.2** Why it backtracks exponentially
- **82.3** Measurement: doubling per character
- **82.4** Edges and failure modes
- **82.5** Connections
- **82.6** Exercises
- **82.7** Summary and cross-references

Listings live under `code/ch082/` and are re-executed by `make verify` on both interpreters.

---

## 82.1 The exponential regex

```python
# code/ch082/l01_redos.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- both regexes accept/reject the SAME strings ---
  'aaaa'   vuln=True  safe=True  agree=True
  'aaab'   vuln=False  safe=False  agree=True
  ''       vuln=False  safe=False  agree=True
  'baaa'   vuln=True  safe=True  agree=True
--- the difference is COST on a crafted near-match (small n here) ---
  'a'*4+'!' rejected by both : True
  'a'*8+'!' rejected by both : True
  'a'*12+'!' rejected by both : True
--- the mechanism ---
  (a+)+ can split 'aaaa' as (aaaa), (aaa)(a), (aa)(aa), ... exponentially
  on a failing input the engine tries every split before giving up
  the de-nested a+$ has no nested quantifier: polynomial, not exponential
  fix: avoid nested/ambiguous quantifiers; bound input length; use timeouts
```

The crucial point of the first block: the vulnerable `(a+)+$` and the safe `a+$` are **behaviorally identical**,
they accept and reject the *same* strings (both match a string ending in one or more `a`s, including `"baaa"`).
They differ *only* in cost. So a validator using `(a+)+$` is not "more thorough" than one using `a+$`; it is the
*same* validation, with a hidden exponential-time trapdoor. The listing uses tiny inputs (`n` up to 12) so it
runs instantly, the exponential blowup is measured separately (§82.3), deliberately, so the listing itself cannot
hang.

The trigger is a **near-match that fails**: `"aaaa...!"` matches `a+` all the way, then the trailing `!` breaks
the `$` anchor, forcing the engine to backtrack and try other groupings, of which there are exponentially many.
A string that matches cleanly, or fails immediately, is fast; the worst case is the *almost*-match, which an
attacker constructs deliberately.

---

## 82.2 Why it backtracks exponentially

`(a+)+` is two nested quantifiers over the same character: an *inner* `a+` (one or more `a`s) inside an *outer*
`+` (one or more of those groups). For a run of *k* `a`s, there are exponentially many ways to partition it into
groups, `(aaaa)`, `(aaa)(a)`, `(aa)(aa)`, `(a)(aaa)`, `(a)(a)(aa)`, and so on, 2^(k-1) partitions. When the whole
pattern *matches*, the engine finds one partition and stops. When it *fails* (the trailing `!` prevents `$` from
matching), the engine must *rule out every partition* before concluding failure, and that is 2^(k-1) work:
exponential in the input length. Each added `a` doubles the number of partitions, hence the doubling in §82.3.

The general danger signature is a quantifier applied to a group that itself contains a quantifier matching the
*same* thing, `(a+)+`, `(a*)*`, `(a|a)*`, `(.*)*`, `(\d+)+`, and the classic `(\w+\s?)*` and email-validating
monsters. Any pattern where the engine can match a given substring *more than one way* creates the ambiguity
that backtracking explores exponentially. The **de-nested** form removes the ambiguity: `a+$` has *one* way to
match a run of `a`s (greedily, then anchor), so it is polynomial, not exponential.

The rule: **never write a regex with a nested or overlapping quantifier, and never run an attacker-influenced
regex that can backtrack catastrophically.** Rewrite `(a+)+` as `a+`, `(x+y+)+` to remove the nesting, and be
especially wary of quantified groups that can match empty or overlapping strings. Test regexes against
adversarial near-match inputs, not just valid ones, a regex that passes all your *valid* test cases can still
explode on a *crafted* one.

---

## 82.3 Measurement: doubling per character

**Methodology.** `code/ch082/bench_backtracking.py`. The vulnerable `(a+)+$` and the de-nested `a+$` on the
crafted near-match `"a" * n + "!"`, at increasing `n` (capped at 22 so the benchmark cannot hang). `min` per
length. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| n | `(a+)+$` (vulnerable) | factor | `a+$` (safe) |
|---|---|---|---|
| 14 | 0.94 ms | - | 2.7 us |
| 16 | 3.73 ms | 2.0x | 1.2 us |
| 18 | 15.02 ms | 2.0x | 3.1 us |
| 20 | 60.09 ms | 2.0x | 3.0 us |
| 22 | 239.21 ms | **2.0x** | 3.5 us |

The vulnerable regex's time **doubles for every added character**, the signature of exponential complexity:
~1 ms at n=14, ~239 ms at n=22, and extrapolating, ~1 s at n=24, *minutes* at n=30, *hours* at n=40. The safe
`a+$` stays flat at a few *microseconds* across all these lengths. So an attacker who can send a ~30-character
string to an endpoint using `(a+)+$` hangs a worker; a handful of such requests exhaust every worker, a complete
denial-of-service from a tiny payload.

The rule: **defend regexes that touch untrusted input on multiple layers.** First, **avoid nested/overlapping
quantifiers**, de-nest `(a+)+` to `a+` (the §82.1 equivalence shows it changes nothing but the cost). Second,
**bound the input length** before matching (reject an over-long string outright), because even a *non*-nested
regex like `a+$` is O(n^2) with `search` on huge input (search retries every start position), still a DoS at
large enough input, though never exponential. Third, **anchor** (`^...$`) and prefer `match`/`fullmatch` over
`search` to avoid the per-position retry. Fourth, **set a timeout** on matching untrusted input (a watchdog, or a
separate process), or use a **linear-time engine** (`re2`, `regex` with its safety options) for attacker-facing
patterns. The exponential blowup is the headline, but the general lesson is that a regex over untrusted input is
attack surface, and its *runtime*, not just its result, must be bounded.

---

## 82.4 Edges and failure modes

**Nested/overlapping quantifiers.** §82.2. `(a+)+`, `(a*)*`, `(a|a)*`, `(.*)*`, `(\w+\s?)*`, exponential on a
crafted near-match. De-nest them; test against adversarial inputs.

**Unbounded untrusted input.** §82.3. Even a safe regex is O(n^2) with `search` on huge input. Reject over-long
input *before* matching; set a maximum length.

**`search` vs `match`/`fullmatch`.** `search` retries at every start position (O(n) starts), multiplying cost.
Anchor with `^`/`$` and use `match`/`fullmatch` when you mean "the whole string", it both is correct and avoids
the retry.

**Testing only valid inputs.** A regex that passes all *valid* test cases can still explode on a *crafted*
near-match. Include adversarial ReDoS inputs (long runs that fail at the end) in the test suite for any regex on
untrusted data.

**Trusting a regex from a config/user.** A regex supplied by a user (a search filter, a rule) can be a
deliberate ReDoS. Never compile and run an untrusted *pattern* against untrusted *input* without a timeout or a
safe engine.

**Assuming `re` has a timeout.** Python's `re` has **no** built-in match timeout, once a catastrophic match
starts, it runs to completion (it does not even respond to signals promptly mid-match in all cases). You must
prevent the blowup (bound input, safe pattern) or run matching where you can kill it (a subprocess with a
timeout).

---

## 82.5 Connections

**Backward.** The complexity-class thinking (exponential vs polynomial, doubling as the signature) is the
measurement discipline of the book, and Chapter 34's O(2^n)-vs-O(n) contrast. The `re` engine and regex basics
are a text-processing topic (Deep D). The DoS-via-your-own-cost framing echoes the algorithmic-complexity
failures elsewhere (Chapter 7's O(n^2) string building, Chapter 32's O(n) `pop(0)`).

**Forward.** Input validation and sanitization broadly (bounding, allow-lists), and safe parsing of untrusted
data, are Deep O security material. Linear-time regex engines (`re2`) and the `regex` module are Deep D/Deep O
tooling. Rate-limiting and resource caps that contain any single request's cost are Deep U.

**Across books.** Bounded-cost regex matching is a boundary Book II enforces on untrusted input before it reaches
**Book III**. A **Book III** service that applies regexes to user queries, uploaded documents, or tool arguments
uses de-nested, anchored patterns, bounds input length, and runs attacker-facing matching under a timeout, so no
single request can consume unbounded CPU. The §82.3 exponential blowup is exactly the low-effort, high-impact DoS
that passes functional tests (the regex *works*) yet takes production down, which **Deep U** guards against at
the input seam.

---

## 82.6 Exercises

**1. Watch it double.** Reproduce §82.3 (bounded `n`) and confirm the vulnerable regex's time doubles per
character while the safe one stays flat. Explain why doubling means exponential.

**2. De-nest a pattern.** Take `(a+)+$` and rewrite it as `a+$`, and confirm (as in §82.1) they accept the same
strings. Explain what the nesting added, and what removing it changed.

**3. Bound the input.** Show that even `a+$` with `search` slows on very long input, then add a length check
before matching and an anchor, and show it stays fast. Explain the two separate defenses.

**4. Test adversarially.** Write a regex validator and a test that feeds it a crafted near-match, and show a
naive validator hangs (bound the test's input so it does not hang your suite). Explain why valid-only tests miss
ReDoS.

**5. The design question.** A backtracking regex engine gives expressive patterns at the risk of exponential
worst-case time. Argue how to use regexes safely on untrusted input. Your answer must use the §82.3 doubling,
name the dangerous quantifier shapes, and list the layered defenses (de-nest, bound length, anchor, timeout,
safe engine).

---

## 82.7 Summary and cross-references

- Python's `re` **backtracks**, and a **nested/overlapping quantifier** (`(a+)+`, `(a*)*`, `(.*)*`) has
  exponentially many ways to split its input, so on a **crafted near-match** it takes **exponential** time, a
  **ReDoS** denial-of-service.
- **Measured:** `(a+)+$` time **doubles per character** (~1 ms at n=14, ~239 ms at n=22, minutes at n=30); the
  de-nested `a+$`, which accepts the *same* strings, stays in **microseconds**.
- **Defend on layers:** avoid nested/overlapping quantifiers (de-nest); **bound input length** (even `a+$` is
  O(n^2) with `search` on huge input); anchor and use `match`/`fullmatch`; set a **timeout** (Python's `re` has
  none) or use a linear-time engine (`re2`).
- **Test regexes against adversarial near-matches,** not just valid inputs; never run an untrusted pattern on
  untrusted input unbounded.

**Cross-references.** Exponential vs polynomial (O(2^n)/O(n)) → Chapter 34; algorithmic DoS → Chapters 7, 32.
`re` and regex → Deep D. Safe engines (`re2`), input validation → Deep O. Rate-limiting/resource caps → Deep U.
The input seam → Deep U.
