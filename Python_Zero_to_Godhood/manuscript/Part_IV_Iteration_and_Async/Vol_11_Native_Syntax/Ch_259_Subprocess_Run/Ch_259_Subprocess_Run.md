# Chapter 259: Subprocess Run

## The constraint

Running an external command from Python - invoking `git`, calling a converter, shelling out to a tool - is a routine need, and for most of the language's history it was served by a confusing family of options, none of which was the obvious right choice.

`os.system` ran a command but gave you no way to capture its output, and it passed the command through the shell, opening the door to shell-injection if any part of the command came from untrusted input.
`os.popen` captured output but was deprecated.
`subprocess.Popen` was the powerful, correct foundation - but it was *low-level*: to run a command and get its output you created a `Popen`, wired up `stdout`/`stderr` pipes, called `communicate()`, and checked `returncode` by hand.
The common case - "run this command, wait for it, give me the exit code and the output" - required a paragraph of ceremony against a low-level API.

The constraint Python 3.5 (2015) answered: **provide one high-level function that runs a command to completion and returns a structured result, so the common case is a single call.**

This chapter owns no Deep-Volume mechanism - process invocation is a standard-library capability built on the OS, not a language feature.
What it owns is the release: the day "run a command and get the result" became one call.

## What shipped

`subprocess.run` runs a command to completion and returns a `CompletedProcess` with the `returncode` and, when requested, captured `stdout`/`stderr`.
`capture_output=True` and `text=True` collect output as strings; `check=True` raises on failure; `timeout=` bounds it; `input=` feeds stdin; and passing the command as a *list* avoids the shell.
Listing 259.1 shows it on today's interpreters, running the current Python on fixed one-liners so the output is deterministic.

Verified output (CPython 3.13.5):

```text
--- run() executes a command and returns a CompletedProcess ---
  type(result)      : CompletedProcess
  result.returncode : 0   (0 = success)
  result.stdout     : 'hello from a subprocess\n'
  one call runs the command to completion and hands back an object
  with the exit code and captured output. no Popen, no manual pipe
  wiring, no communicate() - the common case is one line
--- capture_output + text: get stdout/stderr as strings ---
  stdout : 'out\n'
  stderr : 'err\n'
  capture_output collects both streams; text=True decodes them from
  bytes to str. you get the child's output as ordinary strings to
  parse, log, or assert on
--- returncode reports success or failure without raising ---
  a command exiting 3 -> returncode : 3
  by default run() does NOT raise on a nonzero exit; you inspect
  returncode. this suits commands whose failure is an expected
  outcome you want to branch on, not an exception
--- check=True: turn a nonzero exit into an exception ---
  check=True raised CalledProcessError, returncode=1
  with check=True a failing command raises CalledProcessError - the
  right choice when the command MUST succeed and failure should stop
  the flow, like an error in your own code
--- passing input, and why a list (not a shell string) is safer ---
  fed stdin 'quiet text', got : 'QUIET TEXT\n\n'
  input= sends data to the child's stdin. passing the command as a
  LIST of arguments (not one shell string) avoids the shell entirely,
  so untrusted values cannot inject extra commands - the safe default
--- the constraint answered ---
  running a command meant picking from os.system/popen/Popen -
  unsafe, deprecated, or low-level. subprocess.run (3.5) is one call
  that returns a CompletedProcess with return code and captured
  output, check=True to raise on failure, timeout= to bound it, and
  list-args to stay shell-injection-safe. the common case became one line
```

## Why each part answers the constraint

**One call, a structured result.**
The first block shows `run` executing a command and returning a `CompletedProcess` with `returncode` (`0` for success) and captured `stdout`.
No `Popen`, no pipe wiring, no `communicate()` - the whole common case is one function call that hands back an object carrying everything you usually want.

**Output as strings.**
The second block shows `capture_output=True` collecting both streams and `text=True` decoding them from bytes to `str`.
You get the child's `stdout` and `stderr` as ordinary strings, ready to parse, log, or assert on - which is what most callers want, rather than raw byte streams they must decode themselves.

**Failure without raising, by default.**
The third block shows a command exiting with code `3` producing `returncode == 3` and *no exception*.
By default `run` does not treat a nonzero exit as an error, because for many commands a nonzero exit is an expected outcome to branch on (a linter finding issues, a diff finding differences).
You inspect `returncode` and decide.

**`check=True` for must-succeed commands.**
The fourth block shows the opposite policy: with `check=True`, a failing command raises `CalledProcessError` carrying the return code.
This is the right choice when the command *must* succeed and its failure should halt the flow like an error in your own code - fail loudly rather than silently continuing on a broken result.

**Input, and the shell-safety default.**
The fifth block shows `input=` feeding the child's stdin (the uppercased text comes back), and states the security point: passing the command as a *list of arguments* rather than a single shell string means the shell is never invoked, so untrusted values in the arguments cannot inject additional commands.
This list-not-string default is the single most important safety property, and it is why `run([...])` should be preferred over anything that builds a shell command string.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; `subprocess` is a standard-library interface to the operating system's process facilities, built on the file and exception models the Deep Volumes cover.
What the timeline records is the release act: in 3.5, `subprocess.run` unified the command-running story into one high-level function, superseding `os.system`, `os.popen`, and the manual `Popen` dance for the common case (`Popen` remains for streaming and advanced control).
The modern consequence, verified above, is that `subprocess.run` is the standard way to run a command from Python - with `capture_output`/`text` for output, `check` for must-succeed semantics, `timeout` to bound runaway commands, and list-arguments to stay injection-safe.

## Where this lands

`subprocess.run` is the function to reach for whenever you need to run an external command.
Pass the command as a list to avoid the shell; add `capture_output=True, text=True` when you need the output; add `check=True` when failure should raise; add `timeout=` when the command might hang; use `input=` to feed stdin.
Drop to `Popen` only when you genuinely need to stream input and output concurrently or manage a long-lived child - the cases `run` deliberately does not cover.
No Deep Volume owns a process mechanism; this chapter is the record of the release that made running a command a single, safe, structured call.
