# Chapter 14: The Walrus Operator and Positional-Only Parameters (Python 3.8)

Here is a line that does its expensive work twice:

```python
if pattern.match(text):
    group = pattern.match(text).group(1)      # the match is computed a second time
```

The regex match runs once to decide the branch and again to extract the group, and nothing warns you.
The 3.8 fix is one operator, `:=`, which binds the result of the first match to a name that the body
can reuse:

```python
if (m := pattern.match(text)):
    group = m.group(1)                         # the match is computed once
```

Measured on a small regex, computing once instead of twice is about **1.7x faster** for that step. The
walrus operator (PEP 572) is one of two 3.8 features that look small and are quietly significant. It
broke Python's long-standing wall between statements and expressions, letting you bind a name *inside*
an expression. The other, **positional-only parameters** `/` (PEP 570), gave function authors the
control over the positional/keyword boundary that C builtins always had. Both are about precision; and
one of them comes with a performance justification that, as this chapter measures, does not hold.

## Section index

- **14.1** The assignment expression `:=` (PEP 572)
- **14.2** Positional-only parameters `/` (PEP 570)
- **14.3** Measurement: the walrus saves work, `/` does not save call time
- **14.4** Edges and failure modes
- **14.5** Connections
- **14.6** Exercises
- **14.7** Summary and cross-references

Listings live under `code/ch014/` and are re-executed by `make verify` on both interpreters.

---

## 14.1 The assignment expression `:=` (PEP 572)

**Why this exists.** Python deliberately separated *statements* (assignment `x = 1`, which yields no
value) from *expressions* (which do). That cleanliness forced two common patterns to be clumsy:
computing a value to *test* and then *reuse* required either a pre-loop assignment plus a `while
True`/`break`, or computing the value twice, as in the chapter opening. The walrus adds an assignment
expression: it binds a name *and* evaluates to the bound value, without abolishing the
statement/expression distinction (it is a separate operator, not a redefinition of `=`). At the AST
level a normal assignment is an `Assign` statement; `x := 1` is a `NamedExpr` expression, and the
bytecode duplicates the value on the stack (`COPY` in 3.11+, `DUP_TOP` before) so the binding consumes
one copy and the surrounding expression gets the other.

```python
# code/ch014/l01_walrus.py
while (line := stream.readline()):        # read-until-sentinel, no while True / break
    lines.append(line.strip())

def parent_func(data):
    result = [y for x in data if (y := x * 2) > 2]   # compute once, test and reuse
    return result, y                                  # y survives in the surrounding scope
```

Verified output (CPython 3.13.5):

```text
--- := duplicates the value on the stack (COPY in 3.11+) ---
  has COPY (dup for the expression value): True
  has STORE_NAME (the binding)           : True
--- the two canonical uses ---
  loop-until-empty: ['aaa', 'bbb', 'ccc']
  filter-and-reuse: ([4, 6], 6)
```

**The scoping subtlety.** Inside a comprehension, a walrus target *binds in the enclosing scope, not
the comprehension's*, which is why `y` is still visible (and equals the last value, `6`) after
`parent_func`'s comprehension finishes. This hoisting is deliberate, for "keep the last or maximal
value" patterns, and it survived PEP 709 comprehension inlining (Chapter 3):

```text
--- the scoping subtlety: a walrus in a comprehension binds OUTWARD ---
  nested code objects in parent_func: [] (empty => PEP 709 inlined)
  yet y leaked to the enclosing scope: that hoisting survived inlining.
```

The comprehension is inlined (no nested code object), yet the walrus still targets the surrounding
scope. **The compiler forbids the dangerous cases** to keep this readable:

```text
--- the compiler forbids the dangerous cases ---
  rebinding the loop var -> assignment expression cannot rebind comprehension iteration variable 'i'
```

Rebinding a comprehension's own iteration variable is a `SyntaxError`, as is a walrus at the top level
of an expression statement (`x := 1` must be parenthesized) or inside a class-body comprehension (class
namespaces are not function frames and cannot carry the closure cell the hoisting needs). The
guideline: `:=` exists to remove redundancy, not to win golf. If it makes a line harder to scan, use a
plain assignment.

