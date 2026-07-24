# Chapter 1: The Inheritance from ABC

Python did not begin as a good idea. It began as a fix-list for a language its author loved and had
concluded was a failure.

That language was ABC, and Guido van Rossum had spent much of the 1980s helping build it at CWI in
Amsterdam. When he started Python over the Christmas break of 1989, he was not designing from a
blank sheet. He was carrying forward everything ABC got right, indentation, a small set of powerful
built-in types, a focus on readability, and deliberately reversing the specific decisions that, in
his own words, kept ABC from being used. Almost every characteristic feature of Python is on one
side or the other of that ledger. This chapter is the ledger.

**A note on this chapter's evidence.** The historical claims here are sourced to Guido's own written
accounts, cited inline, because the interpreters of that era are not buildable on current hardware
and the record is the only primary source available. Where this chapter shows running code, it
demonstrates the *modern consequence* of an early decision, on the verification interpreters, and
says so. It never regenerates 1991 output on a 2025 interpreter and pretends otherwise.

## Section index

- **1.1** The problem: a beautiful language nobody could use
- **1.2** The model: keep the ergonomics, fix the boundaries
- **1.3** Mechanism I: indentation as a token, not a convention
- **1.4** Mechanism II: extensibility, the decision that mattered most
- **1.5** What the timeline inherited
- **1.6** The dates, as far as they can be verified
- **1.7** Edges: what Python did *not* take from ABC
- **1.8** Connections
- **1.9** Exercises
- **1.10** Summary and cross-references

---

## 1.1 The problem: a beautiful language nobody could use

ABC was designed to teach programming to people who were not programmers: scientists, linguists,
students. By the accounts of the people who used it, it was genuinely good at that. It had a clean
syntax, a small set of well-chosen data types, and no boilerplate. It was also, by 1989, going
nowhere.

Guido's diagnosis was specific, and it was not about the syntax. In his telling, ABC had two flaws
that were fatal in practice rather than in theory. The first was that **it could not talk to the
outside world**: "There was no way to redirect IO to or from a file. They literally didn't have any
other IO available," using persistent global variables where other languages used files (van Rossum,
*The Making of Python*, artima.com). A language that cannot open a file cannot be used for the system
scripting that was the daily work at CWI.

The second flaw was deeper and is the one that shaped Python most: **ABC could not be extended.** Its
parser knew about its built-in types directly, and there was no notion of a standard library that a
third party could add to. If ABC did not already do what you needed, you could not teach it to; you
had to change the language itself. A language that only its authors can grow is a language with a
ceiling.

Guido had a second problem, a concrete one. He had moved to the Amoeba distributed operating system
project at CWI, and the team needed a scripting language. His account is unsentimental about the
motivation: "My original motivation for creating Python was the perceived need for a higher level
language in the Amoeba project. I realized that the development of system administration utilities in
C was taking too long" (van Rossum, *The History of Python*, python-history.blogspot.com). C was too
slow to write; ABC could not do the job at all. The gap between them was the opening.

---

## 1.2 The model: keep the ergonomics, fix the boundaries

The design that came out of that Christmas break is best understood as a single strategy: **take
ABC's ergonomics and remove its walls.**

Guido stated the goal as borrowing "everything I liked from ABC while at the same time fixing all
its problems (as I perceived them)" (*The History of Python*). The things he liked were surface-level
in the best sense: indentation for grouping, a handful of high-level built-in types, an insistence
on readability. The problems were all at the boundaries, where the language met files, met C, met
code its authors had never seen.

So the model of early Python is two commitments held at once:

- **Inward, keep ABC's clarity.** Indentation, not braces. A small set of powerful types, `list`,
  `dict`, `str`, rather than a sprawl. Statements that read like the thing they do.
- **Outward, open every wall ABC had closed.** Real file I/O. A module system, borrowed from
  Modula, so the language could be grown in pieces. And above all, a way for third parties to add
  new types that behaved exactly like the built-in ones.

The rest of this book is, in a sense, the working-out of the second commitment across thirty-five
years. But it starts here, and the two mechanisms below are where the strategy became code.

---

## 1.3 Mechanism I: indentation as a token, not a convention

Every language that uses indentation for grouping claims it improves readability. Python's claim is
stronger and more interesting: in Python, indentation is not a style enforced by a linter on top of
the real syntax. It *is* the syntax. The lexer emits indentation as tokens, and the grammar consumes
those tokens exactly as C's grammar consumes `{` and `}`.

You can see the tokens directly:

