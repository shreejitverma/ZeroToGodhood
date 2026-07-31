# Chapter 14: The Licence Rupture

This volume is named "The Licence Rupture and 2.0" because between Python 1.5.2 and 2.1, the language's *legal foundation*, its licence and its ownership, nearly fractured, and the crisis was as existential as any technical one. A programming language is not only code; it is a legal artifact that enterprises, Linux distributions, and other free-software projects must be able to *use*, which means its licence must be stable, clear, and compatible with the licences of the software it combines with. For a stretch around 2000, Python's was none of those.

The story is one of institutional drift. Guido van Rossum developed Python at CWI in Amsterdam (1989-1995), moved to **CNRI** in the United States (1995), which released Python 1.6 under a licence whose choice-of-law clause made it **GPL-incompatible**, then moved to **BeOpen.com** (Python 2.0 under yet another licence), then to Digital Creations. Four stewards in a decade, each with its own licence, and one version legally unable to combine with the era's dominant free-software licence. The **Python Software Foundation (PSF)** was formed in 2001 to *own* Python and its licence permanently, and the PSF License, permissive and GPL-compatible, has governed every release since. This chapter tells that story, with the modern consequence, the copyright chain that ships in every interpreter, on the verification interpreters, and draws the lesson: **a language's legal foundation is infrastructure, as load-bearing as its object model.**

## Section index

- **14.1** The constraint: a language must be legally usable
- **14.2** The copyright chain, and the history it records
- **14.3** The rupture: four owners in a decade
- **14.4** Why the licence mattered: GPL compatibility
- **14.5** The resolution: a foundation that owns the language
- **14.6** Edges: governance as ongoing work
- **14.7** Connections
- **14.8** Exercises
- **14.9** Summary and cross-references

Listings live under `code/ch224/` and are re-executed by `make verify` on the verification interpreters.

---

## 14.1 The constraint: a language must be legally usable

Code that anyone can read is not automatically code that anyone can *use*. Using a language means shipping its interpreter (in a product, a distribution, an appliance), embedding it (in a larger application), and combining it with other software, and every one of those requires a *licence* that permits them. A licence that is unclear about what it permits, that conflicts with the licences of software it must combine with, or that changes with the author's employer, is a liability that keeps serious adopters away, because a company cannot build on a legal foundation it cannot rely on.

Python's early informality created exactly this liability. In the CWI years the licence was permissive but the ownership was an academic institution's, not a structure designed to steward a language. When Guido changed employers, the licence changed with him, because whoever *owned* the copyright set the terms. By 2000, Python had been released under CWI's terms, then CNRI's, then BeOpen's, and the CNRI licence had a specific defect (§14.4) that made one version legally incompatible with the GPL. The constraint the PSF was created to answer is that **a language needs a permanent, neutral owner and a stable, compatible licence**, because without them, the ecosystem, the enterprises, distributions, and projects that must be legally free to use Python, cannot be built.

---

## 14.2 The copyright chain, and the history it records

```python
# code/ch224/l01_the_licence_rupture.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the licence ships in the interpreter (sys.copyright) ---
  sys.copyright names the stewards (years elided, they drift):
    present : True  Python Software Foundation
    present : True  BeOpen.com
    present : True  Corporation for National Research Initiatives
    present : True  Stichting Mathematisch Centrum
  the copyright chain IS the history: PSF, then BeOpen, then CNRI,
  then CWI (Stichting Mathematisch Centrum) - each entity that
  stewarded Python, in reverse order
```

