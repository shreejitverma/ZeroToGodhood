# Chapter 15: The PEG Parser, Dict Union, and Pattern Matching (Python 3.9-3.10)

A developer writes what looks like a clean status-code dispatch with the new `match` statement:

```python
OK = 200
def handle(code):
    match code:
        case OK:
            return "handled as OK"
```

They test it with `handle(200)`, it works, they ship it. Then `handle(404)` also returns `"handled as
OK"`. So does `handle(500)`, and every other code. The bug is not a typo; it is the single most
important rule in structural pattern matching, and it is invisible until it fires: **a bare name in a
pattern captures, it does not compare.** `case OK:` does not test `code == OK`; it binds `code` to a
new local named `OK` and matches *everything*.

That rule is the sharp edge of the most visible syntax addition since Python 3.0. The 3.9-3.10 cycle
delivered **structural pattern matching** (`match`/`case`, PEP 634), which became possible only because
3.9 replaced the 30-year-old LL(1) parser with a **PEG parser** (PEP 617) capable of the richer
grammar. The same window added the small but daily-useful **dict union operators** `|` and `|=` (PEP
584). This chapter treats pattern matching as the deep topic, because it is *destructuring plus
matching*, not a C `switch`, and it is precise about the capture rule and about one performance
assumption that does not hold.

## Section index

- **15.1** The PEG parser and dict union (PEP 617, PEP 584)
- **15.2** Structural pattern matching (PEP 634)
- **15.3** The capture-versus-value gotcha
- **15.4** Measurement: match is readability, not speed
- **15.5** Edges and failure modes
- **15.6** Connections
- **15.7** Exercises
- **15.8** Summary and cross-references

Listings live under `code/ch015/` and are re-executed by `make verify` on both interpreters.

---

## 15.1 The PEG parser and dict union (PEP 617, PEP 584)

Chapter 2 covered the LL(1)-to-PEG transition; here is what it *bought* the language. The PEG parser
brings **ordered choice** (`e1 / e2`, first match wins deterministically) and **unlimited lookahead**
with **packrat memoization** (caching each rule-at-position result keeps parsing linear-time). Freed
from one-token lookahead, the grammar could express constructs the old parser could not, most visibly
the parenthesized multi-line context managers of 3.10, which the old parser could not distinguish from
a parenthesized tuple without arbitrary lookahead. The rewrite also improved error messages and made
the `match` grammar feasible.

The same release added dict union:

```python
# code/ch015/l01_peg_and_dict_union.py
d1, d2 = {"a": 1, "b": 2}, {"b": 99, "c": 3}
```

Verified output (CPython 3.13.5):

```text
--- dict union: | merges into a new dict, |= updates in place ---
  d1 | d2 (right key wins): {'a': 1, 'b': 99, 'c': 3}
  merged |= d2            : {'a': 1, 'b': 99, 'c': 3}
--- | requires a mapping on the right; a non-mapping raises ---
  d1 | [1, 2] -> unsupported operand type(s) for |
```

**PEP 584** gave `dict` the binary `|` (merge into a new dict) and `|=` (in-place update), mapping to
the `nb_or`/`nb_inplace_or` slots. Right-hand keys win on collision. Two semantics worth noting: `|`
always returns a plain `dict` even for `dict` subclasses, and `|=` accepts any mapping (or an iterable
of key/value pairs, like `update`) on the right while `|` requires a mapping. Prefer `|`/`|=` for
readability; `{**a, **b}` remains valid and, as §15.4 measures, merges at the same speed.

---

## 15.2 Structural pattern matching (PEP 634)

**Why this exists, and what it is not.** `match`/`case` is *not* a C/Java `switch` (which only compares
a scalar against constants). It is structural matching: each `case` is a *pattern* that simultaneously
tests the *shape* of the subject and *binds names* from its components, closer to Rust's `match` or
ML-family destructuring. It shines when branching on the structure of data: ASTs, JSON-ish messages,
command tokens, geometric types.

```python
# code/ch015/l02_pattern_matching.py
def classify(x):
    match x:
        case 0:                              # literal (value) pattern
            return "zero"
        case [a, b, *rest]:                  # sequence with star-capture
            return f"seq:{a},{b},rest={rest}"
        case {"type": t, "value": v}:        # mapping pattern (subset of keys)
            return f"map:{t}={v}"
        case str() as s if len(s) > 3:       # class pattern + as-binding + guard
            return f"long-str:{s}"
        case int() | float():                # OR pattern
            return f"number:{x}"
        case _:                              # wildcard
            return "unknown"
```

Verified output (CPython 3.13.5):

```text
--- the pattern taxonomy over mixed subjects ---
                           0 -> zero
                         [7] -> one-list:7
                [1, 2, 3, 4] -> seq:1,2,rest=[3, 4]
  {'type': 'pt', 'value': 9} -> map:pt=9
                     'hello' -> long-str:hello
                         3.5 -> number:3.5
                      (1, 2) -> seq:1,2,rest=[]
```

