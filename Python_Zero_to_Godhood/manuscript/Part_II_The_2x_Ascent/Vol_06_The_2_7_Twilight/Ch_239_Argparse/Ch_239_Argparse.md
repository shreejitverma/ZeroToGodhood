# Chapter 239: Argparse

## The constraint

Every command-line program has to answer the same questions about its arguments: which are required, which are optional, which take a value, what type that value is, what the defaults are, which values are allowed, what happens when the user gets it wrong, and what `--help` should say.
Parsing `sys.argv` by hand means answering all of them yourself, in a loop, for every program - and the hand-rolled result is always subtly different, usually incomplete, and rarely produces a decent error message or help screen.

The standard library had made one attempt: `optparse`, added in 2.3, handled *optional* arguments well.
But it did not handle *positional* arguments at all - the `service` in `deploy service --env prod` - and by the late 2000s it had been declared complete and closed to new features.
A program with both positional and optional arguments still meant gluing `optparse` to hand-written positional handling, back in the loop-and-validate business for half the interface.

The constraint Python 2.7 (2010, PEP 389) answered was this: **make a complete command-line interface - positionals and options, types and defaults, validation, help, and error reporting - something you declare rather than something you parse.**

This is a two-track chapter in a slightly different sense than most: no Deep Volume owns a "command-line" mechanism, because argparse is a standard-library tool built entirely from language features covered elsewhere (the type coercion of Chapter 234's `key`-style callables, the namespace object, exceptions).
What this chapter owns is the release: the day the standard library gained a declarative CLI builder that replaced the hand-written parsing loop, and became the default way Python programs define their command lines.

## What shipped

`argparse.ArgumentParser` lets you *declare* each argument with `add_argument` - its name, type, default, allowed choices, and help text - and then does the parsing.
It returns a `Namespace` of typed, defaulted attributes; it validates types and choices, emitting a usage error and exiting on bad input; and it generates a formatted `--help` screen from the declarations.
Listing 239.1 shows all of this on today's interpreters.
(The listing sets `prog="deploy"` and feeds explicit argument lists rather than reading `sys.argv`, so the output is stable and reproducible.)

Verified output (CPython 3.13.5):

```text
--- you DECLARE arguments; argparse parses them into a Namespace ---
  parsed 'billing --env prod --replicas 3':
    service=billing env=prod replicas=3 dry_run=False
  no parsing loop: each add_argument() declared a name, and argparse
  produced a Namespace with typed, defaulted attributes
--- types and defaults are applied for you ---
  parsed 'billing --dry-run':
    env=dev (default), replicas=1 (default int), dry_run=True (flag set True)
  --replicas is int : int (type=int coerced '3' -> 3 above)
  defaults fill unspecified options, type=int coerces the string,
  and store_true makes --dry-run a boolean flag. all declared, none
  hand-written
--- validation and choices are enforced automatically ---
  '--env moon' rejected: not in choices {dev, staging, prod}
  '--replicas notanumber' rejected: not a valid int
  argparse validates choices and types, prints a usage error, and
  exits - the error handling you would otherwise write by hand for
  every flag (it raises SystemExit, caught here for the demo)
--- generated --help: documentation from the declarations ---
  | usage: deploy [-h] [--env {dev,staging,prod}] [--replicas REPLICAS]
  |               [--dry-run]
  |               service
  | 
  | Deploy a service to an environment.
  | 
  | positional arguments:
  |   service               name of the service to deploy
  | 
  | options:
  |   -h, --help            show this help message and exit
  |   --env {dev,staging,prod}
  |                         target environment
  |   --replicas REPLICAS   number of replicas
  |   --dry-run             plan only, do not apply
  every argument's help= became a formatted --help screen, usage
  line included. you declared the interface once; the docs are free
--- the constraint answered ---
  hand-parsing sys.argv means re-implementing flags, types, defaults,
  validation, help, and errors - badly, every time. argparse (2.7)
  made the CLI a DECLARATION: state the arguments, get parsing,
  coercion, validation, help, and usage errors. that is why real
  Python command-line tools are built on it
```

## Why each part answers the constraint

**Declaration replaces the parsing loop.**
The first block shows the core move: four `add_argument` calls declared the interface, and `parse_args` turned `billing --env prod --replicas 3` into a `Namespace` with `service`, `env`, `replicas`, and `dry_run` attributes.
There is no loop over `sys.argv`, no manual tracking of which flag consumes the next token - the declarations drove all of it.

**Types and defaults are applied automatically.**
The second block shows the machinery filling in for you.
Unspecified options take their declared defaults (`env` is `dev`, `replicas` is `1`); `type=int` coerced the string `"3"` into the integer `3`; and `action="store_true"` made `--dry-run` a boolean flag that is `True` when present.
Each of these is a thing the hand-rolled parser had to do explicitly and often got wrong; here they are consequences of the declaration.

**Validation and errors are handled.**
The third block shows argparse rejecting bad input: `--env moon` fails because `moon` is not among the declared `choices`, and `--replicas notanumber` fails because it is not a valid `int`.
In real use argparse prints a usage message and exits; the listing redirects that message and catches the `SystemExit` only so the demo output stays clean.
The point is that the entire error path - detect, report, exit with a usage message - comes from the declarations, not from hand-written validation after every flag.

**Help is generated from the same declarations.**
The fourth block is the quiet payoff.
The `--help` screen - the usage line with its optionals in brackets, the description, the positional and optional sections, each argument's help text - was assembled entirely from the `add_argument` calls.
You wrote the interface once; the documentation is free and always in sync with the actual parsing, because they come from the same source.

## The two-track note

Because argparse is a library rather than a language mechanism, there is no Deep Volume that "owns" it; it is built from the same building blocks the Deep Volumes cover - callables used as type converters, exceptions for the exit path, a plain object for the result namespace.
What the timeline records is the release decision: in 2.7, `argparse` superseded the positional-blind, feature-frozen `optparse`, and made a complete command-line interface a declaration.
The modern consequence, verified above, is that argparse remains the standard-library default for building CLIs - the `--help` format has evolved slightly across versions (the section heading is now `options:`), but the declare-don't-parse model is unchanged, and it is what almost every Python command-line tool is built on.

## Where this lands

argparse is a case study in the twilight-era standard library maturing: taking a task everyone did badly by hand and turning it into a declarative tool that does it well, completely, and consistently.
Reach for it whenever a script grows past one or two arguments; declare the interface with `add_argument`, let it parse, validate, and document, and spend your effort on what the program *does* rather than on re-implementing argument handling.
For the common case it is more than enough; when a tool grows into many subcommands, the same declarative model extends through `add_subparsers`.
No Deep Volume claims a CLI mechanism; this chapter is the record of the release that made "a real command-line interface" something you state rather than something you parse.
