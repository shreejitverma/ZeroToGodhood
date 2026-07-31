"""Listing 286.1 - Python 3.13 (2024): PEP 594, the standard library learns to shrink.

'Batteries included' built a huge standard library, and over decades a lot of
those batteries went flat: modules for dead protocols (telnetlib, nntplib),
obsolete audio formats (aifc, sunau, sndhdr), and unmaintained or insecure
helpers (crypt, cgi). They still shipped, still needed maintenance, and quietly
suggested they were fit for use. Python 3.13 executed PEP 594, removing about two
dozen of these 'dead batteries' after a formal deprecation period. Importing one
now fails cleanly, pushing you to a maintained replacement. This is the
concurrency-reckoning era's other reckoning: a mature language deciding that
REMOVING code is part of stewardship. Deep volumes own no removal mechanism; this
is the release where the stdlib got smaller on purpose. Verified on current
interpreters (all post-3.13).
"""


REMOVED = [
    "telnetlib",   # the Telnet protocol - obsolete and insecure
    "cgi",         # old CGI web helpers - superseded by WSGI/ASGI frameworks
    "nntplib",     # Usenet news - a dead protocol for most users
    "aifc", "sunau", "sndhdr", "imghdr",  # obsolete audio/image format sniffers
    "crypt",       # unix crypt - platform-specific, insecure, unmaintained
    "uu", "xdrlib", "chunk", "mailcap", "pipes",
]


def main() -> None:
    print("--- importing a removed 'dead battery' now fails cleanly ---")
    try:
        import telnetlib
    except ImportError as exc:
        print(f"  import telnetlib -> {type(exc).__name__}: {exc}")
    print("  telnetlib (the Telnet protocol) was obsolete and a security")
    print("  liability. it is gone in 3.13, so importing it fails with a clear")
    print("  ModuleNotFoundError instead of handing you dead, unmaintained code")

    print("--- about two dozen modules were removed together (PEP 594) ---")
    gone = []
    for name in REMOVED:
        try:
            __import__(name)
        except ImportError:
            gone.append(name)
    print(f"  of this sample, removed and now unimportable : {len(gone)}/{len(REMOVED)}")
    print(f"  all of the sample are gone : {len(gone) == len(REMOVED)}")
    print("  PEP 594 named the 'dead batteries' - modules for defunct protocols,")
    print("  obsolete formats, and insecure or unmaintained helpers - and 3.13")
    print("  removed them as a batch after a multi-release deprecation window")

    print("--- the removals push you toward maintained replacements ---")
    replacements = {
        "cgi": "a WSGI/ASGI web framework (Flask, FastAPI, Django)",
        "telnetlib": "a third-party client, or ssh/paramiko for real remote work",
        "crypt": "hashlib / passlib for password hashing",
        "imghdr": "a library like Pillow, or filetype, for format detection",
    }
    for old, new in replacements.items():
        print(f"  {old:>10} -> {new}")
    print("  none of these needs left users stranded - each has a better,")
    print("  maintained option. removal is a nudge to the right tool, not a")
    print("  capability lost")

    print("--- the core library is unaffected; only the flat batteries went ---")
    import json, csv, sqlite3, datetime, itertools  # all still here
    print(f"  json, csv, sqlite3, datetime, itertools still import : "
          f"{all([json, csv, sqlite3, datetime, itertools])}")
    print("  PEP 594 was surgical: it removed modules that were obsolete or")
    print("  unmaintained, not the vast, healthy core. the stdlib got LIGHTER,")
    print("  not weaker - less to maintain, less to mislead newcomers")

    print("--- the constraint answered ---")
    print("  'batteries included' accreted modules that went obsolete, insecure,")
    print("  or unmaintained yet kept shipping - maintenance burden and false")
    print("  endorsement. PEP 594 (3.13) removed about two dozen dead batteries")
    print("  after formal deprecation, each with a maintained alternative. a")
    print("  mature stdlib decided that removing code is part of stewardship")


if __name__ == "__main__":
    main()
