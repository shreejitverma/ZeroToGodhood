# Chapter 261: The Secrets Module

## The constraint

For years, Python programmers generated the things that must be *unguessable* - password-reset tokens, session IDs, API keys, one-time codes - using the `random` module, because it was the obvious place to look for randomness.
And that was a genuine security vulnerability, quietly shipped in a great deal of production code.

The `random` module is a Mersenne Twister: a fast, high-quality *pseudo*-random generator designed for simulations and sampling, where reproducibility is a *feature*.
It is seeded from a relatively small internal state, and its entire future output is determined by that state.
`random.seed(0)` makes it fully deterministic - the same sequence every time - which is exactly what you want for a reproducible experiment and exactly what you must never have for a secret.
Worse, the generator is not cryptographically strong: an attacker who observes enough of its output can reconstruct the internal state and predict all future values.
Using it to mint session tokens means an attacker who collects a few tokens may be able to predict the next one.

The problem was not that programmers were careless; it was that the standard library offered `random` prominently and offered no obvious, correct alternative for the security case.
The constraint Python 3.6 (2016, PEP 506) answered: **give "generate an unguessable value" a correct, obvious home in the standard library, so nobody reaches for `random` by mistake.**

This chapter owns no Deep-Volume mechanism; cryptographic randomness is a security-domain capability, not a language feature.
What it owns is the release: the day secure token generation got its own module.

## What shipped

The `secrets` module provides a cryptographically strong generator (drawing from the operating system's entropy source), token helpers in the shapes real uses need, secure analogues of `random`'s selection functions, and a constant-time comparison for checking tokens safely.
Listing 261.1 shows all of it on today's interpreters, checking structure and the predictability *contrast* rather than raw secret values.

Verified output (CPython 3.13.5):

```text
--- the danger: random is REPRODUCIBLE, so its output is guessable ---
  random.seed(0); random.random() twice equal? : True
  seeding random with the same value gives the SAME sequence - by
  design, for reproducible simulations. for a token that means: know
  the seed (or enough outputs) and you can reproduce every 'secret'
--- secrets has no seed: its output cannot be reproduced ---
  secrets module has a seed() function? : False
  secrets draws from the OS cryptographic entropy source, so there is
  nothing to seed and nothing to reproduce. that unpredictability is
  the whole point - it is the correct tool for anything secret
--- token helpers: the right output shapes for real uses ---
  token_hex(16)     length : 32   (32 hex chars = 16 bytes)
  token_hex is all hex digits : True
  token_urlsafe(16) type   : str
  token_bytes(16)   length : 16 bytes
  token_hex for a hex string, token_urlsafe for a URL/cookie value,
  token_bytes for raw bytes - the shapes session IDs and reset tokens
  actually need, each cryptographically strong
--- secrets.choice / randbelow for secure selection ---
  an 8-char secure code drew from the alphabet : True
  secrets.randbelow(100) is in [0, 100) : True
  choice() and randbelow() are the secure analogues of random's -
  use them when the SELECTION must be unpredictable (a one-time code,
  a temporary password), not just statistically random
--- compare_digest: constant-time comparison against timing attacks ---
  compare_digest(equal)   : True
  compare_digest(unequal) : False
  == on secrets can leak via TIMING: it returns early at the first
  differing byte, so response time reveals how much of a guess was
  right. compare_digest takes constant time regardless, closing that
  side channel - use it to check tokens and signatures
--- the constraint answered ---
  the random module is reproducible pseudo-randomness for simulations,
  and using it for tokens is a real vulnerability. secrets (3.6) gave
  cryptographically strong generation an obvious home: token_hex/
  urlsafe/bytes for IDs, choice/randbelow for secure selection, and
  compare_digest for safe checking. 'unguessable token' got a correct default
```

## Why each part answers the constraint

**`random` is reproducible - that is the danger.**
The first block demonstrates the flaw: `random.seed(0)` followed by `random.random()`, done twice, produces the *same* value.
This reproducibility is a feature for simulations and a fatal flaw for secrets: if the seed is known or guessable (and process seeds often are), or if enough outputs are observed, the entire sequence is recoverable.
A "random" token from `random` is, to a determined attacker, not random at all.

**`secrets` has no seed.**
The second block shows the structural difference: `secrets` has no `seed` function, because it draws from the OS cryptographic entropy source and there is nothing to seed.
Its output cannot be reproduced by anyone, which is precisely the property a secret requires.
The absence of a seed is not a missing feature - it is the guarantee.

**Token helpers in the right shapes.**
The third block shows the convenience layer: `token_hex(16)` gives 32 hex characters (16 bytes) of strong randomness, `token_urlsafe(16)` gives a URL-safe string suitable for cookies and query parameters, and `token_bytes(16)` gives raw bytes.
These are the exact output shapes that session IDs, reset tokens, and API keys need, each cryptographically strong by construction - so you neither hand-roll the encoding nor accidentally weaken it.

**Secure selection.**
The fourth block shows `secrets.choice` and `secrets.randbelow` - the secure analogues of `random.choice` and range selection - building an 8-character code from a confusable-free alphabet and a bounded random integer.
Use these whenever the *selection* must be unpredictable: a one-time code, a temporary password, a random assignment that must not be guessable.

**Constant-time comparison.**
The fifth block covers a subtler attack.
Comparing a secret with `==` can leak information through *timing*: `==` returns as soon as it finds a differing byte, so an attacker measuring response times can learn how many leading bytes of a guess were correct, and reconstruct the secret byte by byte.
`secrets.compare_digest` takes constant time regardless of where the strings differ, closing that side channel.
Use it to check tokens, signatures, and HMACs - anywhere you compare a user-supplied value against a secret.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; `secrets` is a thin, correct interface to the operating system's cryptographic randomness (`os.urandom` underneath) plus the helpers and constant-time comparison that secure token handling requires.
What the timeline records is the release act: in 3.6, PEP 506 gave secure random generation an obvious, well-named home, so the correct tool is the one a programmer naturally finds.
The modern consequence, verified above, is that `secrets` is the standard answer for tokens and codes, and reaching for `random` in a security context is recognized as the bug it always was.

## Where this lands

`secrets` is a small module whose value is entirely in *steering*: it makes the secure choice the obvious choice.
Use `random` for simulations, sampling, shuffling, games, and anything where reproducibility helps and secrecy does not matter.
Use `secrets` for anything an adversary must not predict: `token_hex`/`token_urlsafe`/`token_bytes` for identifiers and keys, `choice`/`randbelow` for secure selection, and `compare_digest` to check secrets without leaking timing.
The dividing line is simple - if guessing the value would be a security problem, it belongs in `secrets`.
No Deep Volume owns a cryptographic mechanism; this chapter is the record of the release that gave unguessable randomness a correct default.
