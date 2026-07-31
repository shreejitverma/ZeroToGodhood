"""Listing 277.1 - Python 3.11 (2022): tomllib, TOML parsing in the standard library.

By 2022 TOML had become Python's own configuration format: pyproject.toml is
where build systems, packaging, and most tools read their settings. Yet parsing
it required a THIRD-PARTY library (toml, tomli), so every tool that read
pyproject.toml carried a dependency just to read the file that configures
dependencies. Python 3.11's PEP 680 put a TOML parser in the standard library as
tomllib: load(file) and loads(string) turn TOML into ordinary Python dicts, with
TOML's types (strings, ints, floats, booleans, dates, arrays, nested tables)
mapped to their Python equivalents. It is read-only by design. Deep volumes own
no config mechanism; this is the release that made reading Python's config
format dependency-free. Verified on current interpreters.
"""

import tomllib


CONFIG = """
title = "My Project"
version = 3

[owner]
name = "Ada Lovelace"
active = true

[database]
host = "localhost"
ports = [8000, 8001, 8002]
timeout = 5.5

[[servers]]
name = "alpha"
region = "us-east"

[[servers]]
name = "beta"
region = "eu-west"
"""


def main() -> None:
    print("--- loads() turns a TOML string into a plain dict ---")
    config = tomllib.loads(CONFIG)
    print(f"  type(config)        : {type(config).__name__}")
    print(f"  config['title']     : {config['title']!r}")
    print(f"  config['version']   : {config['version']}  (an int)")
    print("  TOML text becomes an ordinary nested dict. no third-party toml/tomli")
    print("  dependency - the parser is in the standard library now")

    print("--- TOML types map to Python types ---")
    db = config["database"]
    print(f"  string  host    : {db['host']!r} ({type(db['host']).__name__})")
    print(f"  float   timeout : {db['timeout']} ({type(db['timeout']).__name__})")
    print(f"  bool    active  : {config['owner']['active']} "
          f"({type(config['owner']['active']).__name__})")
    print(f"  array   ports   : {db['ports']} ({type(db['ports']).__name__})")
    print("  each TOML value becomes its natural Python type: strings, ints,")
    print("  floats, booleans, and arrays-as-lists - typed, not all strings")

    print("--- [tables] become nested dicts ---")
    print(f"  config['owner']['name'] : {config['owner']['name']!r}")
    print(f"  config['database']['host'] : {config['database']['host']!r}")
    print("  a [owner] section is a nested dict under 'owner'. dotted access")
    print("  mirrors the TOML structure - sections nest as you would expect")

    print("--- [[array of tables]] becomes a list of dicts ---")
    servers = config["servers"]
    print(f"  config['servers'] is a list of {len(servers)} tables")
    for s in servers:
        print(f"    server {s['name']!r} in region {s['region']!r}")
    print("  the [[servers]] double-bracket syntax is TOML's array-of-tables:")
    print("  it becomes a Python list of dicts, one per [[servers]] block - the")
    print("  shape you want for a repeated config section")

    print("--- load(file) reads from an open binary file; it is READ-ONLY ---")
    import io
    binary_file = io.BytesIO(CONFIG.encode("utf-8"))   # tomllib.load needs BINARY
    from_file = tomllib.load(binary_file)
    print(f"  load(binary_file)['title'] : {from_file['title']!r}")
    print(f"  tomllib has a dumps/write function? : {hasattr(tomllib, 'dumps')}")
    print("  load() takes a file opened in BINARY mode (TOML is defined as UTF-8).")
    print("  tomllib is READ-only by design - it parses but does not write, since")
    print("  round-tripping config while preserving comments is a separate job")

    print("--- the constraint answered ---")
    print("  TOML is Python's config format (pyproject.toml), yet reading it")
    print("  needed a third-party parser - a dependency just to read the file")
    print("  that lists dependencies. tomllib (3.11) put a read-only TOML parser")
    print("  in the stdlib: loads/load map TOML to native Python types and nested")
    print("  dicts. reading Python's own config became dependency-free")


if __name__ == "__main__":
    main()
