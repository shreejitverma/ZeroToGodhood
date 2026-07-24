"""Listing 7.5 - / is always true division, // floors toward negative infinity,
and % follows the divisor's sign.

Python 2's / was floor division for two integers but true division if either was
a float, a silent precision trap. Python 3 split them: / always returns a float,
// always floors. The floor-vs-truncate difference from C is a real portability
hazard.
"""

print("--- the clean split ---")
print("  7 / 2   =", 7 / 2, "  (true division, always a float)")
print("  7 // 2  =", 7 // 2, "  (floor division)")

print()
print("--- the portability hazard: floor vs truncate for negatives ---")
print("  -7 // 2 =", -7 // 2, "  Python floors toward -inf")
print("  int(-7 / 2) =", int(-7 / 2), "  C/Java/Go truncate toward zero")
print("  -7 % 2  =", -7 % 2, "  Python: sign follows the DIVISOR")
print("     (C would give -1 here: sign follows the dividend)")

print()
print("Porting modular arithmetic between Python and C without accounting for")
print("this produces off-by-one bugs that pass every positive-number test.")
print("When you need truncation in Python, use int(a / b) or math.trunc.")
