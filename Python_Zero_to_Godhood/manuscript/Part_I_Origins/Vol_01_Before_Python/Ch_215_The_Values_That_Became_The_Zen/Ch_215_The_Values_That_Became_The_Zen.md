# Chapter 3: The Values That Became the Zen

Chapters 1 and 2 read Python's lineage as decisions, keep ABC's ergonomics, adopt Modula's seams, run on C while rejecting its value model. But decisions need a compass, a set of values that says which way to decide when the record is silent, and Python's compass was set in 1989 and has barely moved since. The values, **readability**, **explicitness**, **one obvious way**, **practicality over purity**, were present in Guido's original fix-list long before Tim Peters distilled them, in 2004, into the twenty aphorisms of the **Zen of Python** (PEP 20).

The chronology matters and this chapter is careful about it: **the Zen codified the values; it did not create them.** The Zen postdates the design by fifteen years, so a chapter that cited the Zen as the *source* of Python's values would have its history backwards. Instead the listing shows the Zen where it lives (it ships in the interpreter, `import this`), then demonstrates two of its values not as slogans but as *running behaviour* on the verification interpreters, explicit name resolution, and errors that refuse to pass silently. The values are observable in how the language behaves, which is the only honest way a technical book can discuss them.

This is the last chapter of "Before Python": the ancestors (2) supplied mechanisms, this chapter supplies the values that governed their use, and Chapter 4 will show 1989's prototype as the two applied together.

## Section index

- **3.1** The problem: mechanisms need a compass
- **3.2** The Zen, where it actually lives
- **3.3** Explicit is better than implicit: names resolve by rule
- **3.4** Errors should never pass silently: the language insists
- **3.5** The values as constraints on the timeline
- **3.6** Edges: where the values tension with each other
- **3.7** Connections
- **3.8** Exercises
- **3.9** Summary and cross-references

Listings live under `code/ch215/` and are re-executed by `make verify` on the verification interpreters.

---

## 3.1 The problem: mechanisms need a compass

A language is a sequence of decisions, and Chapters 1-2 showed Python's earliest ones. But decisions accumulate for decades, made by different people, under pressures the original designer never saw, and without a shared compass they drift into incoherence, the language that adds every requested feature becomes a language with no character and a hundred ways to do everything. Python did not drift, and the reason is that its values were explicit, widely shared, and applied as a *filter* on proposals: a feature that violated readability or added a second obvious way was argued for years or rejected outright.

The values were not written down at first, they were Guido's taste, exercised in review. But taste does not scale to a community, so in 2004 Tim Peters wrote them down as PEP 20, and "the Zen of Python" became the compass every subsequent design argument could cite. The Zen is not a specification, no compiler checks it, but it is the most-cited document in Python's design discourse, because it names the values a proposal must not violate.

---

## 3.2 The Zen, where it actually lives

```python
# code/ch215/l01_the_values_that_became_the_zen.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the Zen ships in the interpreter (PEP 20, 2004) ---
  'import this' prints 20 aphorisms
  first : 'Beautiful is better than ugly.'
  last  : "Namespaces are one honking great idea -- let's do more of those!"
  the Zen is a 2004 distillation (Tim Peters) of values present in
  the 1989 design - it codified them, it did not invent them
```

**The Zen is not documentation about Python; it is *in* Python.**
`import this` prints it, an Easter egg that is also a statement, the language's values ship with the language. The count is 19 aphorisms under a one-line title (20 non-empty lines), from "Beautiful is better than ugly" to "Namespaces are one honking great idea", the last a direct callback to Modula's module inheritance (Chapter 2). That the Zen closes on namespaces is not accidental: the module-as-namespace was one of the seams that made Python growable, and Tim Peters ending the Zen there is the community recognising its own foundation.