---

## 14.2 Positional-only parameters `/` (PEP 570)

**Why this exists.** Before 3.8, pure-Python functions could not express what every C builtin already
did: "these parameters may be passed *only positionally*." That mattered for two reasons. **API
stability**: if a parameter can be passed by keyword, its *name* becomes part of your public contract
and you can never rename it without breaking callers. **`**kwargs` safety**: a function like
`dict(**kwargs)` could not accept a key literally named as one of its parameters without a collision.
The `/` marker fixes both, making every parameter before it positional-only.

```python
# code/ch014/l02_positional_only.py
def func(a, b, /, c, d, *, e, f):
    return (a, b, c, d, e, f)
```

Verified output (CPython 3.13.5):

```text
--- the boundaries are encoded in the code object ---
  co_posonlyargcount: 2 (a, b before /)
  co_argcount       : 4 (a, b, c, d: all positionals)
  co_kwonlyargcount : 2 (e, f after *)
--- calling within the contract works ---
  func(1, 2, 3, 4, e=5, f=6): (1, 2, 3, 4, 5, 6)
--- passing a positional-only param by keyword is a precise TypeError ---
  func(a=1, b=2, ...) -> func() got some positional-only arguments passed as keyword arguments: 'a, b'
```

The boundaries are encoded in the code object: `a, b` are positional-only (`co_posonlyargcount == 2`);
`c, d` are positional-or-keyword (so `co_argcount == 4` counts all four positionals); `e, f` are
keyword-only after the `*`. Together `/` and `*` give an author full control over how each parameter
may be supplied, and misuse raises a precise `TypeError` naming the offending parameters.

Mark a parameter positional-only when its name is an implementation detail you want freedom to rename,
when you accept arbitrary `**kwargs` that might collide with a parameter name, or when matching a
builtin's signature. Do not over-apply it to ordinary application code where keyword arguments aid
readability. And, as §14.3 shows, do not reach for it expecting a speedup.

---

## 14.3 Measurement: the walrus saves work, `/` does not save call time

Two claims meet here. The walrus's value is de-duplication, which is measurable. And positional-only
parameters come with a common performance justification, that they enable "index-based vectorcall
argument copying" that "trims call overhead," which is the kind of claim this book tests rather than
repeats.

**Methodology.** `code/ch014/bench_walrus_posonly.py`, through `_harness/bench.py`. `min` over 15
batches; within one interpreter; CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**The walrus, computing a regex match once versus twice:**

| form | ratio |
|---|---|
| compute the match twice | 1.00x |
| walrus, compute once | **0.58x** (about 1.7x faster) |

For a value that is both tested and used, the walrus computes it once and the naive form computes it
twice, so the walrus saves the whole second computation, here about 42%. The saving scales with how
expensive the computation is: for a regex match it is substantial, for a cheap integer it is
negligible. The walrus is a de-duplication tool, and its payoff is exactly the cost of the duplicated
work it removes.

**Positional-only, called positionally:**

| definition | ratio |
|---|---|
| positional-or-keyword `def` | 1.00x |
| positional-only `def` | **1.00x** |

**Calling a positional-only function with positional arguments is the same speed as calling an ordinary
one.** There is no measurable call-overhead benefit, because a positional call already takes the fast
path regardless of the marker. The vectorcall optimization the performance folklore points at is real
only relative to a *keyword* call, and you would not pass arguments by keyword to a hot function in the
first place. So the honest justification for positional-only parameters is API stability and `**kwargs`
safety, not call speed. Choose it to protect a parameter name from becoming part of your contract, not
to make calls faster; the measurement says the latter benefit is not there.

---

## 14.4 Edges and failure modes

**`:=` for density instead of de-duplication.** §14.1. Use it to avoid evaluating something twice or to
fold a sentinel-read loop; do not chain several walruses into one unreadable expression.

**The comprehension hoist.** §14.1. A walrus in a comprehension leaks its target to the enclosing
scope, useful for "keep the last value," surprising if you expected comprehension-local scoping. Name
such targets clearly.

