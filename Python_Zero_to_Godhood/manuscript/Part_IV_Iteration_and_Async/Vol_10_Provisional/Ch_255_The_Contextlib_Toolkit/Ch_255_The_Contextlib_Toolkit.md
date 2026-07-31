# Chapter 255: The Contextlib Toolkit

## The constraint

The `with` statement (Chapter 5) gave Python a clean way to guarantee cleanup, built on the `finally` guarantee of the unified `try` (Chapter 232).
But `with` is a mechanism, not a library, and several extremely common patterns *around* it still had to be written out by hand each time - as `try`/`except`/`finally` blocks whose intent was buried in their structure.

Three patterns recurred constantly.
"Ignore this one specific exception" was an empty-`except` block: `try: os.remove(path) except FileNotFoundError: pass` - four lines whose meaning is "delete it if it exists," with the intent hidden in the control flow.
"Capture or silence what this code prints" meant manually saving `sys.stdout`, replacing it, running the code in a `try`, and restoring it in a `finally` - a fiddly and easy-to-botch dance.
And "clean up a *runtime-determined* number of resources" had no clean form at all: `with A, B, C:` requires knowing the managers when you write the code, so a variable-length set of them fell back to manual nesting or hand-written cleanup loops.

The constraint Python 3.4 (2014) answered: **stock `contextlib` with ready-made tools for these recurring patterns, so each becomes a named, self-documenting `with`-block instead of hand-written `try` boilerplate.**

This is a two-track chapter.
Exception unwinding is Deep Volume B's, and the context-manager protocol (`__enter__`/`__exit__`) is Chapter 5's.
What this chapter owns is the release: the day `contextlib` grew the toolbox built on top of them.

## What shipped

Listing 255.1 shows the three headline tools - `suppress`, `redirect_stdout`, and `ExitStack` (the last added in 3.3, completing the set) - on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- suppress(): a with-block that swallows a chosen exception ---
  reached the line after the with-block (the error was suppressed)
  suppress(FileNotFoundError) replaces `try: ... except
  FileNotFoundError: pass` - the intent ('ignore this specific
  error') is now the NAME of the block, not a silent empty except
--- suppress only swallows the named type; others propagate ---
  a ValueError inside suppress(KeyError) propagated : different error
  suppress is precise: it catches only the type(s) you name. an
  unrelated exception passes through, so you do not accidentally
  hide bugs the way a bare `except:` would
--- redirect_stdout(): capture print output cleanly ---
  captured 2 lines from stdout
  first captured line : 'this goes into the buffer, not the terminal'
  redirect_stdout temporarily points sys.stdout at our buffer, so
  code that prints can be captured or silenced without editing it -
  ideal for testing output or quieting a chatty library
--- ExitStack(): manage a DYNAMIC number of context managers ---
  event log : ['open a', 'open b', 'open c', 'using 3 resources', 'close c', 'close b', 'close a']
  a plain `with A, B, C:` needs the managers known at write time.
  ExitStack enters an arbitrary NUMBER of them and guarantees each
  is closed (in REVERSE order) - note close c, b, a on exit
--- the payoff: recurring try shapes become named with-blocks ---
  try/except Exc: pass          -> with suppress(Exc):
  save/restore sys.stdout       -> with redirect_stdout(buf):
  N nested with-statements       -> with ExitStack() as stack:
  each pattern now has a self-documenting name instead of hand-
  written try/finally or deep nesting
--- the constraint answered ---
  `with` automated cleanup, but common patterns around it were still
  boilerplate. contextlib (3.4) stocked the toolbox: suppress for
  ignoring a specific error, redirect_stdout for capturing output,
  ExitStack for a runtime-sized set of managers. recurring try/finally
  shapes became named, precise, self-documenting with-blocks
```

## Why each part answers the constraint

**`suppress` names the intent.**
The first block shows `with suppress(FileNotFoundError):` swallowing exactly that exception, so control reaches the line after the block.
This replaces `try: ... except FileNotFoundError: pass` - and the improvement is not brevity but *clarity*: the intent "ignore this specific error" is now the name of the block, not something the reader has to infer from an empty `except` clause.

**`suppress` is precise, unlike a bare `except`.**
The second block shows the safety property: a `ValueError` inside `suppress(KeyError)` propagates, because `suppress` catches only the type you name.
This is the crucial difference from the lazy `try: ... except: pass` (a bare `except` that swallows *everything*, including bugs).
`suppress` swallows exactly the named exception(s) and lets everything else through, so it hides the error you meant to ignore without hiding the ones you did not.

**`redirect_stdout` captures output cleanly.**
The third block shows `with redirect_stdout(buffer):` sending `print` output into a `StringIO` instead of the terminal, which the test then reads back.
This temporarily repoints `sys.stdout`, and restores it on exit, without the manual save/replace/try/restore dance.
It is the standard way to test what code prints, or to silence a chatty library - capturing output from code you cannot or should not edit.

**`ExitStack` handles a runtime-sized set of managers.**
The fourth block shows the hardest pattern.
A plain `with A, B, C:` needs the managers known when you write the statement.
`ExitStack` lets you `enter_context` an arbitrary *number* of context managers - here one per name in a runtime list - and guarantees each is exited, in reverse order, when the stack closes.
The event log confirms it: `a`, `b`, `c` open in order and close as `c`, `b`, `a`, the correct LIFO cleanup, for a count not known until runtime.

**Each pattern gets a name.**
The fifth block summarizes the payoff: `try/except Exc: pass` becomes `with suppress(Exc):`, the stdout dance becomes `with redirect_stdout(buf):`, and N nested `with` statements become `with ExitStack() as stack:`.
Each recurring shape now has a self-documenting name instead of hand-written `try`/`finally` or deep nesting.

## The two-track note

The unwinding semantics that make these tools correct - how `__exit__` receives and can suppress an exception, why `finally`-style guarantees hold through them - are Deep Volume B's and Chapter 5's to develop.
`suppress` returning truthy from `__exit__` to swallow the exception, `ExitStack` registering callbacks and unwinding them in reverse, `redirect_stdout` saving and restoring a global - all are ordinary applications of the context-manager protocol.
What the timeline records is the release act: in 3.4 (with `ExitStack` from 3.3), `contextlib` gained the toolkit that turns common `with`-adjacent patterns into named blocks.
The modern consequence, verified above, is that these are standard idioms - `suppress` for expected errors, `redirect_stdout`/`redirect_stderr` for output capture, `ExitStack` for dynamic resource management - and later additions (`nullcontext`, `closing`, `contextmanager` itself) round out the set.

## Where this lands

The `contextlib` toolkit is a study in turning control-flow patterns into vocabulary.
Reach for `suppress` when you want to ignore a *specific*, expected exception - and never as a substitute for a bare `except`, which hides everything.
Reach for `redirect_stdout` (and `redirect_stderr`) to capture or quiet output from code you do not want to modify.
Reach for `ExitStack` when the number of resources to manage is known only at runtime, or when you need to conditionally enter context managers.
Deep Volume B and Chapter 5 explain the machinery; this chapter is the record of the release that stocked the toolbox built on it.