**The dating discipline is the chapter's point.**
Python is from 1989; the Zen is from 2004. The values (readability, explicitness) are observable in the 1989 design (Chapter 1's indentation-as-grammar is "readability counts" made syntax); the *aphorisms* are a later distillation. A book that said "Python was designed according to the Zen" would invert cause and effect, so this book says the opposite: the Zen is a photograph of values already fifteen years old, taken by someone who knew them well. The rest of the chapter shows those values as behaviour, which is where they actually reside.

---

## 3.3 Explicit is better than implicit: names resolve by rule

```text
--- 'explicit is better than implicit': names resolve by rule ---
  a name resolves to the nearest ENCLOSING binding : 'enclosing'
  no implicit global fallback surprise here        : 'module-level'
  Python resolves names by an explicit rule (local, enclosing,
  global, builtin) - not by an implicit 'whatever is in scope'.
```

**Explicitness is a value with a mechanism, and name resolution is where you see it.**
A name in `inner` resolves to the nearest *enclosing* binding (`'enclosing'`), following the LEGB rule, local, enclosing, global, builtin, in a defined order, and the module-level `x` is untouched. There is no implicit "look wherever" fallback, no dynamic scoping where a name means whatever the caller happened to have. The rule is explicit, the resolution is predictable, and "explicit is better than implicit" is not a slogan here but the observable behaviour of the scope system (Chapter 75, Deep H, own the mechanism; this chapter owns why it is shaped this way).

**The senior-engineer contrast is with languages that chose implicitness.**
Dynamic scoping (early Lisps, some shells) resolves a name against the *caller's* environment, which is powerful and unpredictable, the same name means different things depending on who called you. Python rejected this for lexical (static) scoping with the explicit LEGB rule, because a value the language holds, that code should mean what it says where it is written, requires that names resolve by their textual position, not by runtime happenstance. The value chose the mechanism.

---

## 3.4 Errors should never pass silently: the language insists

```text
--- 'errors should never pass silently': the language insists ---
  1/0 does not return 0 or NaN silently : raised ZeroDivisionError
  {}['missing'] raises, not returns None : KeyError
  a language that returned a default on error would be 'convenient'
  and wrong; Python raises, because a silent error is a bug you
  find in production instead of at the call site
```

**The language refuses to make errors convenient, and that refusal is a value.**
`1/0` raises `ZeroDivisionError` rather than returning `0`, `NaN`, or `inf`; `{}['missing']` raises `KeyError` rather than returning `None`. Both refusals are deliberate, and both are the opposite of "convenient". A language that returned a default on error would let more programs *run*, and let more programs be *silently wrong*, the error surfacing arbitrarily later, in production, far from its cause. Python's Modula-3-inherited exception model (Chapter 2) is deployed here in service of a value: errors should surface at the call site, loudly, where they can be understood.

**This value underwrites an entire deep volume.**
Deep O's testing, debugging, and observability discipline rests on errors being loud: a test can assert a `raises`, a debugger can break on an exception, a log can capture a traceback, *because* the error did not pass silently. Contrast JavaScript's `undefined`-on-missing-key or SQL's `NULL`-propagation, both "convenient", both sources of famous bug classes. Python chose the loud path, and the choice is why "errors should never pass silently, unless explicitly silenced" (the aphorism's full form) is a value with teeth: silencing an error requires an explicit `try/except pass`, which review can see and question.

---

## 3.5 The values as constraints on the timeline

```text
--- the value, and the volume ---
  every release in the timeline that follows answers a constraint
  WITHOUT abandoning these values: readability, explicitness, one
  obvious way. when a feature would violate them (implicit magic,
  a second obvious way) it is argued for years or rejected - which
  is why Python's history is slow, deliberate, and coherent
```

**The values are why Python's history reads as coherent rather than accretive.**
Every release from Chapter 4 forward answers a *constraint*, a problem the world posed, but it does so under the values' filter: a mechanism that would violate readability, or add a second obvious way, or introduce implicit magic, is argued for years (the walrus operator's PEP 572 debate) or rejected (the many syntax proposals that died). This is why Python moves slowly and why its features, added over three decades by hundreds of people, still feel like one language. The Zen is the filter, and the timeline is the record of what passed through it.

