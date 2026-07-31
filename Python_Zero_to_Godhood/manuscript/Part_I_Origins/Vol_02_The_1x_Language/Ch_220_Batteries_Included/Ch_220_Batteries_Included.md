# Chapter 10: Batteries Included

Volume 2 closes on the decision that shaped Python's *identity* more than any single language feature: the choice to ship a large, useful standard library. The phrase **"batteries included"**, current in the Python community by the late 1990s, names the policy that common tasks, talking to files, the network, JSON, dates, math, hashing, should need no third-party install. A fresh Python could do real work out of the box, and that immediacy drove adoption in a way a small-core language could not.

This was the extensibility decision (Chapter 1) turned into strategy. Because Python was easy to extend, a rich standard library could be *built*, and because it was shipped *with the interpreter*, it was *available* to every user with zero setup. The two properties compound: extensibility made the library possible, and inclusion made it ubiquitous. This chapter surveys the breadth a modern interpreter carries, the direct descendant of the 1.x commitment, and reads the decision's payoff and its cost: a large standard library ages, because it ships with the interpreter and cannot break compatibility, so some batteries corrode as PyPI packages surpass them. The decision was right for its era, and the tension it created is a recurring theme of the timeline that follows.

## Section index

- **10.1** The constraint: ship a big library or a small core
- **10.2** The breadth, and why it mattered
- **10.3** One script, five domains, no third-party code
- **10.4** The stdlib as a museum of solved problems
- **10.5** The cost: a large standard library ages
- **10.6** Edges: the corroding batteries
- **10.7** Connections
- **10.8** Exercises
- **10.9** Summary and cross-references

Listings live under `code/ch220/` and are re-executed by `make verify` on the verification interpreters.

---

## 10.1 The constraint: ship a big library or a small core

Every young language faces one strategic question about its standard library: **ship a big one or a small one?** A small core (C's, early JavaScript's) keeps the language simple and pushes capability to third parties, at the cost of every user needing to assemble a toolchain before doing anything real. A big library (Java's, Python's) makes the language immediately useful, at the cost of size, maintenance burden, and the risk that its included tools age.

Python chose big, and the choice was enabled by Chapter 1's extensibility decision. Because a third party could add a module that behaved exactly like a built-in (a C type is an object, Chapter 1), the standard library could grow to hundreds of modules without changing the language, each module was just more objects in more namespaces (Chapter 2's Modula-inherited module system). And because Python was positioned as a scripting language for system tasks (the Amoeba project, Chapter 1), immediate usefulness *mattered*: a script that needs a `pip install` before it can open a socket is a script that does not get written. So "batteries included" was not a slogan bolted on; it was the extensibility decision applied as strategy, and it defined what Python became, a language you reach for, not one you assemble a toolchain around.

---

## 10.2 The breadth, and why it mattered

```python
# code/ch220/l01_batteries_included.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the stdlib is large, and that is the point ---
  the standard library ships well over 100 top-level modules : True
  the load-bearing core is all present : True
  every one is available with zero installs - 'batteries included'
  means a fresh Python can do real work before any pip runs
```

**The standard library ships well over a hundred top-level modules, and the load-bearing core is always present.**
The exact count drifts by version (each release adds and removes modules, so the listing checks a *threshold* rather than a number that would age), but the shape is constant: a large library, with the core, `json`, `os`, `sys`, `datetime`, `math`, `socket`, `csv`, `sqlite3`, `hashlib`, `asyncio`, `collections`, guaranteed present on every interpreter. This is the breadth "batteries included" promised, and its value is that *availability is certain*: a script can `import json` and know it will be there, on any Python, with no install, no version pinning, no network. Certainty of availability is what makes the standard library the default toolkit, and it is a property only inclusion (not a package index) can provide.

**Zero-install availability is the whole point, and it is an ecosystem property.**
A fresh Python can do real work before any `pip` runs, which matters most exactly where installing is hardest: locked-down environments, air-gapped machines, CI without network, teaching settings, one-off scripts. The standard library is the capability floor no environment can be below, and that floor is what made Python the glue language of system administration, scientific computing's substrate, and web tooling, each could assume the stdlib and build up. The extensibility decision let the library be built; the inclusion decision made it a floor, and the floor is the ecosystem foundation.

---

## 10.3 One script, five domains, no third-party code

```text
--- one script, five domains, no third-party code ---
  json    : {"symbol": "ACME", "qty": 100, "price": 42.5}
  math    : sqrt(2) = 1.414214, pi = 3.141593
  datetime: 2000-09-05 was a Tuesday
  sys     : running CPython 3.x on this interpreter : True
  files, sockets, threads, http, csv, sqlite, hashlib - all in the
  box. this breadth is why Python became a SCRIPTING language you
  reach for, not a language you assemble a toolchain around
```