Note that `(1, 2)` matched the *sequence* pattern: sequence patterns match any
`collections.abc.Sequence` *except* `str`/`bytes`/`bytearray`, deliberately excluded so a string is not
destructured character by character. Mapping patterns match a *subset* of keys. Class patterns use
`__match_args__` to map positional sub-patterns to attributes, so `case Point(0, 0)` and `case Point(x,
0)` destructure a `Point` by its declared field order.

**What the compiler does.** A `match` does not compile to a linear `if/elif` chain; it builds a decision
tree with dedicated opcodes:

```text
--- the compiler builds a decision tree, not an if/elif chain ---
  shape-testing opcodes in seqmatch: ['MATCH_SEQUENCE', 'GET_LEN', 'UNPACK_SEQUENCE']
  these test shape once and fail fast BEFORE binding, so a half-matched
  pattern never leaks a partial binding.
```

`MATCH_SEQUENCE`, `MATCH_MAPPING`, `MATCH_KEYS`, `MATCH_CLASS`, plus `GET_LEN`/`UNPACK_SEQUENCE`, test
the shape once and fail fast. Bindings happen only on the success path, so a failed sub-pattern cleans
the stack and tries the next case, and a half-matched pattern never leaks a partial binding. This is a
correctness property, not a speed one, as §15.4 shows.

---

## 15.3 The capture-versus-value gotcha

The chapter opened with the rule that bites everyone. In a pattern, an unqualified name is a *capture
pattern*: it matches anything and binds the name. It is *not* a comparison against a variable of that
name. To compare against a named constant, use a *dotted (value) pattern*:

```python
# code/ch015/l03_capture_gotcha.py
OK = 200
def handle(code):
    match code:
        case OK:                      # captures ALL codes; does not compare to 200
            return f"treated {code} as OK"
```

Verified output (CPython 3.13.5):

```text
--- a bare-name capture silently matches everything ---
  handle(404): treated 404 as OK  <- not 200, still 'OK'
  handle(500): treated 500 as OK  <- also silently 'OK'
--- a dotted value pattern compares instead of capturing ---
  check(200): ok
  check(404): other
--- 3.13 rejects a capture that makes remaining patterns unreachable ---
  SyntaxError: name capture 'NAME' makes remaining patterns unreachable
```

`handle(404)` returns `"treated 404 as OK"` because `case OK:` bound `code` to a local and matched.
`check`, using the dotted `case http.HTTPStatus.OK:`, compares by equality and correctly returns
`"other"` for 404. Python 3.13 added a safety net: a bare-name capture *before* other cases makes them
unreachable and is a compile-time `SyntaxError`. But note the limit of that net, which the listing
states explicitly: **it only fires when the capture shadows a *later* case.** A capture as the only or
last case, like `handle` above, still compiles and silently matches everything. The net catches the
obvious mistake, not the chapter-opening one. Use dotted value patterns for constants, always.

---

## 15.4 Measurement: match is readability, not speed

§15.2 said the compiler builds a decision tree that "tests shape once and fails fast." That is true, and
it is easy to read as a performance claim. It is not one. The class-pattern protocol (an `isinstance`
check, then a `__match_args__` lookup, then attribute extraction) is *more* work than direct attribute
access, so `match` is slower than an equivalent hand-written `if/elif`, not faster.

**Methodology.** `code/ch015/bench_match.py`. The same `Point` dispatch written as a `match` and as an
`if/elif` that does the *same* `isinstance` guard `MATCH_CLASS` performs implicitly, so the comparison is
fair. `min` over 15 batches; within one interpreter; CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| structural dispatch | ratio |
|---|---|
| hand-written `if/elif` (same checks) | 1.00x |
| `match` | **4.34x** |

**`match` is about 4.3x slower** than the equivalent `if/elif` for this dispatch. The decision tree is
real, but each `MATCH_CLASS` runs the full class-pattern protocol, which costs several times a direct
`p.x == 0`. So `match` is a *readability and expressiveness* feature: reach for it when destructuring a
complex shape (a nested message, an AST node, a sequence with a star-capture) makes the code clearer,
not when you want it faster than an `if` chain. For a scalar against a few constants, an `if/elif` or a
dict dispatch is both clearer and faster.

The dict union operators, by contrast, cost nothing over the alternatives:

| dict merge | ratio |
|---|---|
| `|` operator | 1.00x |
| `{**a, **b}` | ~1.0x |
| `copy()` + `update()` | 1.28x |

`|` and `{**a, **b}` merge at the same speed, and both beat the two-statement `copy`-then-`update`. Here
the readable choice is also the fast one, so `|`/`|=` win on both counts.

---

## 15.5 Edges and failure modes

**A bare name captures.** §15.3. `case OK:` binds and matches everything; it does not compare. Use a
dotted value pattern (`case module.OK:`) for constants. The 3.13 safety net only catches captures that
shadow *later* cases.

**`match` for plain equality.** §15.4. For a scalar against a few constants, `if/elif` or a dict
dispatch is clearer and ~4x faster. `match` earns its keep on *structure*, not on scalar comparison.