```python
# code/ch020/l01_indentation_is_syntax.py
import io, tokenize
SOURCE = "def f(x):\n    if x:\n        return 1\n    return 0\n"
for tok in tokenize.generate_tokens(io.StringIO(SOURCE).readline):
    ...
```

Verified output (CPython 3.13.5):

```text
--- what the lexer emits ---
  NAME     'def'
  NAME     'f'
  OP       '('
  NAME     'x'
  OP       ')'
  OP       ':'
  NEWLINE  '\\n'
  INDENT   '    '
  NAME     'if'
  NAME     'x'
  OP       ':'
  NEWLINE  '\\n'
  INDENT   '        '
  NAME     'return'
  NUMBER   '1'
  NEWLINE  '\\n'
  DEDENT   ''
  NAME     'return'
  NUMBER   '0'
  NEWLINE  '\\n'
  DEDENT   ''
```

`INDENT` and `DEDENT` are tokens in the stream, sitting between the `NAME`s and `OP`s like any other
token. This is the whole trick, and it is why Python needs no block delimiters: the token stream
already carries the block structure, because the lexer put it there.

**The senior-engineer contrast.** In C, C++, Java, or Rust, indentation is invisible to the compiler.
You can format a function on one line or across fifty and the parse is identical, because `{` and `}`
carry the structure and whitespace is discarded. Python moves that job from a pair of punctuation
marks to the lexer's column tracking. The consequence a systems programmer should notice is that
this costs nothing at runtime: the `DEDENT` tokens are consumed when the source is compiled to
bytecode, and the code object that results is structurally identical to what a brace language would
produce.

Because the structure is tokenised, a malformed indent is a compile-time error, not a runtime
surprise:

```text
--- INDENT and DEDENT are structural, so a bad indent is a SyntaxError ---
  inconsistent dedent -> IndentationError: unindent does not match any outer indentation level
  unexpected indent   -> IndentationError: unexpected indent
```

`IndentationError` is a subclass of `SyntaxError`. Bad indentation fails the same way a missing
parenthesis does: the source never becomes a code object. This is the ABC inheritance made rigorous.
ABC used indentation; Python made indentation part of the formal grammar, and cross-references to the
lexer and the parser that produce these tokens are the subject of Chapter 2 (Python 1.x) and the
lexical-analysis chapter of the language-reference volume.

Guido's reason for the choice, incidentally, was partly aesthetic revulsion at the alternative ABC
offered. ABC used uppercase keywords, and he "never got comfortable with the uppercase, neither
reading nor typing it" (*The Making of Python*). Indentation for grouping and lowercase keywords are
the same decision seen from two sides: make the common case quiet.

---

## 1.4 Mechanism II: extensibility, the decision that mattered most

If indentation is the inheritance people notice, extensibility is the one that made Python survive.
Guido calls it directly: his "most innovative contribution to Python's success was making it easy to
extend" (*The Making of Python*). This is the reversal of ABC's fatal second flaw, and it is worth
being precise about what it means, because it is subtler than "you can write libraries."

The commitment is this: **a type added by a third party is indistinguishable, to the rest of the
language, from a built-in type.** There is no privileged inner circle of types the interpreter knows
about and an outer class of user types that behave differently. `list` and a class you define an hour
from now go through the same machinery.

That property is visible in modern CPython, which is the direct descendant of the 1991 design:

```python
# code/ch020/l02_extensibility.py
import builtins, types

class Ledger(dict):                 # subclass a built-in type
    def __setitem__(self, key, value):
        self.seen.append(key)
        super().__setitem__(key, value)

Made = type("Made", (object,), {"kind": "runtime"})   # build a type at runtime
```

Verified output (CPython 3.13.5):

```text
--- built-in types are ordinary objects in an ordinary module ---
  builtins is a module: True
  'list' is an attribute of it: True
  and it is a plain dict: dict
--- so a built-in type can be subclassed like any other ---
  Ledger(dict) instance: {'a': 1, 'b': 2} seen: ['a', 'b']
  still a dict: True
--- and a type can be built at runtime, with no compiler involvement ---
  type() built: Made | kind: runtime | speak(): hello
```

`builtins` is a module, and `list` is one of its attributes. Not a keyword, not a compiler intrinsic:
an attribute, of a namespace, that is a plain dictionary. That is the architectural decision. Because
`list` is just an object in a namespace, it can be subclassed, shadowed, or inspected like anything
else, and a new type can be constructed at runtime by calling `type` with no compiler involved at all.

The payoff, and the thing ABC could not do:

