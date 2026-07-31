# Chapter 243: Keyword-Only Arguments

## The constraint

Read this call and tell me what it does:

```python
connect("db.internal", 5, True, False)
```

You cannot, not without opening the function definition.
What is `5` - a timeout, a port, a retry count?
What do `True` and `False` switch on?
This is the disease of positional arguments used for options: every option becomes a bare, meaningless value at the call site, and the reader has to cross-reference the signature to decode it.

Python had keyword arguments from the start - you *could* write `connect("db.internal", timeout=5, retry=True, verbose=False)`.
But nothing *required* it.
A function author who wanted options to be readable could only hope callers passed them by name; any caller was free to fall back to the unreadable positional form.
Worse, positional order became a compatibility contract: once callers passed options positionally, the author could never reorder or insert a parameter without silently breaking them.

The constraint Python 3.0 (2008, PEP 3102) answered: **let a function's signature *require* that certain parameters be passed by name, so options are self-documenting at every call site and their order is never frozen into callers.**

This is a two-track chapter.
The call and argument-binding model - how positional and keyword arguments are matched to parameters, how `*args` and `**kwargs` collect the overflow, the full binding algorithm - belongs to Deep Volume B.
What this chapter owns is the release: the day a signature gained the power to demand named arguments.

## What shipped

A bare `*` in a parameter list marks a boundary: every parameter *after* it is keyword-only and must be passed by name.
A `*args` catch-all does the same for the parameters that follow it.
Listing 243.1 shows both, and why they matter, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- a bare * makes every following parameter keyword-only ---
  connect('db', timeout=5, retry=True) ->
    db timeout=5 retry=True verbose=False
  host is positional; timeout/retry/verbose come after `*`, so they
  MUST be named. the call spells out what each option is - no bare
  5/True/False whose meaning you have to look up
--- passing a keyword-only argument positionally is an ERROR ---
  connect('db', 5) -> TypeError: connect() takes 1 positional argument but 2 were given
  the function AUTHOR decided timeout cannot be positional. the
  unreadable connect('db', 5, True, False) is now impossible to
  write - the signature forbids it, not just discourages it
--- the readability contrast, side by side ---
  positional (hypothetical) : connect('db', 5, True, False)
  keyword-only (enforced)   : connect('db', timeout=5, retry=True,
                                      verbose=False)
  same information; the second is self-documenting. keyword-only
  arguments make the readable form the ONLY form
--- *args also opens keyword-only: params after *args are named ---
  log('INFO', 'a', 'b', 'c') : [INFO] a b c
  log('WARN', 'x', 'y', sep='-', upper=True) : [WARN] X-Y
  when a function takes *messages (any number of positionals), sep
  and upper come AFTER it, so they are automatically keyword-only -
  there is no positional slot left for them. options stay named
--- why it matters for API evolution ---
  because options are named, the author can ADD a new keyword-only
  parameter without breaking any existing call: no caller was
  relying on positional order for those options. positional params,
  by contrast, freeze their order into every call site forever
--- the constraint answered ---
  positional arguments let options be passed as bare values, making
  call sites unreadable and positional order a compatibility trap.
  keyword-only parameters (3.0) let a signature REQUIRE that options
  be named, so calls document themselves and new options can be
  added safely. the signature became an API-design tool
```

## Why each part answers the constraint

**The bare `*` marks the boundary.**
The first block shows `connect(host, *, timeout=30, retry=False, verbose=False)`: `host` is an ordinary positional parameter, and everything after the `*` must be passed by name.
The call `connect('db', timeout=5, retry=True)` spells out each option, so there is no `5`/`True` whose meaning you must look up.

**The requirement is enforced, not suggested.**
The second block shows the enforcement: `connect('db', 5)` raises `TypeError` because `connect` accepts only one positional argument and `5` has no positional slot to land in.
This is the crux.
Previous to 3.0, a signature could *encourage* named options only by convention; a caller could always ignore it.
Keyword-only parameters let the author *forbid* the positional form.
The unreadable `connect('db', 5, True, False)` is not merely discouraged - it will not run.

**The readable form becomes the only form.**
The third block puts the two call styles side by side: the hypothetical positional `connect('db', 5, True, False)` versus the enforced `connect('db', timeout=5, retry=True, verbose=False)`.
Same information, and the keyword-only signature makes the self-documenting version the only one a caller can write.
Readability stops depending on caller discipline.

**`*args` opens keyword-only automatically.**
The fourth block shows the second trigger.
`log(level, *messages, sep=" ", upper=False)` collects any number of positional messages in `*messages`, so `sep` and `upper` come *after* the catch-all - there is no positional slot left for them, making them keyword-only by necessity.
This is a natural and common way keyword-only parameters arise: a variadic function's options must be named, because the positional slots are all consumed by the variadic part.

**API evolution is the deeper payoff.**
The fifth block states the benefit that outlasts readability.
Because options are named, the author can *add* a new keyword-only parameter later without breaking any existing call - no caller was depending on positional order for those options.
Positional parameters, by contrast, freeze their order into every call site: reorder or insert one, and every positional caller breaks.
Keyword-only parameters are thus a tool for keeping an API extensible over time, not just readable in the moment.

## The two-track note

The full argument-binding algorithm - how the interpreter matches a call's positional and keyword arguments against a signature's positional, keyword-only, `*args`, and `**kwargs` slots, and how positional-only parameters (a later addition, `/` in the signature) complete the picture - is Deep Volume B's to develop.
What the timeline records is the release act: in 3.0, PEP 3102 gave signatures the power to require named arguments.
The modern consequence, verified above, is that keyword-only parameters are a standard API-design tool - used throughout the standard library for options and flags - and the enforcement is exactly as strict today as when it shipped.

## Where this lands

Keyword-only arguments turned a matter of caller etiquette into a property the function author controls.
Reach for a bare `*` whenever a function has options - flags, tuning knobs, anything a reader could not decode from a bare value - to force those options to be named.
Reach for it especially for boolean parameters, where a positional `True`/`False` is nearly always unreadable.
The result is call sites that document themselves and an API you can extend without breaking callers.
Deep Volume B explains the binding model underneath; this chapter is the record of the release that let a signature demand the readable form.
