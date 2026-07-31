# Chapter 272: Mapping Patterns

## The constraint

Dispatching on the contents of a dictionary is one of the most common things real programs do, because so much data arrives as dictionaries: a JSON message, a config block, an event record, an API response.
Before `match`, handling one meant a tangle of membership checks and manual access:

```python
if "type" in event and event["type"] == "move":
    x, y = event["x"], event["y"]
    ...
elif "type" in event and event["type"] == "click":
    button = event["button"]
    ...
```

Every branch re-checks for the key, re-reads it, and re-accesses the fields, and a missing key raises `KeyError` unless you guard for it.

Python 3.10's *mapping patterns* match a dictionary by the keys it contains and bind their values.
The constraint they answer: **dispatch on which keys a mapping has and what their values are, declaratively**, replacing the `in`-check-and-access chains.

This chapter is the mapping-pattern facet of the pattern-matching volume; the mechanism is Deep Volume B's.

## What shipped

A mapping pattern like `{"type": "move", "x": x, "y": y}` matches a mapping that *has* those keys, checks the literal values, and binds the captured ones.
Its defining rule is *subset* semantics - extra keys are allowed - and `**rest` captures the leftovers.
Listing 272.1 shows this on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- match a dict by the keys it contains, binding the values ---
  handle({'type': 'move', 'x': 3, 'y': 4}) : move to (3, 4)
  handle({'type': 'click', 'button': 'left'}) : click with left
  handle({'type': 'key', 'code': 27}) : key 27
  `{'type': 'move', 'x': x, 'y': y}` matches a mapping that has those
  keys, checks 'type' equals 'move', and binds x and y from their
  values. dispatch on structure, not a chain of `in` checks
--- SUBSET semantics: extra keys are allowed ---
  handle({...move with extra keys...}) : move to (1, 2)
  the event has timestamp and source too, but the pattern only names
  type/x/y - and it STILL matches. a mapping pattern requires the
  named keys to be PRESENT, not that they are the ONLY keys. real
  messages always carry fields you ignore, so subset matching is right
--- a missing named key means NO match ---
  handle({'type': 'move', 'x': 5}) : unhandled event type 'move'
  this move is missing 'y', so `{'type':'move','x':x,'y':y}` does NOT
  match - it needs ALL its named keys. it falls to `{'type': t}`,
  which only requires a 'type'. patterns are ordered specific->general
--- capture the leftovers with **rest ---
  split({'id': 42, 'name': 'Ada', 'role': 'admin'}) : id=42, other fields=['name', 'role']
  `{'id': id, **rest}` binds id and collects every OTHER key/value
  into rest (a dict). the mapping analogue of *rest for sequences -
  pull out the fields you name, keep the remainder
--- keys are usually literals; values are full patterns ---
  route(200 + text) : ok, body is text of length 5
  route(404)        : status 404
  the KEY is a literal to look up; the VALUE position is a full
  pattern - a literal (200), a type (int()), a capture, anything. so
  you match on both which keys exist AND what their values look like
--- the constraint answered ---
  dispatching on dict contents was `if 'k' in d and d['k']==...`
  chains with manual access. mapping patterns (3.10) match by the
  keys present (subset semantics: extra keys fine, missing named keys
  fail), bind their values with full sub-patterns, and collect the
  rest with **. dict dispatch became structural and declarative
```

## Why each part answers the constraint

**Match by keys, bind the values.**
The first block shows `handle` dispatching on event dicts: `{"type": "move", "x": x, "y": y}` matches a mapping that has those keys, checks that `"type"` equals `"move"`, and binds `x` and `y` from their values.
The membership-check-and-access chain becomes one pattern that expresses the whole shape.

**Subset semantics - extra keys allowed.**
The second block shows the defining rule.
A richer move event with `timestamp` and `source` keys *still* matches `{"type": "move", "x": x, "y": y}`, because a mapping pattern requires the named keys to be *present*, not that they are the *only* keys.
This is exactly right for real data: messages and records routinely carry fields a given handler ignores, so requiring an exact key set would make patterns brittle.
Subset matching is what makes mapping patterns usable on real-world dicts.

**Missing named keys fail.**
The third block shows the other side: a move missing its `y` key does *not* match `{"type": "move", "x": x, "y": y}`, because all named keys must be present.
It falls through to the more general `{"type": t}`, which requires only a `type`.
This is the specific-before-general ordering that pattern matching relies on - the fully-specified move pattern first, the catch-all type pattern after.

**`**rest` captures leftovers.**
The fourth block shows the mapping analogue of the sequence star: `{"id": id, **rest}` binds `id` and collects every *other* key-value pair into `rest` as a dict.
`split` pulls out the `id` and keeps the remaining fields - the "extract what I name, keep the rest" operation, now declarative.

**Values are full patterns.**
The fifth block shows the depth available in the value position.
The *key* is a literal to look up, but the *value* is a full sub-pattern: `{"status": 200, "body": str() as body}` matches a literal status and a string body (binding it), while `{"status": int() as code}` matches any integer status.
So a mapping pattern matches on both *which keys exist* and *what their values look like* - literals, type patterns, captures, nested structures - composing arbitrarily.

## The two-track note

How the interpreter tests a mapping pattern - checking the subject is a mapping, looking up each named key, matching the value sub-patterns, and collecting `**rest` - is Deep Volume B's to develop, and the "is it a mapping" test connects to the abstract-base-class machinery of Chapter 235.
What the timeline records is the mapping-pattern facet of the 3.10 release: subset-semantics key matching with value sub-patterns and `**rest` capture.
The modern consequence, verified above, is that dispatching on dictionary contents - JSON messages, event records, config blocks - is structural pattern matching rather than `in`-check chains, with subset semantics that fit how real structured data actually looks.

## Where this lands

Mapping patterns are the natural fit for the dictionary-shaped data that pervades modern programs: JSON payloads, event streams, configuration, API responses.
Reach for them to dispatch on which keys a mapping has and what their values are, relying on subset semantics so your patterns are not broken by extra fields.
Name every key a branch requires (a missing one correctly fails the match), use full sub-patterns in the value positions to match on value shape, and use `**rest` when you want the unnamed fields.
Deep Volume B explains the matching mechanism; this chapter is the record of the mapping-pattern facet of structural pattern matching.