```text
--- the same door the C-API uses ---
  a type written in C is indistinguishable from one written in Python:
    list     __module__=builtins   written in C
    Ledger   __module__=__main__   written in Python
    Made     __module__=__main__   written in Python
  both are PyTypeObjects; the caller cannot tell.
```

`list` is written in C. `Ledger` is written in Python. `Made` was assembled at runtime. To every
other part of the interpreter they are the same kind of thing, a `PyTypeObject`, and no caller can
tell them apart. This is the exact capability ABC lacked, and it is why Python's standard library
could grow without the language itself changing, and why the entire scientific-computing and
web-development ecosystems could be bolted on decades later without Guido's involvement. A language
whose types are ordinary objects is a language other people can extend. That door, opened at the
start, is the one that everything else in this book walks through, and its full mechanism, the
`PyTypeObject` and the C-API that populates it, is **Deep A** and **Deep M**.

---

## 1.5 What the timeline inherited

Reading the ledger forward, the strategy of 1.2 seeds threads that this book tracks for thirty-five
years:

- **Indentation as grammar** (§1.3) is stable to this day and was reaffirmed, not revised, when the
  parser was replaced wholesale by PEG in Python 3.9 (Chapter 14). The tokeniser still emits `INDENT`
  and `DEDENT`; only the grammar consuming them changed.
- **Everything is an object** is the deep form of the extensibility decision (§1.4). It is the
  subject of **Deep A**, and it is why Python has both the uniformity that makes it pleasant and the
  per-object overhead measured there.
- **The module system** borrowed from Modula becomes the import machinery of **Deep G**, and its
  namespace-package extension is one of the headline features of Python 3.3 (Chapter 9).
- **File I/O and the outside world**, ABC's first fatal flaw, becomes the text/bytes model of Python
  3.0 (Chapter 7) and the entire systems-programming half of the standard library.

The through-line for this opening volume is the one this chapter states: **Python is what you get when
you keep a teaching language's clarity and systematically open every boundary it had closed.**
Everything in Volume 1 is a consequence of that sentence.

---

## 1.6 The dates, as far as they can be verified

History chapters are where a technical book is most tempted to fabricate, because dates are easy to
assert and hard to check. Here is what the primary record supports, with its sources, and what it
does not.

- Guido began Python "in late December 1989, and had a working version in the first months of 1990"
  (*The History of Python*, python-history.blogspot.com). The "Christmas 1989" framing is his own.
- The first public release was **version 0.9.0**, posted to the `alt.sources` Usenet newsgroup on
  **20 February 1991**, distributed as "21 uuencoded parts that had to be joined together and
  uudecoded to form a compressed tar file," under a licence based on MIT's X11 licence (*The History
  of Python*). This is Guido's own statement and is the authority this book uses.
- 0.9.0 already contained classes with inheritance, exception handling, functions, modules, and the
  core types `list`, `dict`, and `str`. This much is consistent across every account, though the
  precise feature list of 0.9.0 specifically, as opposed to the 0.9.x line, is not something Guido
  itemises, and this book does not claim more than the record supports.

**One conflict worth flagging honestly.** Some secondary sources state that the code posted to
`alt.sources` was version 0.9.1, not 0.9.0. Guido's own history blog says 0.9.0. This book follows
the primary source, and notes the discrepancy rather than hiding it, because a reader who finds the
0.9.1 claim elsewhere deserves to know it was considered. The likely explanation is that 0.9.1
followed within days, but "likely" is not "verified," and it is labelled as such.

The 1.x releases that follow, 1.0 in January 1994, the CWI-era versions through 1.2, and the move to
CNRI, are Chapter 2's subject and are dated there against the same standard.

---

## 1.7 Edges: what Python did *not* take from ABC

The ledger has a debit side, and it is as informative as the credit side.

**ABC's uppercase keywords: rejected** (§1.3). Aesthetic, but Guido names it as a real motivation, and
it points at a design value, quietness in the common case, that recurs throughout Python's history.

**ABC's monolithic design: rejected.** ABC was one integrated environment. Python was a language plus
an interpreter you could embed and extend, which is the §1.4 decision restated as architecture.

**ABC's numeric-type sophistication: partly kept, partly deferred.** ABC had arbitrary-precision
numbers, and Python kept unbounded integers (the reason a Python `int` is not a machine word, **Deep
A**). But Python did not inherit ABC's full numeric tower wholesale; the rational and decimal types
arrived later and as library modules, which is the extensibility decision paying off.

**ABC's persistent global state: firmly rejected**, because it was the mechanism behind the first
fatal flaw. Python's answer, real files and real I/O, is the thing that made it usable at all, and it
is the reason a language designed for a distributed-OS project could become a general-purpose one.

