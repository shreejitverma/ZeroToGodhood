# Chapter 263: The Breakpoint Builtin

## The constraint

To drop into a debugger at a point in your code, you wrote this:

```python
import pdb; pdb.set_trace()
```

It worked, and it was awful in several small, daily ways.
It is a two-statement incantation crammed onto one line, easy to fumble and easy to mistype.
It hard-wires *one* debugger, `pdb`: if you preferred `ipdb`, a web-based debugger, or your IDE's debugger, you wrote a *different* line, and switching meant editing every occurrence.
And because it is an unremarkable pair of statements, it is easy to leave one behind - a stray `pdb.set_trace()` shipped to production is a classic embarrassment, and finding them all before committing meant grepping for a specific import-and-call pattern.

The deeper problem is that the line conflated two separate things: the *intent* ("stop here and let me inspect") and the *tool* ("use pdb specifically").
Those should be decoupled - the code should express the intent, and which debugger actually runs should be a configuration choice.

The constraint Python 3.7 (2018, PEP 553) answered: **make "stop here in the debugger" a single, memorable builtin routed through one configurable indirection point, so the debugger is a choice rather than a hard-coded import.**

This chapter owns no Deep-Volume mechanism; debugging is a tooling concern, not a language feature.
What it owns is the release: the day dropping into a debugger became one word.

## What shipped

The `breakpoint()` builtin calls `sys.breakpointhook()`, which by default launches `pdb` but can be replaced in code or redirected by the `PYTHONBREAKPOINT` environment variable.
Listing 263.1 shows the indirection on today's interpreters, replacing the hook with a recorder so nothing interactive launches.

Verified output (CPython 3.13.5):

```text
--- breakpoint() is a builtin that routes through sys.breakpointhook ---
  breakpoint is a builtin : True
  sys.breakpointhook exists : True
  breakpoint() does not hard-code pdb; it calls whatever
  sys.breakpointhook points to. that one indirection is the feature -
  the debugger becomes a configuration choice, not a literal import
--- replacing the hook redirects where breakpoint() goes ---
  breakpoint() called the hook 2 times
  it forwarded arguments : ((42,), {'reason': 'inspect state'})
  we pointed sys.breakpointhook at our own function, so breakpoint()
  invoked IT instead of pdb - and passed along any args. this is how
  ipdb, IDEs, and remote debuggers hook in: they just set the hook
--- disabling: point the hook at a no-op ---
  with a no-op hook, breakpoint() did nothing interactive : True
  setting the hook to a no-op (or PYTHONBREAKPOINT=0 in the
  environment) makes every breakpoint() call a harmless pass - you
  can neutralise them globally without editing the code
--- the environment route: PYTHONBREAKPOINT, no code change ---
  the DEFAULT hook reads the PYTHONBREAKPOINT env var:
    unset            -> pdb.set_trace() (the default debugger)
    'ipdb.set_trace' -> import ipdb and call it
    '0'              -> disabled, breakpoint() does nothing
  so you choose your debugger, or turn debugging off, from OUTSIDE
  the program - the source just says breakpoint() and stays neutral
--- the win over `import pdb; pdb.set_trace()` ---
  one short word instead of a two-statement incantation; one
  configurable indirection instead of a hard-wired debugger; and a
  single obvious token to grep for and remove before committing.
  the intent ('stop here') is separated from the tool ('which debugger')
--- the constraint answered ---
  dropping into a debugger meant a long pdb-specific line, repeated
  and hard to swap or scrub. breakpoint() (3.7) made it one builtin
  routed through sys.breakpointhook, so the debugger is chosen by
  code or by PYTHONBREAKPOINT and disabled with =0. 'stop here'
  became one word, decoupled from which debugger runs
```

## Why each part answers the constraint

**One builtin, one indirection point.**
The first block establishes the design: `breakpoint` is a builtin, and `sys.breakpointhook` is the indirection it calls.
`breakpoint()` does not import `pdb` directly; it invokes whatever the hook points to.
That single indirection is the whole feature - it turns the debugger from a literal in your source into a configuration choice.

**Replacing the hook redirects everything.**
The second block shows the mechanism.
Pointing `sys.breakpointhook` at a custom function makes every `breakpoint()` call invoke *that* function instead of `pdb` - and arguments pass through (`breakpoint(42, reason="inspect state")` forwards `(42,)` and `{"reason": "inspect state"}`).
This is exactly how `ipdb`, IDE debuggers, and remote debuggers integrate: they set the hook, and your unchanged `breakpoint()` calls route to them.

**Disabling is trivial.**
The third block shows a no-op hook making `breakpoint()` do nothing interactive.
You can neutralize every breakpoint in a program globally - by setting the hook to a no-op in code, or `PYTHONBREAKPOINT=0` in the environment - without editing the source.
A stray `breakpoint()` is far less dangerous than a stray `pdb.set_trace()`, because it can be switched off from outside.

**The environment route needs no code change.**
The fourth block describes the `PYTHONBREAKPOINT` variable that the default hook honors: unset launches `pdb`, `ipdb.set_trace` launches `ipdb`, `0` disables entirely.
So you choose your debugger, or turn debugging off, from *outside* the program - the source just says `breakpoint()` and stays neutral about which tool runs.
This is the decoupling the old line lacked.

**The concrete wins.**
The fifth block summarizes: one short word instead of a two-statement incantation; one configurable indirection instead of a hard-wired debugger; and a single obvious token (`breakpoint`) to grep for and remove before committing.
The intent and the tool are separated - the code expresses "stop here," and configuration decides "with which debugger."

## The two-track note

There is no language mechanism here to defer to a Deep Volume; `breakpoint` is a small builtin plus a documented hook, built on ordinary callable indirection.
What the timeline records is the release act: in 3.7, PEP 553 added `breakpoint()` and `sys.breakpointhook`, decoupling the intent to debug from the choice of debugger.
The modern consequence, verified above, is that `breakpoint()` is the standard way to enter a debugger, IDEs and alternative debuggers integrate through the hook, and `PYTHONBREAKPOINT=0` is a standard way to run code with all breakpoints neutralized.

## Where this lands

`breakpoint()` is a small ergonomics win that quietly improved a daily ritual.
Use `breakpoint()` wherever you would once have written `import pdb; pdb.set_trace()` - it is shorter, memorable, and greppable.
Configure your preferred debugger via `PYTHONBREAKPOINT` (or by setting `sys.breakpointhook`), and set `PYTHONBREAKPOINT=0` in environments where breakpoints must never fire.
No Deep Volume owns a debugger; this chapter is the record of the release that made dropping into one a single, configurable word.
