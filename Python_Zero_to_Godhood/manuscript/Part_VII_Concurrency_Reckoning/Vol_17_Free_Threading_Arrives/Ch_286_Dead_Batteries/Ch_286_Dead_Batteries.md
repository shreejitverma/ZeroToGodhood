# Chapter 286: Dead Batteries

## The constraint

"Batteries included" is one of Python's oldest and best slogans: the standard library ships with tools for a vast range of tasks, so a great deal is possible with no dependencies at all.
Over three decades, that philosophy built an enormous standard library - and, inevitably, a lot of those batteries went flat.

Modules accumulated for protocols that died (`telnetlib` for Telnet, `nntplib` for Usenet), for obsolete media formats (`aifc`, `sunau`, `sndhdr`, `imghdr`), and for helpers that became insecure or unmaintained (`crypt`, `cgi`).
They kept shipping in every Python for years after they stopped being a good idea.
This carried two real costs.
First, *maintenance*: every module in the standard library must be kept building and passing tests on every platform and every release, and dead modules consumed that effort for no benefit.
Second, and subtler, *false endorsement*: a module's presence in the standard library implicitly says "this is a reasonable, supported way to do this," so a newcomer reaching for `cgi` to build a web app, or `crypt` to hash a password, was being quietly misdirected toward the wrong tool.

The constraint Python 3.13 (2024, PEP 594) answered is one that mature software rarely confronts squarely: **removing code is part of stewardship.**
After a formal, multi-release deprecation period, 3.13 removed about two dozen "dead batteries."

This chapter owns no Deep-Volume mechanism; a module removal is a curation decision, not a language feature.
What it owns is the release: the day the standard library got smaller on purpose.

## What shipped

PEP 594 removed a batch of obsolete, unmaintained, or insecure modules.
Importing one now fails cleanly with `ModuleNotFoundError`, and each removed module has a maintained alternative.
Listing 286.1 shows this on today's interpreters (all post-3.13).

Verified output (CPython 3.13.5):

```text
--- importing a removed 'dead battery' now fails cleanly ---
  import telnetlib -> ModuleNotFoundError: No module named 'telnetlib'
  telnetlib (the Telnet protocol) was obsolete and a security
  liability. it is gone in 3.13, so importing it fails with a clear
  ModuleNotFoundError instead of handing you dead, unmaintained code
--- about two dozen modules were removed together (PEP 594) ---
  of this sample, removed and now unimportable : 13/13
  all of the sample are gone : True
  PEP 594 named the 'dead batteries' - modules for defunct protocols,
  obsolete formats, and insecure or unmaintained helpers - and 3.13
  removed them as a batch after a multi-release deprecation window
--- the removals push you toward maintained replacements ---
         cgi -> a WSGI/ASGI web framework (Flask, FastAPI, Django)
   telnetlib -> a third-party client, or ssh/paramiko for real remote work
       crypt -> hashlib / passlib for password hashing
      imghdr -> a library like Pillow, or filetype, for format detection
  none of these needs left users stranded - each has a better,
  maintained option. removal is a nudge to the right tool, not a
  capability lost
--- the core library is unaffected; only the flat batteries went ---
  json, csv, sqlite3, datetime, itertools still import : True
  PEP 594 was surgical: it removed modules that were obsolete or
  unmaintained, not the vast, healthy core. the stdlib got LIGHTER,
  not weaker - less to maintain, less to mislead newcomers
--- the constraint answered ---
  'batteries included' accreted modules that went obsolete, insecure,
  or unmaintained yet kept shipping - maintenance burden and false
  endorsement. PEP 594 (3.13) removed about two dozen dead batteries
  after formal deprecation, each with a maintained alternative. a
  mature stdlib decided that removing code is part of stewardship
```

## Why each part answers the constraint

**Removed modules fail cleanly.**
The first block shows `import telnetlib` raising `ModuleNotFoundError: No module named 'telnetlib'`.
Telnet is an obsolete, insecure protocol, and the module was a liability; removing it means a program that reaches for it fails immediately and clearly, rather than being handed dead, unmaintained code that might appear to work while carrying security risks.

**A whole batch went at once.**
The second block confirms the scale: the sampled modules are all gone.
PEP 594 named the "dead batteries" as a category - defunct protocols, obsolete formats, insecure or unmaintained helpers - and 3.13 removed them together, after a deprecation window that spanned several releases so the removal was announced long in advance.

**The removals point to replacements.**
The third block addresses the obvious worry - "but what if I needed that?" - by listing where each capability now lives: `cgi` gives way to WSGI/ASGI web frameworks, `telnetlib` to purpose-built clients or SSH, `crypt` to `hashlib`/`passlib`, `imghdr` to libraries like Pillow.
None of these needs left users stranded; each has a better, maintained option.
The removal is a *nudge toward the right tool*, not a lost capability - and in the security cases (`crypt`, `cgi`, `telnetlib`), the replacement is safer.

**The core is untouched.**
The fourth block makes the crucial reassurance concrete: `json`, `csv`, `sqlite3`, `datetime`, `itertools` - the workhorses - all still import.
PEP 594 was surgical, removing the obsolete and unmaintained modules, not the vast healthy core.
The standard library got *lighter, not weaker*: less to maintain, and less to mislead newcomers into using the wrong thing.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; this is a curation decision executed through the ordinary module system.
What the timeline records is a deliberate act of stewardship: in 3.13, after formal deprecation, PEP 594 removed about two dozen dead batteries.
The modern consequence, verified above, is that the removed modules fail cleanly on import, each with a documented replacement, and the standard library is smaller and more trustworthy - its presence now a more reliable signal that a module is a reasonable choice.
This is the concurrency-reckoning era's *other* reckoning: alongside the hard work of removing the GIL, the project also confronted its own accumulated cruft.

## Where this lands, and the close of Free-Threading Arrives

The dead-batteries removal is a small feature to *use* - there is nothing to do but not import the removed modules - and a large one to *understand*, because it marks a shift in how a mature language treats its own history.
For most of Python's life, the standard library only grew; PEP 594 established that it can also shrink, and that shrinking obsolete parts is a service to users, not a betrayal of "batteries included."
If your code depends on a removed module, the migration path is documented and usually leads to a better tool; if it does not, you benefit from a lighter, more maintainable, less misleading standard library.
No Deep Volume owns a removal mechanism; this chapter is the record of the release where the standard library got smaller on purpose.

This closes Volume 17, Free-Threading Arrives.
Its headline changes were the experimental free-threaded (no-GIL) build (Chapter 26) and the copy-and-patch JIT (Chapter 27), with subinterpreters and the per-interpreter GIL (Chapter 23) as their foundation - the first concrete steps of the concurrency reckoning that Part VII is named for.
Around those landmarks, 3.13 delivered `copy.replace`, the unified `@deprecated` decorator, and the dead-batteries pruning here.
Part VII continues with Volume 18, the 3.14 release that moved free-threading from experimental to supported.