The lesson for a reader who cares about design: **the decisions that made Python succeed were mostly
reversals, not inventions.** Guido's genius in 1989 was less in what he thought of than in what he
correctly identified as ABC's mistakes and refused to repeat.

---

## 1.8 Connections

**Forward.** The lexer and parser that turn indentation into tokens are Chapter 2's executable
pipeline, and the PEG rewrite that replaced the original parser without touching the tokeniser is
Chapter 14 (Python 3.9). "Everything is an object," the deep form of §1.4, is **Deep A**. The module
system is **Deep G**. ABC's I/O flaw, fixed, becomes the text/bytes model of Chapter 7 (Python 3.0).

**Across books.** The extensibility decision of §1.4, that a C type and a Python type are the same
kind of object, is the foundation the entire **Book I** boundary rests on. A C++ class exposed to
Python through `nanobind` becomes a `PyTypeObject` indistinguishable from a built-in, which is only
possible because Guido decided in 1989 that there would be no privileged inner circle of types. The
order-book example that runs through all three books relies on exactly this: its C++ matching engine
appears to Python code as an ordinary object. **Deep M** owns that boundary.

---

## 1.9 Exercises

**1. Read the tokens yourself.** Take a function with a nested `if`/`else` and a `for` loop and run it
through `tokenize.generate_tokens` as in Listing 20.1. Predict, before running, exactly how many
`INDENT` and `DEDENT` tokens it will produce, and where. The count is not obvious for `else`; explain
why.

**2. The extensibility test.** Write a class that subclasses `list` and forbids duplicates on
`append`. Then, without changing that class, demonstrate that ordinary code which expects a `list`
accepts your instance without knowing it is special. What property of §1.4 makes this work, and what
is the one method you must be careful *not* to break for it to keep working?

**3. Find the flaw in a modern setting.** ABC could not open a file. Construct the smallest modern
Python program that would have been impossible in ABC as described in §1.1, and explain which single
language capability each line depends on. The point is to feel the size of the gap Guido was closing.

**4. The historian's exercise.** §1.6 flags a 0.9.0-versus-0.9.1 conflict between primary and
secondary sources. Find one primary source (Guido's writing, an archived `alt.sources` posting, or the
preserved 0.9.x source tree) and one secondary source that disagree on *any* fact about early Python,
and write two sentences on which you would trust and why. This is the discipline the rest of this book
applies to every claim.

**5. The design question.** Guido identified ABC's inextensibility as fatal and made the opposite
choice. But "any third party can add a type that behaves like a built-in" is also the source of some
of Python's hardest problems: monkeypatching, the difficulty of optimising a language where `list`
might have been replaced, and the specialising interpreter's need to guard every assumption (Chapter
15). Argue whether the extensibility decision was worth its cost, and identify one specific place
later in this book where the interpreter pays for it at runtime.

---

## 1.10 Summary and cross-references

- Python began as Guido van Rossum's **fix-list for ABC**, a language he admired and judged a
  failure, started over the Christmas break of **1989** and first released as **version 0.9.0** to
  `alt.sources` on **20 February 1991**.
- ABC's two fatal flaws in Guido's account were **no file I/O** and **no extensibility**. Python's
  design is the systematic reversal of both while keeping ABC's clarity: indentation, a small set of
  powerful types, readability.
- **Indentation is a token, not a convention.** The lexer emits `INDENT`/`DEDENT`, the grammar
  consumes them like braces, and bad indentation is a compile-time `IndentationError`. It costs
  nothing at runtime.
- **Extensibility is the decision that mattered most.** Built-in types are ordinary objects in
  ordinary namespaces, and a type written in C, in Python, or at runtime is the same `PyTypeObject`
  to every caller. This is why the standard library and the whole ecosystem could grow without the
  language changing.
- The historical claims here are **sourced to Guido's own accounts** and one primary-versus-secondary
  conflict (0.9.0 vs 0.9.1) is flagged rather than smoothed.

**Cross-references.** The executable pipeline that tokenises and parses this syntax → Chapter 2. The
PEG parser that replaced the original → Chapter 14. Everything-is-an-object in depth → Deep A. The
import system → Deep G. Text, bytes, and the I/O that ABC lacked → Chapter 7. The C-API boundary that
extensibility makes possible → Deep M.

**Sources.** Guido van Rossum, *The Making of Python* (interview, artima.com); Guido van Rossum, *The
History of Python: Personal History, part 1, CWI* (python-history.blogspot.com); *History of Python*
(en.wikipedia.org), used only for cross-checking secondary claims, never as sole authority.
