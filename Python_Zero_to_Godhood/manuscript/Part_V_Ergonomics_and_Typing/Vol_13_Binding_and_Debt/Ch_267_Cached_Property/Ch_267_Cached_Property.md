# Chapter 267: Cached Property

## The constraint

A `property` (Chapter 227) turns a method into an attribute-like read: `obj.summary` runs a method each time.
That is exactly right when the value is cheap to compute or when it changes - you want a fresh result on every access.
But it is wasteful in a very common situation: an *expensive* result that, once computed, *never changes* for the life of the object.
A parsed representation of an immutable document, a statistical summary over data that will not be mutated, a compiled form of a fixed configuration - computing these once is fine, computing them on every access is a needless repeated cost.

The pattern to fix this was well known and tediously manual: on first access, compute the value, stash it in a private attribute like `self._summary`, and return the stash; on later accesses, check whether the stash exists and return it.

```python
@property
def summary(self):
    if self._summary is None:
        self._summary = expensive_computation()
    return self._summary
```

Every such property carried this compute-check-stash boilerplate, and every one was a small opportunity to get the caching logic wrong.

The constraint Python 3.8 (2019) answered: **make compute-once-and-cache a decorator**, so an expensive stable value computed from an instance's data can be written as a plain method and cached automatically.

This is a two-track chapter.
The descriptor protocol that makes it work - how `property` and `cached_property` hook attribute access - belongs to Deep Volume C, and the argument-keyed caching of `lru_cache` is Chapter 245.
What this chapter owns is the release: the day the compute-once pattern became `@cached_property`.

## What shipped

`functools.cached_property` is a descriptor that, on first access, computes the value and *stores it in the instance's `__dict__` under the same name* - so every later access is a plain attribute read that never re-runs the method.
Listing 267.1 shows it on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- first access computes; later accesses are cached ---
  compute_count before any access : 0
  d.summary (1st access) : {'n': 5, 'total': 14, 'max': 5}
  d.summary (2nd access) : {'n': 5, 'total': 14, 'max': 5}
  d.summary (3rd access) : {'n': 5, 'total': 14, 'max': 5}
  compute_count after three reads : 1   (ran ONCE)
  the body ran a single time; the 2nd and 3rd reads returned the
  stored value. an expensive result computed once, then free forever
--- the cache lives in the instance __dict__ under the same name ---
  'summary' in d.__dict__ before? depends, after access : True
  d.__dict__['summary'] is the cached value : True
  cached_property is a descriptor that, on first access, writes the
  result straight into the instance dict under 'summary'. after that,
  normal attribute lookup finds it FIRST and the descriptor is never
  consulted again - that is why later reads cost nothing (Deep C)
--- the cache is PER INSTANCE, not shared across objects ---
  d.summary  : {'n': 5, 'total': 14, 'max': 5}
  d2.summary : {'n': 2, 'total': 30, 'max': 20}
  d2 computed its own : compute_count(d)=1, compute_count(d2)=1
  each instance caches independently, because the value lives in that
  instance's own __dict__. two datasets, two separate cached summaries
--- to recompute, delete the cached attribute ---
  after deleting the cache, 'summary' in d.__dict__ : False
  next access recomputed : compute_count(d)=2
  deleting the stored attribute makes the next access recompute -
  the escape hatch when the underlying data DID change and you want
  a fresh value. (plain @property never caches, so use that if the
  value changes often)
--- cached_property vs property vs lru_cache ---
  @property       : recomputes every read (cheap/changing values)
  @cached_property: computes once per instance, then a stored attr
  @lru_cache      : caches by ARGUMENTS across calls (Chapter 245)
  cached_property is the right tool for an expensive, stable, no-arg
  result derived from an instance's (effectively immutable) data
--- the constraint answered ---
  a property recomputes every access - wasteful for an expensive
  value that never changes. the manual fix (compute, stash in
  self._x, return it) was boilerplate in every such property.
  cached_property (3.8) makes it a decorator: first access computes
  and stores in the instance dict, every later access is a free read
```

## Why each part answers the constraint

**Compute once, then free.**
The first block shows the core behavior: three accesses to `d.summary` return the same value, but the instrumented `compute_count` shows the method body ran exactly *once*.
The first access computed; the second and third returned the stored value.
An expensive result is paid for once and then read for free.

**The cache is the instance dict.**
The second block explains the mechanism, and it is elegant.
On first access, `cached_property` writes the result into `d.__dict__` under the name `summary`.
Because instance-dict attributes take precedence over class-level descriptors in normal attribute lookup (Deep Volume C), every subsequent `d.summary` finds the stored value *first* and never consults the descriptor again.
That is why later reads cost nothing - they are ordinary attribute lookups, not method calls.

**Per-instance caching.**
The third block shows the cache is per object: `d` and `d2` each compute and cache their own `summary`, because the value lives in each instance's own `__dict__`.
Two datasets have two independent cached summaries, which is exactly right - the value is derived from that instance's data.

**The recompute escape hatch.**
The fourth block shows how to invalidate: delete the cached attribute from the instance dict (`del d.__dict__["summary"]`), and the next access recomputes.
This is the escape hatch for the case where the underlying data genuinely changed and you want a fresh value.
The block is also honest about the precondition: `cached_property` assumes the value is stable, so if the value changes *often*, a plain `@property` (which never caches) is the correct choice.

**Choosing among the three.**
The fifth block places the tools in relation: `@property` recomputes every read (for cheap or changing values), `@cached_property` computes once per instance then becomes a stored attribute (for expensive stable values), and `@lru_cache` caches by *arguments* across calls (Chapter 245).
`cached_property` is specifically the right tool for an expensive, stable, no-argument result derived from an instance's effectively-immutable data.

## The two-track note

The descriptor protocol - how a class-level descriptor participates in attribute lookup, why an instance-dict entry shadows it, the difference between data and non-data descriptors that lets `cached_property` be overridden by the cached value - is Deep Volume C's to develop, and it is the exact mechanism that makes the "store in `__dict__` and never run again" trick work.
What the timeline records is the release act: in 3.8, `functools.cached_property` turned the compute-once-and-stash pattern into a decorator.
The modern consequence, verified above, is that expensive per-instance derived values are written as a plain method with one decorator, cached automatically and invalidated by deletion when needed.

## Where this lands

`cached_property` is a small, sharp tool for a specific and common situation: an expensive value derived from an instance's stable data.
Reach for it when the computation is costly, the result does not change for the object's life (or changes rarely enough that manual invalidation is acceptable), and the value takes no arguments beyond `self`.
Use a plain `@property` when the value is cheap or changes on every read; use `@lru_cache` when you are caching by function arguments rather than per instance; and delete the cached attribute when you deliberately want a recompute.
Be mindful that a class using `cached_property` needs a writable `__dict__` (it does not combine with `__slots__` alone).
Deep Volume C explains the descriptor protocol underneath; this chapter is the record of the release that made compute-once caching a decorator.
