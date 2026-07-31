# Chapter 277: Tomllib

## The constraint

By 2022, TOML had become Python's own configuration format.
`pyproject.toml` is where build backends, packaging metadata, and the growing majority of Python tools read their settings - it is the file that defines a project's dependencies and build configuration.
And yet, parsing TOML required a *third-party library* (`toml`, or the newer `tomli`).

This produced a small absurdity: every tool that read `pyproject.toml` had to carry a dependency *just to read the file that lists dependencies*.
A packaging tool, a linter, a formatter - each bundled a TOML parser to bootstrap itself from the config format the Python ecosystem had standardized on.
For a language whose "batteries included" philosophy put JSON, CSV, and configparser in the standard library, the absence of a TOML parser - for TOML specifically, the format Python had chosen for its own tooling - was a conspicuous gap.

The constraint Python 3.11 (2022, PEP 680) answered: **put a TOML parser in the standard library**, so reading Python's own configuration format needs no dependency.

This chapter owns no Deep-Volume mechanism; parsing a config format is a standard-library capability.
What it owns is the release: the day reading TOML became dependency-free.

## What shipped

`tomllib` provides `loads(string)` and `load(binary_file)`, which parse TOML into ordinary Python dicts, mapping TOML's types to their Python equivalents.
It is *read-only* by design.
Listing 277.1 shows it on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- loads() turns a TOML string into a plain dict ---
  type(config)        : dict
  config['title']     : 'My Project'
  config['version']   : 3  (an int)
  TOML text becomes an ordinary nested dict. no third-party toml/tomli
  dependency - the parser is in the standard library now
--- TOML types map to Python types ---
  string  host    : 'localhost' (str)
  float   timeout : 5.5 (float)
  bool    active  : True (bool)
  array   ports   : [8000, 8001, 8002] (list)
  each TOML value becomes its natural Python type: strings, ints,
  floats, booleans, and arrays-as-lists - typed, not all strings
--- [tables] become nested dicts ---
  config['owner']['name'] : 'Ada Lovelace'
  config['database']['host'] : 'localhost'
  a [owner] section is a nested dict under 'owner'. dotted access
  mirrors the TOML structure - sections nest as you would expect
--- [[array of tables]] becomes a list of dicts ---
  config['servers'] is a list of 2 tables
    server 'alpha' in region 'us-east'
    server 'beta' in region 'eu-west'
  the [[servers]] double-bracket syntax is TOML's array-of-tables:
  it becomes a Python list of dicts, one per [[servers]] block - the
  shape you want for a repeated config section
--- load(file) reads from an open binary file; it is READ-ONLY ---
  load(binary_file)['title'] : 'My Project'
  tomllib has a dumps/write function? : False
  load() takes a file opened in BINARY mode (TOML is defined as UTF-8).
  tomllib is READ-only by design - it parses but does not write, since
  round-tripping config while preserving comments is a separate job
--- the constraint answered ---
  TOML is Python's config format (pyproject.toml), yet reading it
  needed a third-party parser - a dependency just to read the file
  that lists dependencies. tomllib (3.11) put a read-only TOML parser
  in the stdlib: loads/load map TOML to native Python types and nested
  dicts. reading Python's own config became dependency-free
```

## Why each part answers the constraint

**TOML becomes a plain dict.**
The first block shows `tomllib.loads(CONFIG)` producing an ordinary `dict` - `title` is a string, `version` is an int.
No third-party `toml` or `tomli` import is needed; the parser is in the standard library, so any tool can read TOML with nothing but the interpreter.

**Types map naturally.**
The second block shows TOML's typed values becoming their Python equivalents: a string stays a `str`, `5.5` is a `float`, `true` is a `bool`, and an array is a `list`.
Unlike formats where everything arrives as text and you re-parse, TOML values come out typed - the parser does the conversion, so `timeout` is a number you can compute with, not `"5.5"`.

**Tables nest.**
The third block shows `[owner]` and `[database]` sections becoming nested dicts, so `config["owner"]["name"]` mirrors the TOML structure directly.
Sections nest as you would expect, and dotted dict access reads like the config's own hierarchy.

**Array-of-tables becomes a list of dicts.**
The fourth block shows TOML's `[[servers]]` double-bracket syntax - the array-of-tables - becoming a Python list of dicts, one per block.
This is exactly the shape you want for a *repeated* config section (multiple servers, multiple environments), and it maps cleanly to iterating a list of dicts.

**Read-only, binary input.**
The fifth block covers two deliberate design decisions.
`load` takes a file opened in *binary* mode, because TOML is defined as UTF-8 and reading bytes avoids encoding ambiguity.
And `tomllib` has *no* writer (`hasattr(tomllib, "dumps")` is `False`): it is read-only by design.
Writing TOML while preserving comments, formatting, and structure is a genuinely harder, separate problem - one the standard library deliberately left to specialized third-party libraries rather than shipping a lossy writer.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; `tomllib` is a standard-library parser (adapted from the third-party `tomli`).
What the timeline records is the release act: in 3.11, PEP 680 added a read-only TOML parser to the standard library, closing the gap where reading Python's own config format required a dependency.
The modern consequence, verified above, is that tools read `pyproject.toml` and other TOML config with `tomllib` alone, and the "dependency to read the dependency file" absurdity is gone - while writing TOML remains a third-party concern, by intent.

## Where this lands

`tomllib` is a small, focused addition that removed a real friction from the Python tooling ecosystem.
Reach for it to read any TOML configuration - `pyproject.toml`, tool configs, settings files - with `loads` for a string or `load` for a binary file, and work with the resulting native dicts, lists, and typed values.
Remember two things: open the file in binary mode, and it is read-only - if you need to *write* TOML while preserving structure, use a third-party library built for round-tripping.
No Deep Volume owns a config mechanism; this chapter is the record of the release that made reading Python's config format dependency-free.
