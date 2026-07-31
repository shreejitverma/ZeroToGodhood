# Chapter 123: Two Kinds of Random

Two modules answer two opposite questions, and confusing them is a security bug wearing a convenience costume. `random` (Mersenne Twister) is a **deterministic** sequence with a seed: `Random(42)` produces `[0.639427, 0.025011, 0.275029]` on every interpreter in this book's matrix, which is not a footnote but *the reproducibility guarantee, demonstrated*, the same property that makes simulations repeatable, tests stable, and this listing verifiable at all. `secrets` asks the opposite: bits an adversary cannot predict, drawn from the OS entropy pool, no seed, no sequence, no reproduction, so its values *cannot appear verbatim in a verified book*, and the listing prints their **properties** instead (a `token_urlsafe(32)` is 43 chars, `ceil(32*4/3)`, Chapter 120's arithmetic; 1,000 tokens all unique; the alphabet is urlsafe-base64).

That asymmetry, one module's output is on the page and the other's provably cannot be, *is* the chapter's lesson, delivered by the book's own verification mechanism. The listing then shows the two traps between them: the module-level functions share **one hidden global generator** (an interloping `random.random()` from any library shifts your sequence, proven by an equality), and `choices` (with replacement, weights allowed) versus `sample` (without, a k-subset) is the off-by-one of probability code. The decision reduces to one question: *if someone guessed the next value, would it matter?*, with the sting that Mersenne is **recoverable from 624 outputs**, so "random, but it's just a session id" is how prediction attacks begin.

The benchmark prices the asymmetry: a Mersenne draw is **18 ns** of arithmetic; a `secrets` token is **~825 ns**, a kernel crossing, the retail cost of unpredictability, which amortises away in bulk (the grain rule again).

**This is a Deep P chapter.**
Chapter 124 owns KDFs, timing-safe comparison, and the crypto discipline these tokens feed. This chapter owns the two generators and the line between them.

## Section index

- **123.1** Reproducible and unpredictable, side by side
- **123.2** The model: a PRNG's state, a CSPRNG's pool
- **123.3** Measurement: the price of unpredictability
- **123.4** Edges and failure modes
- **123.5** Connections
- **123.6** Exercises
- **123.7** Summary and cross-references

Listings live under `code/ch204/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 123.1 Reproducible and unpredictable, side by side

```python
# code/ch204/l01_two_kinds_of_random.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- seeded means reproducible - this page is the proof ---
  Random(42).random() x3 : [0.639427, 0.025011, 0.275029]
  randrange(1000) x5     : [228, 142, 754, 104, 692]
  shuffle(range(10))     : [3, 2, 4, 9, 5, 7, 0, 6, 1, 8]
  gauss(0, 1) x3         : [-1.4707, -0.5956, -0.314]
  same seed, same sequence, on every interpreter in the matrix -
  the property simulations and tests build on, and the property
  that makes these lines verifiable at all
--- instances, not the module globals ---
  two Random(7) agree      : True
  module-level, after an interloping call, your first draw
  equals what should have been your SECOND : True
  module functions share ONE hidden global generator: any library
  that also calls random.random() shifts your sequence. pass a
  Random(seed) instance through your code; the module namespace is
  for throwaway scripts
--- weighted and sampled, still reproducible ---
  choices(ABC, weights=[5,3,1], k=8) : AAABBAAB
  sample(range(100), 5)              : [33, 70, 29, 24, 91]
  choices draws WITH replacement (weights allowed); sample draws
  WITHOUT (a k-subset) - mixing them up is the off-by-one of
  probability code
