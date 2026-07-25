"""Listing 61.1 - string interning: one shared object for a repeated value.

Interning stores a single canonical copy of a string so that all equal copies
share one object (and compare by identity). CPython auto-interns identifier-like
string LITERALS at compile time (names, dict keys written in source), but does
NOT intern strings built at runtime. sys.intern() forces interning for those.
The headline value is MEMORY: when the same string value appears many times
(parsed field names, categories, tokens), interning collapses the copies to one
object. The comparison speedup people expect is modest on modern CPython, whose
== already has a fast length+memcmp path. This listing shows the behavior.
"""

import sys


def build(parts):
    return "".join(parts)          # a runtime-built string (not a literal)


def main() -> None:
    print("--- identifier-like literals are auto-interned at compile time ---")
    a = "user_id"
    b = "user_id"
    print(f"  two 'user_id' literals share an object : {a is b}")

    print("--- strings built at runtime are NOT auto-interned ---")
    x = build(["user", "_", "id"])
    y = build(["user", "_", "id"])
    print(f"  equal?                                 : {x == y}")
    print(f"  same object (is)?                      : {x is y}")

    print("--- sys.intern forces sharing ---")
    xi = sys.intern(build(["user", "_", "id"]))
    yi = sys.intern(build(["user", "_", "id"]))
    print(f"  after sys.intern, same object          : {xi is yi}")
    print(f"  interned equals the literal            : {xi == a}")

    print("--- why it matters: many copies collapse to one ---")
    print(f"  a list of N equal runtime strings holds N objects;")
    print(f"  interning makes them share ONE (the benchmark measures the saving)")


if __name__ == "__main__":
    main()