**One short script touches five domains with nothing installed, which is the promise realised.**
`json` serialises structured data; `math` computes; `datetime` handles dates (and knows `2000-09-05` was a Tuesday, a real calendrical computation); `sys` introspects the runtime. And the comment names what is *also* in the box, files, sockets, threads, HTTP, CSV, SQLite, hashing, each a domain that in a small-core language would require a dependency. This is why Python became the language you *reach for* for a quick task: the task's tools are already present. A developer with an idea and a Python interpreter can talk to the filesystem, the network, a database, and the web without leaving the standard library, and that immediacy is the adoption engine "batteries included" built.

**The domains compose, which multiplies the value.**
Because all these tools ship together and share the object model (Chapter 4), they *compose*: read a CSV (Chapter 119), parse its dates (`datetime`), hash a column (`hashlib`, Chapter 122), serialise the result (`json`, Chapter 42), and stream it over a socket (Chapter 106), all standard library, all interoperating. The composition is Deep V's capstone in miniature (Chapter 132 assembled a whole system from stdlib pieces), and it is only possible because the pieces were designed to ship and work together. A collection of third-party packages does not compose as reliably, versions conflict, APIs differ, and the guaranteed-together property of the standard library is what makes stdlib composition dependable.

---

## 10.4 The stdlib as a museum of solved problems

```text
--- the stdlib is a museum of solved problems ---
  some modules are load-bearing (json, os, datetime, collections);
  some are historical (the removed cgi, the deprecated modules);
  knowing which is which is most of what separates a fluent Python
  engineer from a beginner
```

**The standard library is a museum: some exhibits are load-bearing, some are historical, and knowing which is which is most of Python fluency.**
`json`, `os`, `datetime`, `collections`, `itertools`, these are load-bearing, used daily, actively maintained, the modern quarters (Deep Q, R, S, P own them). Others are historical: `cgi` (removed in 3.13), the many deprecated modules (`imp`, `optparse` superseded by `argparse`), the ones that solved 1990s problems no longer common. A fluent Python engineer knows the difference, reaches for `argparse` not `getopt`, `pathlib` not raw `os.path` string manipulation, `dataclasses` not hand-written `__init__`, and a beginner does not, reaching for whatever a search returns, often the historical exhibit. The standard library rewards knowing its *shape*, which parts are current and which are museum pieces, and that knowledge is a large fraction of what separates fluent from beginning Python.

**This is why the Deep volumes of Part IX exist.**
Deep Q (data, time, functional), Deep R (persistence, OS, IPC, networking), Deep S (runtime, introspection, tooling), and Deep P (text, binary, crypto) are precisely a guided tour of the load-bearing quarters of the museum, teaching which modules are current and how they are used well. The standard library's size is its strength (the breadth) and its challenge (knowing the shape), and the topical Deep volumes address the challenge directly, they are the museum's docents, pointing at the exhibits still worth using.

---

## 10.5 The cost: a large standard library ages

```text
--- the trade: a large stdlib ages ---
  'batteries included' has a cost: the stdlib evolves slowly (it
  ships with the interpreter, so it cannot break compatibility)
  and some batteries corrode - modules that were state-of-the-art
  in 2000 are surpassed by PyPI packages now (requests over
  urllib, though urllib still works)
```

**The decision's cost is that a shipped library evolves slowly and some batteries corrode, and this tension recurs through the timeline.**
Because the standard library ships *with the interpreter*, it inherits the interpreter's compatibility guarantees: a change that breaks stdlib code breaks every program using it, so stdlib modules evolve conservatively, adding rather than changing, keeping old APIs working for decades. This stability is a feature (your `import json` works the same across releases) and a cost: a module that was state-of-the-art in 2000 cannot be *replaced*, only supplemented, so `urllib` (the 1990s HTTP client) still works but `requests` (the PyPI package) surpasses it in ergonomics, and the standard library carries the old design forward while the ecosystem moves on. The batteries corrode, not into non-function, but into being *outclassed* by faster-moving third-party packages.

**The tension is a genuine theme, not a flaw to fix.**
"Batteries included" made Python immediately useful (§10.2) at the cost of making the library slow to modernise (§10.5), and the two are inseparable: inclusion *is* the compatibility guarantee that *is* the slow evolution. The timeline that follows is full of this tension, PEP 594 removed "dead batteries" (obsolete modules) from 3.11-3.13; the async ecosystem grew in the stdlib (`asyncio`) *and* in third-party frameworks that iterate faster; packaging (Deep N) itself moved from the stdlib's `distutils` (removed in 3.12) to third-party build backends. The decision was right for its era, when a big library drove adoption, and the tension it created, stability versus modernity, is one the timeline manages release by release rather than resolves.

---

## 10.6 Edges: the corroding batteries

**"Dead batteries" were removed, finally, in 3.11-3.13.**
PEP 594 identified standard-library modules that were obsolete, unmaintained, or superseded (`aifc`, `cgi`, `telnetlib`, ~20 others) and removed them across 3.11-3.13, the first large stdlib *removal*, acknowledging that "included forever" was itself a cost. The removals are a course correction: inclusion was strategy in the 1.x era, and pruning is maintenance in the modern one.

