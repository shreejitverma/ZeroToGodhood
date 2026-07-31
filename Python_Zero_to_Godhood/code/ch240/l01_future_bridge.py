"""Listing 240.1 - Python 2.7 (2010-2020): the __future__ bridge and the last 2.x.

Python 2.7 was, by deliberate decision, the LAST 2.x release. Instead of an
evolving 2.8, 2.9, ... in parallel with 3.x, the language chose a LINEAR path:
2.7 was frozen feature-wise and kept alive as a long-term bridge (2010 until
its end-of-life on 1 January 2020), while all new work went into 3.x. The
bridge's key tool was `from __future__ import <feature>`: it let a 2.7 program
opt INTO specific 3.x behaviours - true division, print as a function, unicode
string literals, absolute imports - so a single codebase could behave like 3.x
while still running on 2.x. This chapter's modern consequence: every one of
those 'future' features is now simply how Python works, and __future__ records
the migration in the language itself. Verified on current interpreters.
"""

# These are the real bridge idiom, at the top of the module where the compiler
# requires them. On Python 3 they are no-ops (the behaviours are already the
# default), which is exactly this chapter's point.
from __future__ import division, print_function, unicode_literals

import __future__


def main() -> None:
    print("--- the __future__ module names the 3.x behaviours 2.7 could opt into ---")
    features = ["division", "print_function", "unicode_literals",
                "absolute_import", "with_statement"]
    for name in features:
        feat = getattr(__future__, name)
        mandatory = feat.getMandatoryRelease()
        rel = f"{mandatory[0]}.{mandatory[1]}" if mandatory else "n/a"
        print(f"  {name:<18} mandatory since Python {rel}")
    print("  each was OPTIONAL in 2.x via `from __future__ import ...` and")
    print("  MANDATORY (just the default) from the release shown. the module is")
    print("  a ledger of behaviours that migrated from opt-in to standard")

    print("--- true division: the flagship __future__ import, now the default ---")
    print(f"  1 / 2   : {1 / 2}   (true division - 3.x default; needed the import in 2.x)")
    print(f"  7 // 2  : {7 // 2}   (floor division - the explicit operator)")
    print("  in 2.x, 1/2 was 0 (integer floor) unless you wrote `from __future__")
    print("  import division`. 3.0 made / always true-divide and // always")
    print("  floor. what was a __future__ opt-in is now simply how / behaves")

    print("--- print is a function, not a statement (print_function, now default) ---")
    print(f"  print is callable : {callable(print)}")
    print(f"  print.__name__    : {print.__name__}")
    end_char = "!"
    print("  print with keyword args", end=f"{end_char}\n")
    print("  2.x `print x` was a STATEMENT; `from __future__ import")
    print("  print_function` made it the function it is in 3.x - so it takes")
    print("  sep=, end=, file=, and composes like any other call")

    print("--- all string literals are unicode text (unicode_literals, now default) ---")
    s = "caf" + chr(0x00E9)                 # "cafe" with a precomposed e-acute
    print(f"  type('...') : {type(s).__name__}   (str IS unicode text in 3.x)")
    print(f"  a plain literal holds code points : {len(s)} of them")
    print("  2.x had bytes-y `str` and separate `unicode`; `from __future__")
    print("  import unicode_literals` made every '...' literal unicode. 3.0 made")
    print("  that the only kind of text (the Deep D story). the bridge previewed it")

    print("--- the point: these imports on 3.x are a harmless no-op ---")
    # This module really does `from __future__ import division, ...` at the top.
    already_default = (1 / 2 == 0.5) and callable(print)
    print(f"  this file imported division/print_function/unicode_literals")
    print(f"  and they changed nothing (already the default) : {already_default}")
    print("  the imports still EXIST and still parse on 3.x - they just do")
    print("  nothing, because the future arrived. that is why bridge code")
    print("  written for 2.7 keeps running unchanged on modern Python")

    print("--- the constraint answered ---")
    print("  Python chose a linear path: 2.7 was the final 2.x, frozen and kept")
    print("  alive as a bridge until 2020, not an evolving parallel line. the")
    print("  __future__ mechanism let one 2.7 codebase adopt 3.x behaviour")
    print("  feature by feature, so migration was gradual, not a cliff. today")
    print("  those futures are the present, and __future__ is the record of how")
    print("  the language crossed over")


if __name__ == "__main__":
    main()
