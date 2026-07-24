"""Listing 15.3 - the one gotcha that bites everyone: a bare name captures, it
does not compare.

In a pattern, an unqualified name is a CAPTURE pattern: it matches anything and
binds the name. It is NOT a comparison against a variable of that name. So
`case OK:` does not test `subject == OK`; it binds the subject to OK and matches
everything. To compare against a named constant, use a DOTTED (value) pattern.
"""

# --- the silent bug: a capture as the last case matches everything ---
OK = 200


def handle(code):
    match code:
        case OK:                      # meant to compare to 200; actually captures ALL codes
            return f"treated {code} as OK"


print("--- a bare-name capture silently matches everything ---")
print("  handle(404):", handle(404), " <- not 200, still 'OK'")
print("  handle(500):", handle(500), " <- also silently 'OK'")

# --- the fix: a dotted value pattern compares by equality ---
import http


def check(code):
    match code:
        case http.HTTPStatus.OK:      # dotted: VALUE pattern, compares equality
            return "ok"
        case _:
            return "other"


print()
print("--- a dotted value pattern compares instead of capturing ---")
print("  check(200):", check(200))
print("  check(404):", check(404))

# --- the 3.13 safety net: a capture that shadows LATER cases is a SyntaxError ---
print()
print("--- 3.13 rejects a capture that makes remaining patterns unreachable ---")
try:
    compile("match c:\n case NAME:\n  pass\n case 1:\n  pass\n", "<s>", "exec")
    print("  (compiled: no safety net on this interpreter)")
except SyntaxError as exc:
    print("  SyntaxError:", exc.msg)
print()
print("The safety net only fires when the capture shadows a LATER case; a")
print("capture as the only or last case (like handle above) still compiles and")
print("silently matches everything. Use dotted value patterns for constants.")
