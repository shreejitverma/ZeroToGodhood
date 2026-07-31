# Chapter 283: Immortal Objects

## The constraint

CPython manages memory with *reference counting*: every object carries a count of how many references point to it, incremented on each new reference and decremented on each release, and freed the instant the count hits zero.
This is simple and prompt, and for most objects it is fine.

But consider the objects used *everywhere*: `None`, `True`, `False`, the small integers.
`None` is referenced constantly - every function that returns nothing, every default argument, every "is this set?" check touches it.
Each of those touches bumps `None`'s reference count up and later back down.
Reading `None` a million times means a million refcount writes to a single shared object.

Normally this churn is merely wasteful.
In two modern settings it is *actively harmful*.
Under free-threading (no GIL), every refcount update on a *shared* object must be an *atomic* operation, and `None` is shared by every thread - so its refcount becomes a contention hotspot, with threads fighting over one cache line.
And after `os.fork()`, the child is supposed to share the parent's memory pages copy-on-write - but every refcount write *dirties* a page, forcing a copy of memory that was meant to stay shared, so a program that merely reads shared objects ends up duplicating them.

The constraint Python 3.12 (2023, PEP 683) answered: **stop the refcount churn on the ubiquitous, long-lived objects** - make them *immortal*, with a fixed refcount that is never modified.

This is a two-track chapter.
The free-threading and subinterpreter story this enables is Deep Volume L's subject.
What this chapter owns is the release: the day the most-used objects stopped paying the reference-counting tax.

## What shipped

Immortal objects - `None`, `True`, `False`, small integers, interned strings, and other long-lived singletons - carry a fixed, saturated reference count that the interpreter never increments or decrements, so they are never touched and never freed.
Listing 283.1 shows the behavior on today's interpreters, using thresholds (never a raw count) so the output is version-independent.

Verified output (CPython 3.13.5):

```text
--- the ubiquitous singletons are immortal: a saturated refcount ---
    None refcount is saturated (immortal) : True
    True refcount is saturated (immortal) : True
   False refcount is saturated (immortal) : True
   int 0 refcount is saturated (immortal) : True
   int 1 refcount is saturated (immortal) : True
  None/True/False and small ints report an enormous, fixed refcount -
  the 'immortal' marker. it means the count is pinned and will never
  reach zero, so these objects are never touched and never freed
--- a normal object has a modest, LIVE refcount ---
  a fresh list's refcount is immortal? : False   (no - it is a normal, counted object)
  ordinary objects still use real reference counting: their count is
  small and reflects how many references exist. immortality is only
  for the handful of objects that live for the whole program anyway
--- adding a reference does NOT change an immortal's count ---
  getrefcount(None) unchanged after a new reference : True
  binding another name to None left its refcount untouched - because
  immortal objects skip the increment entirely. that skipped write is
  the whole point
--- but a normal object's count DOES move with references ---
  refcount rose when aliased : True
  and fell when the alias was deleted : True
  the contrast is the point: mortal objects pay the bump-and-drop
  cost (and get freed at zero); immortal ones opt out of it
--- why immortality matters: free-threading and fork ---
  under free-threading (Deep L, Part VII), every refcount bump on a
  SHARED object needs an ATOMIC write - and None is shared by every
  thread, so its count would be a contention hotspot. immortal = no
  writes = no contention. and after os.fork(), refcount writes dirty
  copy-on-write pages; immortal objects keep those pages shared. PEP
  683 is groundwork the no-GIL work (Part VII) needed
--- the constraint answered ---
  reference counting churned constantly on None/True/False/small ints -
  wasted work normally, and actively harmful under free-threading
  (atomic contention) and fork (copy-on-write page dirtying). PEP 683
  (3.12) made those objects immortal: a fixed refcount that is never
  touched. the most-used objects stopped paying the counting tax
```

## Why each part answers the constraint

**The singletons are immortal.**
The first block shows `None`, `True`, `False`, and small ints reporting a saturated (enormous, fixed) reference count - the immortal marker.
The count is pinned: it will never reach zero, so these objects are never freed and, crucially, never *touched* by refcount operations.

**Normal objects are unaffected.**
The second block shows a fresh list is *not* immortal - it uses real reference counting, with a modest count reflecting how many references exist.
Immortality is deliberately narrow: only the handful of objects that live for the whole program's lifetime anyway.
Ordinary objects keep the prompt, precise cleanup that reference counting provides.

**Immortals skip the increment.**
The third block shows the mechanism's effect: binding another name to `None` leaves `getrefcount(None)` *unchanged*, because immortal objects skip the refcount increment entirely.
That skipped write - multiplied across every reference to `None` in a running program - is the whole point.

**Mortals still count.**
The fourth block confirms the contrast: a normal object's refcount *rises* when aliased and *falls* when the alias is deleted (and it is freed at zero).
Mortal objects pay the bump-and-drop cost and get prompt cleanup; immortal ones opt out of both.
The two behaviors coexist, applied to the objects each suits.

**Why it matters.**
The fifth block connects the change to its purpose.
Under free-threading (Deep Volume L, Part VII), every refcount bump on a shared object needs an atomic write, and `None` is shared by every thread - so its count would be a contention hotspot that serializes threads on one cache line.
Immortal means no writes, which means no contention.
And after `os.fork()`, refcount writes dirty copy-on-write pages; immortal objects keep those pages shared, so a forked child that only reads shared singletons does not duplicate their memory.
PEP 683 is groundwork the no-GIL work needed - a performance change that is also an enabling change for the concurrency reckoning ahead.

## The two-track note

The free-threading model that immortality enables - how per-object locking, biased reference counting, and the no-GIL build work - is Deep Volume L's to develop, and it is where the payoff of PEP 683 is fully realized.
What the timeline records is the release act: in 3.12, PEP 683 made the ubiquitous long-lived objects immortal, ending the refcount churn on them.
The modern consequence, verified above, is that `None`, `True`, `False`, and small ints carry a fixed refcount that is never modified - a modest single-threaded win, and a load-bearing prerequisite for both free-threading and fork-friendly memory sharing.
This is Part VI's thesis in miniature: CPython traded a little internal complexity (two refcount regimes) for cycles saved and a path to concurrency.

## Where this lands, and the close of Scopes and Observation

Immortal objects are invisible in daily use - you never reference-count `None` by hand - but they are one of the quiet, foundational changes that made the next era possible.
There is nothing to *do* with this feature; it simply makes the objects you use most no longer pay a counting tax, and it removes what would otherwise be a fatal contention point for free-threading.
When you reach Part VII and Deep Volume L, remember that the no-GIL interpreter could not perform without this: shared immortal singletons that threads read without fighting over a refcount.
Deep Volume L explains the free-threading story; this chapter is the record of the release that made the most-used objects immortal.

This closes Volume 16, Scopes and Observation.
The volume's headline changes were PEP 695's type-parameter syntax and the `type` statement (Chapter 18) and the low-overhead `sys.monitoring` (Chapter 22), joined by the per-interpreter GIL that PEP 683's immortality helps enable.
Around them, 3.12 delivered f-string formalization, `itertools.batched`, `@override`, ever-better error messages, and the immortal-objects groundwork here.
Part VI - Performance - now hands off to Deep Volumes J and K (the interpreter and performance engineering), and the book moves toward Part VII, the concurrency reckoning that this volume's immortal objects were quietly preparing for.