**The str/bytes exclusion.** §15.2. `case [x, y]:` does not match `"ab"`; sequence patterns exclude
`str`/`bytes`/`bytearray`. Match strings with `str()` patterns or guards.

**Mapping patterns are subset matches.** `case {"id": i}:` matches any mapping containing `"id"`,
including one with extra keys. Use `**rest` to capture the remainder, or a guard to assert exactness.

**`|` requires a mapping.** §15.1. `d | [1, 2]` raises `TypeError`; only `|=` accepts an iterable of
pairs. And `|` always returns a plain `dict`, dropping any subclass.

**`__match_args__` is a public contract.** The positional destructuring order of your class is API;
changing it silently breaks every `case ClassName(a, b):`. Dataclasses set it from field order (Chapter
13), so reordering dataclass fields is a breaking change for pattern matching.

---

## 15.6 Connections

**Backward.** The LL(1)-to-PEG transition in depth is Chapter 2; this chapter is what PEG bought.
`{**a, **b}` unpacking is Chapter 11. `__match_args__` on dataclasses, and the frozen-slotted record
that pattern matching destructures, is Chapter 13. Enums in `match` (dotted value patterns over enum
members) are Chapter 10.

**Forward.** The formal grammar and the parser internals are **Deep S**. dict internals and `update`
semantics are **Deep A**. Builtin generics (PEP 585) and `X | Y` unions (PEP 604), which reuse the same
`|` operator at the type level, are Chapter 16, the next chapter.

**Across books.** Structural pattern matching is how Book II cleanly consumes the semi-structured
messages that cross both seams. A tool-call result from **Book III** arrives as a JSON-ish dict, and a
`match` over its shape (`case {"type": "tool_result", "content": c}:`) dispatches it far more readably
than nested `.get()` checks, at the ~4x cost §15.4 measured, which is invisible next to the model call
that produced it. The order-book's command protocol from **Book I** is dispatched the same way. **Deep
U** and **Deep M** own those seams; `match` is the readable dispatcher over what crosses them.

---

## 15.7 Exercises

**1. Reproduce the silent capture.** Write the chapter-opening `handle` function and confirm it treats
every code as OK. Then add a second `case` after it and show the 3.13 `SyntaxError` appears. Explain why
the single-case version compiles while the two-case version does not, in terms of what the safety net
actually checks.

**2. Measure your own dispatch.** Reproduce §15.4's `match`-vs-`if/elif` benchmark, then make the shape
more complex (a three-level nested structure). Predict whether `match`'s relative cost grows or shrinks
as the destructuring deepens, and measure it. At what complexity does `match`'s readability clearly
justify the 4x?

**3. Break a `__match_args__` contract.** Define a class with `__match_args__`, write a `case` that
destructures it positionally, then reorder the fields and show the `case` now binds the wrong
attributes. Explain why this is a silent bug and how you would catch it.

**4. Exploit the subset match.** Write a mapping pattern that matches any dict containing certain keys,
demonstrate it matches a dict with extra keys, then tighten it to reject extras. Explain the two ways
(a guard, or `**rest` with a length check) and their trade-offs.

**5. The design question.** Python chose capture-by-default for bare names in patterns, which is what
makes the chapter-opening bug possible, rather than compare-by-default (which Rust avoids by requiring
patterns to be irrefutable or explicit). Argue whether capture-by-default was the right choice. Your
answer must address what compare-by-default would cost (how would you then bind a name?), why the
dotted-value escape hatch exists, and whether the 3.13 safety net is a fix or an admission.

---

## 15.8 Summary and cross-references

- The **PEG parser** (PEP 617, 3.9), ordered choice plus unlimited lookahead plus packrat memoization,
  replaced LL(1) and unlocked richer syntax (parenthesized context managers, the `match` grammar).
- **`|`/`|=`** (PEP 584) merge and update dicts; `|` returns a plain `dict`, right keys win, non-mappings
  raise `TypeError`.
- **Structural pattern matching** (PEP 634) is **destructuring plus matching**, compiled to a decision
  tree (`MATCH_SEQUENCE`/`MATCH_CLASS`/...). Patterns: literal, capture, wildcard `_`, sequence (excludes
  str/bytes), mapping (subset), class (via `__match_args__`), `|` OR, `as` binding, `if` guards.
- **A bare name captures, it does not compare.** Use a dotted value pattern for constants; the 3.13
  safety net only catches captures that shadow *later* cases.
- **Measured:** `match` is about **4.3x** slower than an equivalent `if/elif` for structural dispatch,
  so it is a readability feature, not a speed one; `|` and `{**a, **b}` merge at the same speed and both
  beat `copy`+`update`.

**Cross-references.** LL(1)-to-PEG → Chapter 2. `{**a, **b}` → Chapter 11. `__match_args__` on
dataclasses → Chapter 13. Enums in `match` → Chapter 10. The formal grammar → Deep S. dict internals →
Deep A. `X | Y` type unions → Chapter 16. The message-dispatch seams to Books I and III → Deep M and
Deep U.
