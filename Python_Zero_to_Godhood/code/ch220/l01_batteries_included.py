"""Listing 220.1 - the 1.x decision that shaped Python's identity: batteries included.

'Batteries included' - the phrase is attributed to the Python community of the
late 1990s - names the decision that Python would ship a large, useful standard
library, so that common tasks needed no third-party install. This was the
extensibility decision (Chapter 1) turned into policy: because the language was
easy to extend, a rich stdlib could be BUILT, and shipping it made Python
useful out of the box. This listing surveys the breadth a modern interpreter
carries - the direct descendant of that 1.x commitment - and shows why it
mattered: a script can talk to files, the network, JSON, dates, and math with
NOTHING installed. Verified on current interpreters.
"""

import datetime
import json
import math
import sys


def main() -> None:
    print("--- the stdlib is large, and that is the point ---")
    top_level = [m for m in sys.stdlib_module_names if not m.startswith("_")]
    print(f"  the standard library ships well over 100 top-level modules "
          f": {len(top_level) > 100}")
    core = {"json", "os", "sys", "datetime", "math", "socket", "csv",
            "sqlite3", "hashlib", "asyncio", "collections"}
    print(f"  the load-bearing core is all present : "
          f"{core <= set(top_level)}")
    print("  every one is available with zero installs - 'batteries included'")
    print("  means a fresh Python can do real work before any pip runs")

    print("--- one script, five domains, no third-party code ---")
    data = {"symbol": "ACME", "qty": 100, "price": 42.5}
    encoded = json.dumps(data)
    print(f"  json    : {encoded}")
    print(f"  math    : sqrt(2) = {math.sqrt(2):.6f}, pi = {math.pi:.6f}")
    when = datetime.date(2000, 9, 5)             # ~Python 2.0 era
    print(f"  datetime: {when.isoformat()} was a {when.strftime('%A')}")
    print(f"  sys     : running CPython 3.x on this interpreter : "
          f"{sys.version_info.major == 3}")
    print("  files, sockets, threads, http, csv, sqlite, hashlib - all in the")
    print("  box. this breadth is why Python became a SCRIPTING language you")
    print("  reach for, not a language you assemble a toolchain around")

    print("--- the stdlib is a museum of solved problems ---")
    print("  some modules are load-bearing (json, os, datetime, collections);")
    print("  some are historical (the removed cgi, the deprecated modules);")
    print("  knowing which is which is most of what separates a fluent Python")
    print("  engineer from a beginner - the stdlib rewards knowing its shape")
    print("  (Deep Q, R, S, P own the modern, load-bearing quarters)")

    print("--- the trade: a large stdlib ages ---")
    print("  'batteries included' has a cost: the stdlib evolves slowly (it")
    print("  ships with the interpreter, so it cannot break compatibility)")
    print("  and some batteries corrode - modules that were state-of-the-art")
    print("  in 2000 are surpassed by PyPI packages now (requests over")
    print("  urllib, though urllib still works). the decision was right for")
    print("  its era and the tension it created is a theme of the timeline")

    print("--- the constraint answered ---")
    print("  1.x faced the question every young language faces: ship a big")
    print("  library or a small core? Python's extensibility (Chapter 1) let")
    print("  it build a big one, and shipping it made Python immediately")
    print("  useful, which drove adoption. 'batteries included' is the")
    print("  extensibility decision as strategy - and it defined the language")


if __name__ == "__main__":
    main()