**Walrus in the forbidden positions.** §14.1. Rebinding the loop variable, an unparenthesized top-level
`:=`, or a class-body comprehension is a `SyntaxError`. The compiler is protecting readability.

**Positional-only for speed.** §14.3. It does not speed up positional calls. Use it for API stability
and `**kwargs` safety.

**Over-marking ordinary code.** Reaching for `/` and `*` reflexively in application code costs
readability; keyword arguments are usually clearer there. Reserve the markers for encoding a real
calling contract in a library.

---

## 14.5 Connections

**Backward.** The comprehension scope the walrus hoists out of, and the PEP 709 inlining it survives,
are Chapter 3; the closures and cells that carry the hoisted binding are Chapters 2 and 3. The code
object fields (`co_posonlyargcount`) that record the parameter boundaries are Chapter 2.

**Forward.** The PEG parser that made richer grammar like the walrus practical to add is Chapter 15
(the next chapter, PEP 617). The vectorcall calling convention and argument binding internals are
**Deep J**. Keyword-only parameters and full signature design are **Deep I**.

**Across books.** Positional-only parameters are how a Python wrapper around a **Book I** C++ function
presents a stable signature: the wrapper marks its forwarding parameters positional-only so their names
(often just `arg0`, `arg1` from the binding generator) never become part of the contract, leaving the
C++ author free to rename them. `nanobind`-generated bindings use positional-only signatures for exactly
this reason. **Deep M** owns that boundary.

---

## 14.6 Exercises

**1. Measure your own de-duplication.** Reproduce §14.3's walrus benchmark with three computations of
increasing cost: an integer add, a regex match, and a function call that sleeps a microsecond. Predict
the walrus's advantage for each before measuring, and explain why it tracks the cost of the duplicated
work.

**2. Leak a value on purpose.** Use a walrus in a comprehension to capture the maximum value seen while
filtering, and read it after the comprehension. Then explain, using §14.1 and Chapter 3, why the value
survives even though the comprehension is inlined and has no frame of its own.

**3. Break a rename.** Write a library function with a positional-or-keyword parameter, have a "caller"
pass it by keyword, then rename the parameter and show the caller breaks. Add `/` to make the parameter
positional-only and show the rename is now safe. This is the API-stability argument from §14.2 made
concrete.

**4. Disprove the speed claim yourself.** Reproduce §14.3's positional-only benchmark and confirm no
call-speed difference. Then construct the one case where positional-only *does* differ (a keyword call),
and explain why that case is irrelevant to a hot path.

**5. The design question.** The walrus operator was one of the most contested additions in Python's
history, contributing to Guido van Rossum stepping down as BDFL. Argue both sides: what it buys (§14.3's
de-duplication, sentinel loops) against the cost of blurring the statement/expression line that Python
had kept clean for decades. Your answer must address why the compiler restricts it so heavily (§14.1)
and whether those restrictions vindicate or undermine the objection.

---

## 14.7 Summary and cross-references

- The **walrus operator** `:=` (PEP 572) is an **assignment expression**: it binds a name and evaluates
  to the value (bytecode duplicates via `COPY`). In comprehensions it **binds in the enclosing scope**
  (hoisting survives PEP 709 inlining); rebinding the loop variable or using it in a class-body
  comprehension is a `SyntaxError`.
- **Positional-only parameters** `/` (PEP 570) make pre-`/` parameters un-passable by keyword,
  protecting parameter *names* from becoming API and avoiding `**kwargs` collisions.
  `co_posonlyargcount` records the count; misuse raises a precise `TypeError`.
- **Measured:** the walrus saves the cost of a duplicated computation (about **1.7x** for a regex match
  tested and reused); positional-only parameters give **no** call-speed benefit for positional calls
  (1.00x), so choose them for API stability, not speed.

**Cross-references.** Comprehension scope and PEP 709 inlining → Chapter 3. Closures and cells → Chapters
2 and 3. The PEG parser → Chapter 15. The vectorcall convention → Deep J. Signature design and the type
system → Deep I. The C++ binding boundary → Deep M.
