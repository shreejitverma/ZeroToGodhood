"""Listing 263.1 - Python 3.7 (2018): the breakpoint() builtin, a debugger you can redirect.

To drop into a debugger you wrote `import pdb; pdb.set_trace()` - a long, easy-
to-fumble incantation hard-wired to ONE debugger (pdb). If you used a different
debugger (ipdb, web-pdb, an IDE's), you wrote a different line, and you had to
find and delete every one before committing. Python 3.7's PEP 553 added the
breakpoint() builtin: a short, memorable call that routes through
sys.breakpointhook, so the debugger it launches is CONFIGURABLE - swap the hook
in code, or set PYTHONBREAKPOINT=ipdb.set_trace (or =0 to disable) with no code
change. Deep volumes own no debugger; this is the release that made 'stop here
in the debugger' one word and one indirection point. This listing replaces the
hook with a recorder so nothing interactive launches. Verified on current
interpreters.
"""

import sys


def main() -> None:
    print("--- breakpoint() is a builtin that routes through sys.breakpointhook ---")
    print(f"  breakpoint is a builtin : {callable(breakpoint)}")
    print(f"  sys.breakpointhook exists : {hasattr(sys, 'breakpointhook')}")
    print("  breakpoint() does not hard-code pdb; it calls whatever")
    print("  sys.breakpointhook points to. that one indirection is the feature -")
    print("  the debugger becomes a configuration choice, not a literal import")

    print("--- replacing the hook redirects where breakpoint() goes ---")
    calls = []
    def fake_debugger(*args, **kwargs):          # stand in for pdb.set_trace
        calls.append((args, kwargs))
    original = sys.breakpointhook
    sys.breakpointhook = fake_debugger
    try:
        breakpoint()                             # -> fake_debugger(), not pdb
        breakpoint(42, reason="inspect state")   # args forward to the hook
    finally:
        sys.breakpointhook = original
    print(f"  breakpoint() called the hook {len(calls)} times")
    print(f"  it forwarded arguments : {calls[1]}")
    print("  we pointed sys.breakpointhook at our own function, so breakpoint()")
    print("  invoked IT instead of pdb - and passed along any args. this is how")
    print("  ipdb, IDEs, and remote debuggers hook in: they just set the hook")

    print("--- disabling: point the hook at a no-op ---")
    ran = []
    sys.breakpointhook = lambda *a, **k: ran.append("nothing")
    try:
        breakpoint()
    finally:
        sys.breakpointhook = original
    print(f"  with a no-op hook, breakpoint() did nothing interactive : "
          f"{ran == ['nothing']}")
    print("  setting the hook to a no-op (or PYTHONBREAKPOINT=0 in the")
    print("  environment) makes every breakpoint() call a harmless pass - you")
    print("  can neutralise them globally without editing the code")

    print("--- the environment route: PYTHONBREAKPOINT, no code change ---")
    print("  the DEFAULT hook reads the PYTHONBREAKPOINT env var:")
    print("    unset            -> pdb.set_trace() (the default debugger)")
    print("    'ipdb.set_trace' -> import ipdb and call it")
    print("    '0'              -> disabled, breakpoint() does nothing")
    print("  so you choose your debugger, or turn debugging off, from OUTSIDE")
    print("  the program - the source just says breakpoint() and stays neutral")

    print("--- the win over `import pdb; pdb.set_trace()` ---")
    print("  one short word instead of a two-statement incantation; one")
    print("  configurable indirection instead of a hard-wired debugger; and a")
    print("  single obvious token to grep for and remove before committing.")
    print("  the intent ('stop here') is separated from the tool ('which debugger')")

    print("--- the constraint answered ---")
    print("  dropping into a debugger meant a long pdb-specific line, repeated")
    print("  and hard to swap or scrub. breakpoint() (3.7) made it one builtin")
    print("  routed through sys.breakpointhook, so the debugger is chosen by")
    print("  code or by PYTHONBREAKPOINT and disabled with =0. 'stop here'")
    print("  became one word, decoupled from which debugger runs")


if __name__ == "__main__":
    main()