**The anti-changelog rule this book follows is the values, formalised.**
"Every release chapter opens with the constraint the release was operating under, and every section answers that constraint" (the book's binding rule) is the same discipline the Zen imposes on design: a change must *answer a problem*, not merely add capability, and a change that does not answer the chapter's constraint goes to its owning Deep volume with a one-line note. The book's structure mirrors Python's design process because both are governed by the same values, and reading the timeline is watching those values applied, release after release, to the problems the world kept posing.

---

## 3.6 Edges: where the values tension with each other

**"One obvious way" versus "practicality beats purity".**
The Zen holds both, and they conflict: "there should be one, and preferably only one, obvious way to do it" argues against redundancy, while "practicality beats purity" argues for the redundant-but-useful. Python has string formatting three ways (`%`, `.format`, f-strings) because practicality won at each step while the community waited for the *one* obvious way (f-strings, Chapter 12) to arrive. The tension is real, and the timeline resolves it case by case, which is why the Zen is a compass, not an algorithm.

**"Explicit" versus "readability" at the extremes.**
Maximally explicit code (every type annotated, every import fully qualified) can be *less* readable than terser code, so "explicit is better than implicit" and "readability counts" pull apart when explicitness becomes noise. Python's optional typing (Deep I) sits exactly on this tension: types make contracts explicit but add visual weight, and the language made them *optional* precisely so each codebase can locate its own balance.

**"Simple is better than complex" versus the specializing interpreter.**
The Zen prizes simplicity, but CPython's interpreter became *dramatically* more complex (Deep H, the specializing adaptive interpreter) to make simple code fast. The value applies to the *language surface*, not the implementation: Python code stays simple while the runtime beneath it grows baroque, which is the whole subject of Deep K (performance without surfacing complexity to the programmer) and a deliberate reading of where "simple" is required and where it is not.

**And the values are not law.**
No compiler enforces the Zen; it is cited in arguments, not checked by tools. A codebase can violate every aphorism and still run, and some do. The values are a *culture*, transmitted through review and discourse, and their power is social, not mechanical, which is both their strength (they adapt) and their limit (they can be ignored). That a 2004 Easter egg became the community's constitution says more about the values' resonance than about any enforcement.

---

## 3.7 Connections

**Forward.**
The name-resolution mechanism the "explicit" value chose is Chapter 75 and Deep H. The exception model the "errors loud" value deploys is Chapter 6, Chapter 5, and Deep O. The "one obvious way" tension in string formatting resolves across Chapters 12 (f-strings) and their predecessors. The optional-typing balance point is Deep I. The specializing interpreter that keeps the surface simple while the runtime complexifies is Deep H and Deep K.

**Across books.**
The values are Python's, not universal: **Book I**'s C++ holds different values (zero-overhead abstraction, explicit resource management, performance as correctness), and the shared trading system lives at the seam between two value systems. Python's "readability counts" and C++'s "you don't pay for what you don't use" both apply to the system, in different tiers, and the boundary (Deep M, Chapter 84) is where a designer chooses which values govern which code, exactly the measured-choice thesis this series argues.

---

## 3.8 Exercises

**1. Read the whole Zen.** Run `import this`; for each aphorism, find one Python feature or standard-library API that embodies it and one that appears to violate it. The violations are where "practicality beats purity" won.

**2. Break the scope rule on purpose.** Construct a name-resolution puzzle where a reader would guess wrong about which binding a name resolves to (a `global` inside a nested function, a comprehension's scope). Explain how the *explicit* LEGB rule resolves it and why the explicitness prevents the bug.

**3. Silence an error correctly.** Take a `try/except pass` that hides a real error and rewrite it to silence *only* the specific expected exception, letting others propagate. Explain what "errors should never pass silently, unless explicitly silenced" requires of the `except` clause.

**4. Date the values.** For three Python features you use daily, find the PEP or release that introduced them and place each on the timeline; then argue which value in the Zen each was serving. The dating is the discipline; the value is the interpretation.

**5. The design question.** The Zen holds "one obvious way" and "practicality beats purity" simultaneously, and they conflict (three string-formatting mechanisms). Argue whether a language *should* hold conflicting values as a compass, or whether it should resolve them into a strict hierarchy; then find one place later in this book where the conflict was resolved in favour of purity and one where practicality won, and infer the real (unwritten) priority.

---

## 3.9 Summary and cross-references

- **Python's values, readability, explicitness, one obvious way, practicality, were present in the 1989 design and codified in 2004 as the Zen of Python (PEP 20).** The Zen *ships* in the interpreter (`import this`) and codified the values; it did not create them, the dating matters.
- **The values are observable as behaviour, not slogans**: "explicit is better than implicit" is the LEGB name-resolution rule (a name resolves by defined order, not by implicit fallback); "errors should never pass silently" is `1/0` raising and `{}['missing']` raising rather than returning a convenient default.
- **The values constrain the timeline**: every release answers a constraint *without* abandoning the values, so features that would violate them are argued for years or rejected, which is why Python's thirty-five-year history reads as one coherent language rather than an accretion.
- **The values tension with each other** ("one obvious way" vs "practicality beats purity"; "simple" vs the specializing interpreter's complexity), and the Zen is a compass applied case by case, not an algorithm, its power cultural, not mechanical.
- **The book's anti-changelog rule is the values formalised**: a change must answer a problem, mirroring the design process the Zen governs.

**Cross-references.** The ABC and Modula/C lineage → Chapters 1-2. Name resolution → Chapter 75, Deep H. Exceptions loud → Chapters 5, 6, Deep O. String formatting's "one obvious way" → Chapter 12. Optional typing's balance → Deep I. Interpreter complexity beneath a simple surface → Deep H, Deep K. The value boundary in the shared system → Chapter 84, Deep M.
