# requires: 3.14+
"""Listing 25.1 - a t-string is a Template object, not a str: it defers the
interpolation so a processor can act on it.

An f-string (Chapter 12) interpolates eagerly and produces a finished str, which
is why it is unsafe to build SQL, HTML, or shell from one: the untrusted value is
already spliced in before you can escape it. PEP 750 (3.14) adds t-strings: t"..."
produces a Template that keeps the literal parts and the interpolated values
SEPARATE, so a processor can escape or validate each value before it becomes a
string.
"""

from string.templatelib import Template

name = "world"
count = 42
t = t"Hello {name}, you have {count} messages"

print("--- a t-string produces a Template, not a str ---")
print("  type(t)         :", type(t).__name__)
print("  isinstance(t, str):", isinstance(t, str))

print()
print("--- the literal parts and the interpolated values are kept separate ---")
print("  t.strings :", t.strings)
print("  t.values  :", t.values)

print()
print("--- each interpolation carries its expression text and format spec ---")
formatted = t"{count:04d}"
for item in formatted.interpolations:
    print(f"  expression={item.expression!r} value={item.value!r} format_spec={item.format_spec!r}")

print()
print("The literal segments in t.strings alternate with the values in t.values.")
print("Because they are separate, a processor sees which parts came from the")
print("template (trusted) and which from interpolation (to be escaped), which an")
print("f-string's finished str can no longer tell apart.")
