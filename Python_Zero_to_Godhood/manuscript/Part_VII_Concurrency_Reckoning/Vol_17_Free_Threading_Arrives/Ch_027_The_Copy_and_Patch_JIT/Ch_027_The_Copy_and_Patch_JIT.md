# Chapter 27: The Copy-and-Patch JIT (Python 3.13)

Python 3.13 added a JIT compiler, and the honest headline is the one the marketing did not use: **it is
not, yet, a speedup.** PEP 744, the proposal that introduced it, says so plainly: "the JIT is about as
fast as the existing specializing interpreter on most platforms." That sounds like a failure. It is
not. It is the most interesting thing about this chapter, because it means the JIT was added for
reasons *other* than immediate performance, and understanding those reasons explains where CPython's
speed is going over the next several releases.

The specializing interpreter (Chapter 17) made the interpreter loop smarter about the common case
without generating machine code. The JIT is the next step: it *does* generate machine code, stitching
together the specialized micro-operations of hot code into native instructions. But it does so with a
technique, *copy-and-patch*, chosen for maintainability over peak performance, and its current gains are
roughly neutral. This chapter explains the mechanism, states honestly what it does and does not yet do,
and, like the free-threading chapter, is clear about which claims this book can verify and which it
cites.

> **Verification note.** The JIT is a *build-time option* (`--enable-experimental-jit`), and neither
> verification interpreter on this book's machine was built with it. The detection API (`sys._jit`) is
> verified and shown; the performance framing is *cited to PEP 744*, the primary and deliberately
> cautious source, not measured here, and is tracked in the verification queue. The full treatment,
> alongside the specializing interpreter it builds on, is **Deep J**.

## Section index

- **27.1** From specialization to compilation
- **27.2** Copy-and-patch: how the JIT is built
- **27.3** Detecting the JIT
- **27.4** Why a JIT that is not yet faster (cited)
- **27.5** Edges and failure modes
- **27.6** Connections
- **27.7** Exercises
- **27.8** Summary and cross-references

The listing lives under `code/ch027/` and is re-executed by `make verify` on both interpreters.

---

## 27.1 From specialization to compilation

Chapter 17's specializing interpreter replaces generic opcodes with type-specialized ones at runtime,
backed by inline caches, and stays entirely within the interpreter loop: no machine code is generated,
the loop just dispatches smarter opcodes. That removes interpreter overhead on the fast path, but it
does not remove the interpreter itself: every specialized opcode is still a C function the eval loop
dispatches to, one at a time, with the dispatch cost between each.

A JIT removes that remaining layer. It identifies a hot *trace*, a sequence of specialized
micro-operations that run together, and compiles them into a single block of native machine code with
no per-opcode dispatch between them. The specialization work of Chapter 17 is the *input*: the JIT
compiles the already-specialized micro-ops, so a polymorphic site that never specialized gives the JIT
nothing to compile. The two are layers, not alternatives, the JIT builds on the specializer, which is
why keeping hot code monomorphic (Chapter 17, §17.5) matters even more when the JIT is on.

---

## 27.2 Copy-and-patch: how the JIT is built

The design choice that defines this JIT is *copy-and-patch*, and it is a maintainability decision as
much as a performance one. Writing a traditional optimizing compiler backend by hand, one that emits
machine code for each target architecture, is an enormous, permanent maintenance burden: every change
to the bytecode would require corresponding changes to the code generator for every platform.

Copy-and-patch avoids that. At CPython *build* time, LLVM compiles a small pre-written template of
machine code for each micro-operation (a "stencil"), once, ahead of time. At *runtime*, the JIT does
not invoke a compiler; it copies the relevant stencils into executable memory and *patches* the holes,
the constants, jump targets, and memory addresses, in place. The result is native code produced by
gluing pre-compiled templates, fast to generate (no runtime compilation) and, crucially, *derived
automatically from the same bytecode definitions the rest of the interpreter uses*. PEP 744's own
justification is maintenance: "CPython's maintainers, by merely editing the bytecode definitions, will
also get the JIT backend updated for free, for all JIT-supported platforms, at once." The entire
mechanism is about 900 lines of build-time Python and 500 lines of runtime C. It is a JIT designed to
be *cheap to maintain* first and fast second, on the bet that the speed comes later once the foundation
exists.