**`urllib` works but `requests` is the ecosystem default.**
The clearest live example: `urllib.request` can fetch a URL, but nearly every real program uses the third-party `requests` (or `httpx`) for its far better ergonomics. The stdlib battery works; it is simply outclassed, and the standard advice, "use `requests`", is an admission that a shipped module can be surpassed without being removed. Deep V's HTTP chapters (125-127) teach the *protocol* from the stdlib up precisely because the stdlib's low-level tools remain the right teaching substrate even when the ecosystem's high-level tools are third-party.

**`distutils` and `asyncio` show both directions.**
`distutils` (the original packaging tool) was *removed* (3.12) in favour of third-party build backends (Deep N), the stdlib ceding a domain that moved too fast for it. `asyncio` (Deep J) was *added* to the stdlib and remains central, even as third-party frameworks (Starlette, FastAPI) build faster-moving layers on top. The standard library's boundary, what belongs in it versus in PyPI, is renegotiated per domain, and the two examples show it moving both ways.

**And the beginner trap is reaching for the museum piece.**
A search for "Python parse command line" may surface `getopt` (the historical exhibit) before `argparse` (the current one); "Python HTTP" may surface `urllib` before `requests`. The standard library's size means it contains obsolete answers alongside current ones, and a beginner cannot tell them apart, which is the "knowing the shape" challenge (§10.4) as a concrete hazard. Fluency is partly immunity to the museum piece.

---

## 10.7 Connections

**Backward.**
The extensibility decision that made the library buildable is Chapter 1; the module system that holds it is Chapter 2; the object model that lets its pieces compose is Chapter 4; the values that shaped which modules were "obvious" are Chapter 3.

**Forward.**
The load-bearing quarters of the standard library are Deep Q (Chapters 32-39), Deep R (40-48), Deep S (49-55), and Deep P (Chapters 117-124); packaging's move from stdlib `distutils` to third-party backends is Deep N; the composition of stdlib pieces into a whole system is Chapter 132 (Deep V's capstone); the async battery is Deep J.

**Across books.**
"Batteries included" is Python's strategy; **Book I**'s C++ took the opposite path historically (a small standard library, capability in third-party libraries and, recently, a slowly growing STL), which is why C++ programs assemble a toolchain where Python programs assume the stdlib. The shared trading system uses Python's included batteries for its glue and analytics (json, datetime, sqlite, asyncio) and C++'s assembled toolchain for its engine, the two strategies meeting at the boundary (Deep M), each right for its tier.

---

## 10.8 Exercises

**1. Survey the museum.** List ten standard-library modules; for each, judge whether it is load-bearing or historical, and name the modern alternative (stdlib or PyPI) if it is historical. Check your judgements against the Deep Q/R/S/P chapters.

**2. Compose five batteries.** Write a script that reads a CSV, parses dates, hashes a field, serialises to JSON, and writes the result, using only the standard library. Note where the pieces compose cleanly (shared object model) and where they do not.

**3. Feel the zero-install floor.** Take a real task you would normally solve with a PyPI package and solve it with the standard library instead; measure the ergonomics gap. This is the "corroded battery" experience firsthand.

**4. Trace a removal.** Pick a module removed by PEP 594 (`cgi`, `telnetlib`); find what replaced it and why it was removed. Explain what "dead battery" means and why removal took until 3.11-3.13.

**5. The design question.** "Batteries included" made Python immediately useful but slow to modernise, and the tension is unresolvable (inclusion *is* the stability that *is* the slow evolution). Argue where a modern language should draw its stdlib boundary, big for immediate usefulness, small for fast evolution, and use Python's `urllib`-vs-`requests` and `distutils`-removed examples to locate the boundary Python is converging on now.

---

## 10.9 Summary and cross-references

- **"Batteries included" (a late-1990s community phrase) named Python's decision to ship a large standard library**, so common tasks need no install, the extensibility decision (Chapter 1) turned into strategy: extensibility made the library buildable, inclusion made it a guaranteed floor.
- **The breadth is the point**: well over a hundred modules with a load-bearing core (`json`, `os`, `datetime`, `socket`, `sqlite3`, `asyncio`) present on every interpreter, so a fresh Python does real work with zero installs, and the pieces *compose* (shared object model, Chapter 4).
- **The standard library is a museum**: load-bearing exhibits and historical ones, and knowing which is which is most of Python fluency, the reason Deep Q/R/S/P exist as guided tours of the current quarters.
- **The cost is aging**: a shipped library evolves slowly (it cannot break compatibility), so batteries corrode (`urllib` outclassed by `requests`), "dead batteries" were finally removed (PEP 594, 3.11-3.13), and the stdlib boundary is renegotiated per domain (`distutils` out, `asyncio` in).
- **The tension is a theme, not a flaw**: inclusion *is* the stability *is* the slow evolution, and the timeline manages it release by release.

**Cross-references.** Extensibility → Chapter 1. The module system → Chapter 2. The object model → Chapter 4. The values → Chapter 3. The load-bearing stdlib → Deep Q, R, S, P. Packaging's evolution → Deep N. The stdlib-composed system → Chapter 132. asyncio → Deep J. The C++ toolchain boundary → Deep M.
