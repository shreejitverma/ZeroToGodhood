# Chapter 249: Inspect Signature

## The constraint

Frameworks live by asking functions a question the functions were never explicitly written to answer: *what parameters do you take?*
A dependency injector needs to know which arguments to supply.
A web router needs to map URL parts to handler parameters.
A CLI builder needs to turn a function's parameters into command-line options.
A test framework needs to match fixtures to the parameters that request them.
All of this is introspection - reading a callable's shape at runtime.

Before Python 3.3, the tool for this was `inspect.getfullargspec`, and it was awkward.
It returned a bundle of *parallel lists*: the argument names in one list, the defaults in another (aligned to the *tail* of the names, so you had to count backwards to match them up), the `*args` name separately, the `**kwargs` name separately, the keyword-only names in yet another list.
Reassembling "parameter `timeout` is keyword-only with default `30`" from these parallel structures was fiddly and error-prone, and the API had grown by accretion around the argument model rather than modeling it cleanly.

The constraint Python 3.3 (2012, PEP 362) answered: **give callables a clean, object-based self-description - one ordered structure of parameter objects, each knowing its own name, kind, and default - that models the full modern argument grammar.**

This is a two-track chapter.
The callable and descriptor model - what a function object is, how bound methods and builtins differ, how the argument kinds relate to the binding algorithm - belongs to Deep Volume C (and the argument model itself to Chapter 243).
What this chapter owns is the release: the day `inspect.signature` gave every callable a first-class, object-based description of itself.

## What shipped

`inspect.signature(callable)` returns a `Signature` object: an ordered mapping of `Parameter` objects, each with a `name`, a `kind` (one of the five parameter kinds), and a `default`.
The `Signature` can `bind` arguments the way a real call would, applying the same matching rules and raising the same errors.
Listing 249.1 shows it on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- signature() gives one object that renders the whole signature ---
  str(signature(handler)) : (path, method='GET', *middlewares, timeout=30, **options)
  one call, one object - it prints the signature as written. no
  reassembling parallel lists of args/defaults/varargs by hand
--- each parameter knows its name, KIND, and default ---
  path         kind=POSITIONAL_OR_KEYWORD default=-
  method       kind=POSITIONAL_OR_KEYWORD default=GET
  middlewares  kind=VAR_POSITIONAL       default=-
  timeout      kind=KEYWORD_ONLY         default=30
  options      kind=VAR_KEYWORD          default=-
  the five KINDS distinguish positional-or-keyword, *args
  (VAR_POSITIONAL), keyword-only, and **kwargs (VAR_KEYWORD) - the
  full argument model of Chapter 243, as inspectable objects
--- bind(): match arguments to parameters, like a call would ---
  bind('/users', 'POST', timeout=5).arguments :
    path = /users
    method = POST
    middlewares = ()
    timeout = 5
    options = {}
  bind() applies the SAME matching rules a real call uses, so a
  framework can resolve what each parameter WOULD receive - the
  basis of dependency injection and request routing
--- bind() enforces the signature: a bad call is caught ---
  bind() with no args -> TypeError: missing a required argument: 'path'
  bind() raises exactly as calling the function would, so validation
  can happen BEFORE the call, from the signature alone
--- it introspects builtins and methods too, uniformly ---
  signature(len)            : (obj, /)
  signature(dict.get)       : (self, key, default=None, /)
  the same Signature object describes user functions, builtins, and
  methods, so introspection code does not special-case callable kinds
--- the constraint answered ---
  callables could be introspected only via getfullargspec's parallel
  lists, awkward and blind to keyword-only args. signature() (3.3)
  gave one Signature object with ordered, self-describing Parameter
  objects and a bind() that mirrors real calls. every modern
  framework's parameter handling stands on it
```

## Why each part answers the constraint

**One object renders the whole signature.**
The first block shows `str(signature(handler))` reproducing the signature exactly as written - `(path, method='GET', *middlewares, timeout=30, **options)`.
A single call yields a single object that already knows the whole shape, with no parallel lists to reassemble.

**Each parameter is self-describing.**
The second block iterates the parameters, and each reports its `name`, its `kind`, and its `default`.
The five kinds - `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL` (`*args`), `KEYWORD_ONLY`, `VAR_KEYWORD` (`**kwargs`), and the positional-only kind seen later - are exactly the argument model of Chapter 243, now represented as inspectable objects rather than inferred from the positions of names in parallel lists.
This is the structural improvement: the model is *modeled*, not encoded implicitly.

**`bind` mirrors a real call.**
The third block shows the capability that makes `signature` a framework foundation.
`sig.bind("/users", "POST", timeout=5)` matches those arguments to the parameters using the *same rules a real call would* - `path` and `method` positionally, `timeout` by keyword, the empty `*middlewares` and `**options` filled in by `apply_defaults`.
A framework can thus compute what each parameter *would* receive, which is the mechanism under dependency injection, request routing, and fixture resolution.

**`bind` enforces the signature.**
The fourth block shows the flip side: `sig.bind()` with no arguments raises `TypeError: missing a required argument: 'path'` - exactly the error the real call would raise.
This lets a framework *validate* a proposed call before making it, from the signature alone.

**It is uniform across callable kinds.**
The fifth block shows `signature` working on `len` and `dict.get` - a builtin and a method - not just user functions.
The same `Signature` object describes all of them (note the `/` marking positional-only parameters), so introspection code does not need to special-case what kind of callable it received.
This uniformity is what lets a framework accept "any callable" and reason about it consistently.

## The two-track note

The callable model - the difference between a function, a bound method, a builtin, and a callable object; how descriptors produce bound methods; how the argument kinds map onto the interpreter's binding algorithm - is Deep Volume C's to develop, with the argument grammar itself established in Chapter 243.
What the timeline records is the release act: in 3.3, PEP 362 gave callables a clean, object-based self-description via `inspect.signature`.
The modern consequence, verified above, is that essentially every framework that inspects functions - `dataclasses` reading field defaults, `pydantic` building validators, `click` generating CLIs, `pytest` matching fixtures, dependency injectors of all kinds - stands on this `Signature`/`Parameter` API.
It is one of those quiet releases whose importance is measured by how much is built on top of it.

## Where this lands

`inspect.signature` is the introspection layer that made Python's "frameworks read your function's shape" magic clean instead of hacky.
Reach for it whenever you need to reason about a callable's parameters programmatically - to inject, validate, route, or document - and prefer it to the older `getfullargspec`, which it supersedes.
Use `Parameter.kind` to distinguish the argument roles, and `Signature.bind` when you need to resolve or validate a call without making it.
Deep Volume C explains the callable model underneath; this chapter is the record of the release that let a function describe itself as a first-class object.