---

## 27.3 Detecting the JIT

The JIT is compiled in only when CPython is configured with `--enable-experimental-jit`; 3.14 exposes
`sys._jit` to query it:

```python
# code/ch027/l01_jit_detection.py
import sys
if hasattr(sys, "_jit"):
    print("  sys._jit.is_available():", sys._jit.is_available())
    print("  sys._jit.is_enabled()  :", sys._jit.is_enabled())
```

Verified output (CPython 3.14.6):

```text
--- is the JIT available and enabled on this interpreter? ---
  sys._jit.is_available(): False
  sys._jit.is_enabled()  : False
  built with --enable-experimental-jit: False
```

This is a default build: the JIT was not compiled in, so `is_available()` is `False`. (On 3.13,
`sys._jit` does not exist at all; the API arrived in 3.14, and both are recorded.) A JIT-enabled build,
configured with `--enable-experimental-jit` and toggled at runtime with `PYTHON_JIT=1`, would report
`True`. The distinction between *available* (compiled in) and *enabled* (active this run) is the API's
whole point: the JIT can be built in but turned off, so a distribution can ship it and let users opt in.

---

## 27.4 Why a JIT that is not yet faster (cited)

**This section's performance characterization is cited to PEP 744, not measured on this book's machine
(verification queue item 3).**

PEP 744 is unusually candid: "Currently, the JIT is about as fast as the existing specializing
interpreter on most platforms," and "while the JIT provides significant gains over the existing
micro-op interpreter, it isn't yet a clear win when always enabled." In other words, on the standard
benchmark suite the JIT is roughly *neutral* versus the plain 3.13 interpreter. The transition from
experimental to permanent is gated on a future criterion PEP 744 states as "a meaningful performance
improvement for at least one popular platform (realistically, on the order of 5%)," which it had not yet
met at proposal time.

So why ship it? Three reasons, all from the primary source. First, *maintainability*: copy-and-patch
generates the backend from the bytecode definitions (§27.2), so the JIT does not fork the interpreter's
semantics. Second, *foundation*: a JIT that produces correct native code, even at break-even speed, is
the substrate on which real optimizations, better trace selection, cross-opcode optimization, register
allocation, can be built incrementally. Third, *early exposure*: shipping it experimental lets it be
tested against real code and platforms while it is still cheap to change. This is a bet, made in public,
that the infrastructure is worth building before it pays off, which is exactly why the honest framing
matters: a reader who expects a 3.13 JIT to speed up their code today will be disappointed, and a reader
who understands it as foundation-laying will watch the right thing.

(Secondary coverage often reports larger figures, 10-30%, for specific compute-heavy microbenchmarks.
Those are real for particular workloads but are not the same claim as a net speedup on a broad suite,
which PEP 744 says the JIT does not yet deliver. This book follows the primary source.)

---

## 27.5 Edges and failure modes

**Expecting a speedup today.** §27.4. On a broad suite the JIT is roughly neutral per PEP 744. Enable it
to experiment and to help the project, not for a guaranteed win now.

**Assuming the default build has it.** §27.3. The JIT is a build option and off in most distributions'
default builds; `sys._jit.is_available()` is `False` here. Check before relying on it.

**Confusing the JIT with the specializer.** §27.1. The specializing interpreter (Chapter 17) is always
on and is where 3.11's speedups came from; the JIT is separate, optional, and builds on it. Polymorphic
code that defeats specialization also gives the JIT nothing.