--- secrets: the values cannot be on this page ---
  token_urlsafe(32) length : 43 chars (43 = ceil(32 * 4/3), Chapter 120's arithmetic)
  alphabet is urlsafe-b64  : True
  1,000 tokens, all unique : True
  randbelow(10) in range   : True
  secrets reads the OS entropy pool (os.urandom): no seed, no
  sequence, no reproduction - which is the entire point, and why
  only PROPERTIES of its output can appear in a verified book
```

**The seeded block is the reproducibility contract, exercised across the matrix.**
`random`, `randrange`, `shuffle`, `gauss`, all deterministic given the seed, all byte-identical on three interpreters, which is *why* the harness can verify them and why every Monte Carlo result, property-based test, and shuffled-fixture in this book pins a seed. The guarantee is CPython's, documented and stable across versions for the core methods; leaning on it is correct engineering, not fragility.

**The instances block is the multi-tenant lesson.**
Two `Random(7)` objects agree because each owns its state; the module-level `random.*` functions share *one* global generator, so an interloping call, from a library, a logging filter, a dependency, advances *your* sequence, and the listing proves it: after one hijacking call, your "first" draw equals what should have been your second. The rule is absolute for anything that must reproduce, **pass a `Random(seed)` instance explicitly**; the module namespace is for throwaway scripts where reproduction does not matter.

**The choices/sample block is one distinction that causes real bugs.**
`choices` draws *with* replacement and accepts weights (a die, a loaded sampler); `sample` draws *without* (a k-subset, a lottery, a train/test split). Using `choices` where `sample` was meant silently allows duplicates, the off-by-one of probability code, invisible until a "unique" set has a repeat.

**And the secrets block teaches by absence.**
No value is quoted because none can be; the *properties* verify instead, and the length line ties back to Chapter 120 (a token is base64 over random bytes, so its character count is the expansion arithmetic). This is the chapter's method: the thing you cannot print is exactly the thing you must not make predictable.

---

## 123.2 The model: a PRNG's state, a CSPRNG's pool

**Mersenne Twister is a large state machine, and its virtues are its vices.**
19,937 bits of state, period 2^19937-1, excellent statistical distribution, and a fast integer recurrence, ideal for simulation. But the state is *recoverable*: observe 624 consecutive 32-bit outputs and you can reconstruct the generator and predict all future values. That single fact partitions every use: acceptable wherever prediction is harmless (games' visuals, sampling, load generation, tests), disqualifying wherever prediction is *profit* (tokens, keys, nonces, anything an adversary benefits from foreseeing). "It looks random" is not the criterion; "can the observer extend the sequence" is.

**`secrets` and `SystemRandom` are the same source behind two faces.**
Both draw from `os.urandom`, the OS CSPRNG (getrandom/BCryptGenRandom), which mixes hardware and environmental entropy and is designed so that observing outputs reveals nothing about future ones. `secrets` adds the *ergonomics of not getting it wrong*: `token_urlsafe`/`token_hex`/`token_bytes` at safe default sizes, `randbelow` without modulo bias, `choice` over a sequence, and `compare_digest` re-exported (Chapter 124). There is no seed because a seed is the attack, the API's shape is the discipline.

**Bias is the subtle failure the safe API removes.**
`secrets.randbelow(n)` is uniform; the naive `os.urandom(1)[0] % n` is *not* (values below `256 % n` occur once extra), a bias that has weakened real token generators. Reaching past `secrets` to roll your own from `urandom` reintroduces exactly the bug the module exists to prevent, the reason "use `secrets`, not `random`, for security" is really "use the safe constructor, not clever arithmetic".

**And the decision is a single question with a one-way cost.**
*If someone guessed the next value, would it matter?* No, `random.Random(seed)`, reproducible and 40x faster. Yes, `secrets`, and the asymmetry is why the default for anything security-adjacent is `secrets`: the cost of using it needlessly is a few hundred nanoseconds; the cost of using `random` where `secrets` was needed is a CVE.

---

## 123.3 Measurement: the price of unpredictability

**Methodology.** `code/ch204/bench_entropy_costs.py`.
`min` of 15 (9 for system rows, 7 for bulk); 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. One value at a time:**

| draw | time | vs mersenne |
|---|---|---|
| `mersenne.random()` | 18.1 ns | 1.00x |
| `mersenne.randrange(1000)` | 120 ns | 6.6x |
| `system.random()` | 736 ns | 40.7x |
| `secrets.token_bytes(16)` | 826 ns | 45.7x |
| `secrets.token_urlsafe(16)` | 993 ns | 54.9x |

**b. A megabyte of bits:** `getrandbits(8M)` (PRNG) 1.15 ms; `os.urandom(1 MB)` (kernel) 3.31 ms (2.9x).

**Table a prices unpredictability at retail.**
The Mersenne draw is 18 ns of pure arithmetic on in-process state; every `secrets`/`system` value crosses into the kernel, ~800 ns, and that microsecond-class gap *is* the cost of unpredictability per value, not the entropy itself. `token_urlsafe`'s extra ~170 ns over `token_bytes` is Chapter 120's base64 (measured, composed). For a login path minting one token per request, the 800 ns is invisible; for anything looping, it is the grain rule (Chapter 100) restated: **draw in sensible units** (a 16-byte token is *one* crossing, never sixteen `secrets.choice` calls).

**Table b shows the crossing amortising.**
In bulk the kernel is only 2.9x the PRNG (both at hundreds of MB/s), because the per-call syscall tax, table a's real subject, is paid once per megabyte instead of once per value. The design consequence: never generate bulk secret material by looping a per-value secrets call; ask for the bytes you need in one request, then slice.

**Book I** draws from the same OS pool through `getrandom` and its PRNG is a faster xoshiro, but the two-professions conclusion is identical and its security chapter states this one's rule verbatim: seedable generators for simulation, the OS pool for secrets, and never the wrong one, because the failure is silent and the review catches it or the attacker does.

---

## 123.4 Edges and failure modes

**`random.seed()` on the module global is a shared mutation.**
Seeding for reproducibility while a dependency also uses the module generator is the instances-block bug at scale: your seed resets *their* sequence too, and interleaving destroys both. Reproducible code owns a `Random` instance; the module functions are for code that does not care.

**Cross-version reproduction covers the core, not everything.**
The documented methods (`random`, `getrandbits`, `randrange`, `shuffle`) reproduce across CPython versions; some distribution methods and internal details may not, and *other implementations* (PyPy, NumPy's generators) differ entirely. Pin the generator *and* the platform when reproduction is a contract (Chapter 114's discipline, applied to randomness).

**NumPy's randomness is a separate world.**
`np.random` has its own state, its own seeding (the modern `default_rng`), and does not share Mersenne with the stdlib; scientific code routinely seeds one and forgets the other, then wonders why results wander. Seed every generator a computation touches, or route all randomness through one injected source.

**Modulo bias is real and `secrets` is the fix, not `%`.**
`secrets.randbelow(n)` and `secrets.choice(seq)` are unbiased; `urandom-then-%` is not. Any hand-rolled "random in range" over `urandom` is a bug candidate; the safe constructors exist precisely so nobody re-derives the bias.

**Token *length* is entropy, not character count.**
`token_urlsafe(n)` is `n` bytes of entropy (~1.3 chars each); shortening the *string* to save space silently cuts entropy, and 8-byte tokens are guessable at scale. Size tokens by the bits an attacker must not brute-force (128+ for anything long-lived), and let Chapter 120's arithmetic set the visible length.

**Forking shares PRNG state.**
After `os.fork` (Deep R), parent and child inherit identical `random` state and produce identical sequences, a classic source of duplicate "random" ids across workers. Re-seed per child, or use `secrets`/`SystemRandom`, which read fresh entropy and are fork-safe by construction, the free-threaded build's shared state raises the same flag for threads that share a module-level generator (Chapter 96's sharing rules apply to the hidden global too).

**And "unguessable" degrades with exposure.**
A token that leaks in a URL, a log, a referrer header is no longer secret however well it was generated; entropy protects against *guessing*, not against *disclosure*. That boundary is Chapter 124's, flagged here so the token's strength is not mistaken for the system's.

---

## 123.5 Connections

**Backward.**
The base64 arithmetic that sets a token's length, Chapter 120; the OS entropy pool `os.urandom` reads, Deep R; the reproducibility discipline pinning artifacts, Chapter 114; the grain rule behind drawing secrets in units, Chapter 100; shared-state hazards for the module global, Chapter 96.

**Forward.**
What the tokens become, session ids, reset links, API keys, and the KDFs, timing-safe comparisons, and constant-time discipline that keep them safe, Chapter 124, which closes the volume.

**Across books.**
**Book I** splits PRNG from CSPRNG the same way (a fast engine for simulation, `getrandom` for secrets) and adds counter-based generators for reproducible *parallel* streams, the free-threaded frontier this chapter's stdlib does not yet reach; both books end on the single question and the one-way cost.

---

## 123.6 Exercises

**1. Reproduce across the matrix.** Verify the listing's seeded lines on every interpreter you have, then break one by switching to the module global and interleaving a library call; show the drift and fix it with an instance.

**2. Recover the generator.** Feed 624 `getrandbits(32)` outputs into a Mersenne state-recovery routine (any published one) and predict the next draw. Then show the same attack producing nothing against `secrets`. File it under why session ids are not `random`.

**3. Measure the bias.** Sample `urandom(1)[0] % 3` a million times and chi-square it against uniform; repeat with `secrets.randbelow(3)`; report the bias and its magnitude.

**4. Fork duplication.** Fork four workers that each print `random.random()` with and without per-child re-seeding; show the duplication and both fixes (re-seed, or `SystemRandom`).

**5. Size a token honestly.** For a password-reset link valid one hour at 10^4 requests/sec of guessing, compute the minimum entropy for a 10^-12 forge probability; pick `token_urlsafe(n)` and justify n.

**6. The design question.** `secrets` is a thin ergonomic layer over `os.urandom` that mostly exists to stop people writing `random.choice` for tokens and `urandom % n` for ranges, a module whose value is the mistakes it prevents, not the capability it adds. Argue whether that belongs in a stdlib (the pedagogical win, the CVE record it addresses) versus documentation alone, and what the *next* such module should be (a KDF-ergonomics layer? Chapter 124 has candidates). Defend your answer with the modulo-bias and wrong-generator failure rates you can find in real breach post-mortems.

---

## 123.7 Summary and cross-references

- **Two modules, opposite questions**: `random` (Mersenne) is deterministic and seedable, `Random(42)` verifies byte-identically across the matrix, the reproducibility guarantee demonstrated; `secrets` reads the OS pool and is unpredictable by design, so its output can only be shown by *properties*, which is the same lesson inverted.
- **The decision is one question**: if guessing the next value would matter, use `secrets`; else `random.Random(seed)`, passed explicitly. Mersenne is **recoverable from 624 outputs**, so "just a session id" is where prediction attacks start.
- **The two traps**: the module functions share one hidden global generator (an interloping call shifts your sequence, proven), and `choices` (with replacement, weighted) versus `sample` (without) is probability code's off-by-one.
- **Priced**: Mersenne 18 ns, a `secrets` token **~825 ns** (a kernel crossing; +170 ns for base64), amortising to 2.9x in bulk, so draw secrets in units, never loop per-value.
- **The edges that ship bugs**: shared-global seeding, cross-version/NumPy reproduction gaps, modulo bias (use the safe constructors), token *length* as entropy not characters, fork/thread-shared PRNG state, and the reminder that entropy resists guessing, not disclosure.

**Cross-references.** Token length arithmetic → Chapter 120. `os.urandom` and the OS pool → Deep R. Reproducible artifacts → Chapter 114. The grain rule → Chapter 100. Shared-state hazards → Chapter 96. KDFs, comparison, and secret discipline → Chapter 124.
