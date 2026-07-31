"""Listing 293.1 - The frontier: writing code that spans Python versions.

Because several Python versions are always supported at once (Chapter 292), real
code must run on a range of them - and use a new feature where present while
degrading gracefully where absent. There are two disciplined ways to do this:
FEATURE DETECTION (ask whether the capability exists) and VERSION GATING (ask
whether the Python is new enough). Feature detection is usually better: it tests
the thing you actually need rather than a version number that only correlates
with it. This chapter shows the patterns - hasattr, try/import, and
sys.version_info guards - that let one codebase target the frontier and the
supported past at once. Verified on current interpreters.
"""

import sys


def main() -> None:
    print("--- feature detection with hasattr: test the capability itself ---")
    # str.removeprefix arrived in 3.9 (Chapter 268). Detect it, do not assume.
    if hasattr(str, "removeprefix"):
        strip_prefix = lambda s, p: s.removeprefix(p)
    else:                                        # fallback for older Pythons
        strip_prefix = lambda s, p: s[len(p):] if s.startswith(p) else s
    print(f"  str has removeprefix : {hasattr(str, 'removeprefix')}")
    print(f"  strip_prefix('unhappy', 'un') : {strip_prefix('unhappy', 'un')!r}")
    print("  hasattr asks 'does this method EXIST?' - the exact question. the")
    print("  code uses the builtin when present and a hand-written fallback")
    print("  otherwise, so it is correct on every version without a version check")

    print("--- try/import: detect a module the same way ---")
    try:
        import tomllib                            # stdlib since 3.11 (Chapter 277)
        toml_source = "tomllib (standard library)"
    except ImportError:
        try:
            import tomli as tomllib               # the third-party backport
            toml_source = "tomli (third-party backport)"
        except ImportError:
            toml_source = "no TOML parser available"
    print(f"  TOML parser resolved to : {toml_source}")
    print("  try/except ImportError picks the stdlib module where it exists and")
    print("  falls back to a backport otherwise - the standard way to support a")
    print("  feature that graduated FROM a package INTO the stdlib")

    print("--- version gating: when detection is not possible ---")
    uses_new_syntax = sys.version_info >= (3, 12)
    print(f"  target the 3.12+ path? : {uses_new_syntax}")
    print("  some changes are SYNTAX (like PEP 701 f-strings or 3.14's t-strings),")
    print("  which you cannot hasattr - the code would not even parse on an old")
    print("  Python. those you gate by version, often by isolating the new syntax")
    print("  in a module imported only on new enough interpreters")

    print("--- prefer feature detection over version gating where you can ---")
    print("  a version check says 'Python is >= 3.9', which only CORRELATES with")
    print("  'removeprefix exists'. hasattr(str, 'removeprefix') tests the truth")
    print("  directly - so it also works on a backport, a patched build, or an")
    print("  alternative implementation. detect the capability, not the version")

    print("--- the __future__ ledger tells you what became default when ---")
    import __future__
    div = __future__.division.getMandatoryRelease()
    print(f"  __future__.division became mandatory in : {div[0]}.{div[1]}")
    print("  __future__ (Chapter 240) records which once-optional behaviours are")
    print("  now the default and since when - a machine-readable history of the")
    print("  language's forward motion, useful when reasoning about old code")

    print("--- the constraint answered ---")
    print("  supporting many live versions means using new features where present")
    print("  and degrading where absent. feature detection (hasattr, try/import)")
    print("  tests the capability directly and is preferred; version gating")
    print("  (sys.version_info) covers syntax changes detection cannot reach.")
    print("  together they let one codebase span the frontier and the past")


if __name__ == "__main__":
    main()