**Reading microbenchmark headlines as suite results.** §27.4. A 30% gain on a tight arithmetic loop is
not a 30% gain on real programs. The primary source's neutral framing is the honest one.

**Citing these numbers as measured.** This chapter's performance claims are cited to PEP 744, not
measured here. Do not present them as this book's measurements.

---

## 27.6 Connections

**Backward.** The specializing interpreter the JIT consumes as input, and the monomorphism that feeds
both, is Chapter 17. The micro-operations the JIT stitches together are the specialized opcodes measured
there. The interpreter loop the JIT partially replaces is Chapter 2.

**Forward.** The full JIT treatment, trace selection, the tier-2 micro-op interpreter, and the
optimizations built on the copy-and-patch foundation, is **Deep J**, alongside `ceval.c`. The
free-threaded build the JIT must eventually coexist with is Chapter 26 and **Deep L**.

**Across books.** The JIT is why the Python glue around a **Book I** C++ kernel may, over coming
releases, need less rewriting-in-C: as the JIT matures, the hot Python dispatch and bookkeeping that
today motivates dropping to C++ may run fast enough in Python that the boundary moves. The JIT does not
change the boundary today (it is neutral), but it is the reason to expect the boundary to shift, which
is a design consideration for where to place the seam. **Deep J** owns the mechanism.

---

## 27.7 Exercises

**1. Detect and toggle.** Run the §27.3 listing. If you can obtain a JIT-enabled build, run it with
`PYTHON_JIT=1` and `PYTHON_JIT=0` and observe `sys._jit.is_enabled()`. Explain the available-versus-
enabled distinction and why a distribution would want both.

**2. Reason about the layering.** Explain, using §27.1, why a polymorphic hot site (Chapter 17) gives the
JIT nothing to compile. What would you change about such code to give both the specializer and the JIT
something to work with?

**3. Read the primary source.** Find PEP 744's statement about current performance and its criterion for
becoming permanent. In two sentences, state what the JIT would have to achieve to graduate from
experimental, and why the project shipped it before then.

**4. Separate the claims.** Find a secondary article claiming a large JIT speedup, identify the exact
workload it measured, and explain why that is or is not the same as PEP 744's "net speedup on a broad
suite" claim. This is the discipline the whole book applies to performance numbers.

**5. The design question.** CPython chose copy-and-patch, a JIT optimized for *maintainability* and
generated from the bytecode definitions, over a hand-written optimizing backend that might be faster
sooner. Argue why. Your answer must address the permanent maintenance cost of a hand-written backend
across platforms, the value of a break-even foundation, and how this choice mirrors the specializing
interpreter's own incremental philosophy (Chapter 17).

---

## 27.8 Summary and cross-references

- Python 3.13 added an **experimental JIT** (PEP 744) that compiles hot traces of specialized micro-ops
  into native code, the next step after the specializing interpreter (Chapter 17), which it builds on
  rather than replaces.
- It uses **copy-and-patch**: LLVM precompiles per-micro-op templates at build time; at runtime the JIT
  copies them into executable memory and patches in constants and addresses, so the backend is generated
  from the bytecode definitions and is cheap to maintain (~900 lines build-time, ~500 runtime).
- **Cited (not measured here):** PEP 744 states the JIT is currently "about as fast as the existing
  specializing interpreter", roughly *neutral*, not yet a clear win. It was shipped for maintainability,
  as a foundation for future optimization, and for early exposure, gated on a future ~5% gain to become
  permanent.
- The JIT is a **build option** (`--enable-experimental-jit`), off in default builds; `sys._jit`
  (3.14+) reports availability and enabled state.

**Cross-references.** The specializing interpreter and monomorphism → Chapter 17. The interpreter loop →
Chapter 2. The full JIT and `ceval.c` treatment → Deep J. The free-threaded build it must coexist with →
Chapter 26 and Deep L. The moving C++ boundary → Deep J and Deep M.