**The copyright notice in every Python interpreter is the licence history, recorded in the code itself.**
`sys.copyright` names four entities: the Python Software Foundation, BeOpen.com, the Corporation for National Research Initiatives, and Stichting Mathematisch Centrum (CWI's legal name). These are the four stewards of Python, listed in reverse chronological order, and the fact that *all four* are named is itself the point: the licence is a *chain*, each steward's contribution carried forward under terms that had to be reconciled. The copyright notice is not boilerplate; it is the legal record of a language that changed hands four times and whose current permissive licence had to encompass all four contributions. That the chain ships in every interpreter, checkable with one line, makes the history concrete: run any Python and you can read whom it descends from.

**The chain records reconciliation, not just succession.**
Each steward held copyright over its contributions, so the current PSF License had to be compatible with, and incorporate, the terms under which CWI, CNRI, and BeOpen released their parts. This is why the copyright notice lists all four rather than just the current owner: the license is a *composite*, permitting use of code contributed under four sets of terms, unified into one permissive whole. The reconciliation was legal work, negotiating with CNRI over the 1.6 licence's defect, structuring the PSF to hold copyright going forward, and the copyright chain is its artifact. A language's licence, this chapter's lesson, is a living legal structure, and Python's carries its turbulent origin in plain sight.

---

## 14.3 The rupture: four owners in a decade

```text
--- the rupture, as the copyright chain records it ---
  CWI (Amsterdam)  1991-1995  Guido's original institution
  CNRI (USA)       1995-2000  1.6 licence was GPL-INCOMPATIBLE
  BeOpen.com       2000       2.0 under the BeOpen license
  PSF              2001-now   formed to OWN Python permanently
```

**Four owners in a decade is the instability the PSF was created to end.**
Python passed through CWI (1991-1995, Guido's original institution), CNRI (1995-2000, where the GPL-incompatible 1.6 licence was issued), BeOpen.com (2000, Python 2.0's licence), and finally the PSF (2001-now). Each transition brought a new licence, because ownership of the copyright determined the terms, and ownership followed Guido's employment. This is a language whose *legal identity* changed four times in ten years, and for the enterprises, distributions, and projects trying to build on Python, that instability was a real risk: the terms under which you could use Python 1.5.2 differed from 1.6 differed from 2.0, and there was no guarantee the next version would not change them again. A language whose licence keeps changing cannot be trusted by the serious adopters an ecosystem needs.

**The instability was a byproduct of Python's early informality, and the fix was formalisation.**
In the early years, Python was Guido's project, hosted by whatever institution employed him, and its licence was whatever that institution's lawyers produced. This worked while Python was small, and became a liability as it grew: a language used by thousands of organisations cannot have a licence that changes with its author's job. The PSF was the *formalisation*, a dedicated, neutral non-profit whose *purpose* is to own Python's intellectual property and steward its licence, independent of any employer. The rupture, four owners in a decade, is what happens without such a structure; the PSF is the structure that ended it, and every release since 2001 has had the same stable owner and licence, which is the continuity the timeline after this point rests on.

---

## 14.4 Why the licence mattered: GPL compatibility

```text
--- why the licence mattered: GPL compatibility ---
  the CNRI 1.6 licence had a Virginia choice-of-law clause that
  made it INCOMPATIBLE with the GPL - meaning GPL software could
  not legally include Python. for a language whose whole value is
  being embedded and combined (Chapter 1: extensibility), a licence
  that forbade combination with the era's dominant free licence was
  an existential problem, not a legal footnote
```

**The CNRI licence's GPL incompatibility was an existential threat to a language built on combination.**
The CNRI licence for Python 1.6 included a clause specifying that disputes would be governed by the law of Virginia (a choice-of-law provision). The Free Software Foundation determined that this clause was incompatible with the GPL, which forbids adding restrictions beyond its own terms, meaning GPL-licensed software could not legally include Python 1.6. For a language whose *entire value proposition* is being embedded and combined (Chapter 1's extensibility decision, a C type is an object, so Python glues to everything), a licence that forbade combination with the GPL, the dominant free-software licence of the era, was not a legal footnote but an existential problem. Half the free-software world could not legally use Python 1.6, and that is the kind of defect that fractures an ecosystem.

**The incompatibility connected the licence to the language's core value.**
Chapter 1 established that Python's success rested on being *extensible* and *combinable*, a language you embed, extend, and glue to other code. A licence that legally *prevented* combination with GPL software directly attacked that value: the technical extensibility was useless where the legal terms forbade the combination. This is why the licence mattered so much and why the resolution was urgent, not because licences are intrinsically important, but because *this* licence defect struck at *this* language's foundational strength. The PSF License was crafted to be GPL-compatible precisely so that Python could be combined with anything, restoring the legal freedom that matches the technical freedom, and the two together are what let the ecosystem grow.

---

## 14.5 The resolution: a foundation that owns the language

```text
--- the resolution: a foundation that owns the language ---
  today Python is owned by the PSF, a non-profit, under a
  permissive GPL-compatible licence (the PSFL). the license and
  governance are STABLE - which is exactly what a language needs
  to be adopted by everyone from hobbyists to banks to distros.
```

**The PSF gave Python a permanent, neutral owner and a stable, permissive, GPL-compatible licence, and that stability is what the ecosystem is built on.**
Since 2001, Python has been owned by the Python Software Foundation, a non-profit whose purpose is stewardship, under the PSF License, permissive (you can do nearly anything with Python, including embed it in proprietary software), GPL-compatible (you can combine it with GPL software), and *stable* (it has not changed with anyone's employment). This stability is precisely what a language needs to be adopted across the full spectrum, hobbyists who need it free, banks who need it legally clear, Linux distributions who need it packageable under their own terms. A language nobody has to worry about the licence of is a language everyone can build on, and the PSF made Python that language. The scientific-computing stack, the web frameworks, the corporate deployments, all of it assumes a stable Python licence, and that assumption is the PSF's achievement.

**The lesson is that governance is infrastructure.**
A programming language's technical design, the object model, the type system, the interpreter, gets the attention, but its *legal and governance* structure is equally load-bearing: without a stable owner and licence, the technical excellence cannot be *relied upon*, because reliance requires legal certainty. The rupture taught the Python community that governance is not a distraction from the "real" work of language design but a *prerequisite* for it, the ecosystem that everything after 2.1 was built on could not exist without the legal foundation the PSF provided. This is why the timeline pauses here: the licence rupture is not a technical chapter, but it is one of the most consequential events in Python's history, because it secured the foundation the technical timeline stands on.

---

## 14.6 Edges: governance as ongoing work

**The PSF owns the licence; it does not, alone, design the language.**
Language design happens through the PEP process (Python Enhancement Proposals) and, historically, Guido's role as Benevolent Dictator For Life (BDFL). The PSF is the *legal and financial* steward, funding development, holding trademarks and copyright, running the infrastructure, distinct from the *technical* governance. The two are complementary: the PSF secures the foundation, the PEP process and (post-2018) the Steering Council decide the language's direction. Conflating them misreads the governance structure.

**Guido stepped down as BDFL in 2018, and governance formalised further.**
After the contentious PEP 572 (the walrus operator) debate, Guido resigned as BDFL, and the community adopted a five-member elected Steering Council (PEP 8016). This is the *technical* governance maturing the way the *legal* governance matured with the PSF, from one person's informal authority to a formal, elected structure. The licence rupture formalised ownership; the 2018 transition formalised direction, and both are the same movement: a language outgrowing the informality of its founding.

**The permissive licence is a deliberate choice with trade-offs.**
The PSF License is permissive (allows proprietary use), not copyleft (which would require derivatives to stay free). This maximises adoption (companies can embed Python in closed products) at the cost of not *requiring* contributions back. It is the right choice for a language that wants ubiquity, but it is a choice, some argue a copyleft licence would have forced more corporate contribution, and the permissive-vs-copyleft trade is a real governance question the PSF answered in favour of adoption.

**And trademark and infrastructure are ongoing PSF work.**
The PSF's role did not end with the licence: it holds the Python trademark (defending against misuse), funds PyPI (the package index, Deep N) and its security work, runs PyCon, and supports development. Governance is not a one-time fix but continuous stewardship, and the PSF's ongoing work, most visibly in packaging security (Chapter 116) and infrastructure, is the licence rupture's resolution *maintained*, not just achieved once.

---

## 14.7 Connections

**Backward.**
The extensibility decision the GPL incompatibility threatened is Chapter 1; the values (openness, community) the PSF institutionalised are Chapter 3; the module and library ecosystem the stable licence enabled is Chapter 10 ("batteries included") and the whole standard library.

**Forward.**
The packaging ecosystem the PSF stewards (PyPI, the trust infrastructure) is Deep N (Chapters 109-116); the governance that decides language direction (the PEP process, the Steering Council) shapes every release in the timeline; the `__future__` change-management mechanism (Chapter 12) is the technical complement to the legal stability the PSF provides.

**Across books.**
Licence and governance matter for every language the shared trading system uses, **Book I**'s C++ is governed by an ISO standards committee (a very different model, formal, slow, vendor-driven), and the contrast is instructive: Python's PSF-plus-PEP model is more agile and community-driven, C++'s ISO model more formal and stable. The shared system depends on *both* being reliably licensed and governed, a bank cannot ship a trading system on a language whose licence might change, and the PSF (for Python) and ISO (for C++) provide the legal certainty the system's deployment requires.

---

## 14.8 Exercises

**1. Read the chain.** Print `sys.copyright` in full; identify each steward and the years; explain what the presence of all four entities in the notice tells you about how the licence was assembled.

**2. Understand the GPL clash.** Research the CNRI licence's choice-of-law clause and why the FSF found it GPL-incompatible; explain in two sentences why a choice-of-law provision can conflict with the GPL's "no additional restrictions" rule.

**3. Permissive vs copyleft.** For a hypothetical new language, argue permissive (PSF-style) versus copyleft (GPL-style) licensing; use Python's adoption-maximising choice and its trade-off (no forced contribution) as the concrete example.

**4. Trace the governance.** Map Python's governance evolution: informal (Guido at CWI/CNRI/BeOpen) → PSF ownership (2001) → BDFL resignation and Steering Council (2018). Explain what each step formalised and why.

**5. The design question.** The licence rupture shows that a language's legal foundation is as load-bearing as its technical design. Argue where a language project should invest in governance *relative to* technical work, too early (bureaucracy before there is anything to govern) versus too late (the rupture), and identify the signal that says "it is time to formalise", using Python's four-owners-in-a-decade as the "too late" warning.

---

## 14.9 Summary and cross-references

- **Between 1.5.2 and 2.1, Python's licence and ownership nearly fractured**: it passed through CWI (1991-1995), CNRI (1995-2000, GPL-incompatible 1.6 licence), BeOpen.com (2000, 2.0 licence), and finally the **Python Software Foundation (2001-now)**, four owners in a decade, the instability the PSF was created to end.
- **The copyright chain ships in every interpreter** (`sys.copyright` names all four stewards), recording not just succession but *reconciliation*, the current permissive PSF License had to encompass code contributed under four sets of terms.
- **The CNRI 1.6 licence's GPL incompatibility** (a Virginia choice-of-law clause) was existential for a language built on *combination* (Chapter 1's extensibility): a licence forbidding combination with the era's dominant free licence attacked Python's foundational strength.
- **The PSF resolved it** with a permanent, neutral owner and a stable, permissive, GPL-compatible licence, the legal certainty that let Python be adopted across the full spectrum from hobbyists to banks to distributions.
- **The lesson is that governance is infrastructure**: a language's legal foundation is as load-bearing as its object model, and the timeline after 2.1 is built on the stability the PSF secured (with technical governance formalising further at Guido's 2018 BDFL resignation).

**Cross-references.** Extensibility and combination → Chapter 1. The values → Chapter 3. Batteries included → Chapter 10. Packaging and the PSF-stewarded ecosystem → Deep N. Change management → Chapter 12. C++'s ISO governance contrast → Book I.
