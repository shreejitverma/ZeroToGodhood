# requires: 3.14+
"""Listing 25.2 - the payoff: safe-by-construction interpolation.

The f-string SQL/HTML injection Chapter 12 warned against is unavoidable with
f-strings, because the untrusted value is spliced into the finished string before
you can escape it. A t-string hands a processor the parts separately, so the
processor escapes each interpolated value while leaving the literal template text
untouched. This listing writes a minimal HTML processor and shows a script tag
being neutralized.
"""

import html as html_module
from string.templatelib import Interpolation, Template


def render_html(template: Template) -> str:
    """Escape every interpolated value; pass literal template text through."""
    parts = []
    for item in template:
        if isinstance(item, Interpolation):
            parts.append(html_module.escape(str(item.value)))   # untrusted -> escaped
        else:
            parts.append(item)                                   # literal template text
    return "".join(parts)


user_input = "<script>alert('xss')</script>"

print("--- an f-string would splice the script tag in verbatim (unsafe) ---")
unsafe = f"<p>{user_input}</p>"
print("  f-string result:", unsafe)

print()
print("--- the t-string processor escapes the interpolated value ---")
safe = render_html(t"<p>{user_input}</p>")
print("  t-string result:", safe)

print()
print("The processor could tell the literal '<p>' (from the template, trusted)")
print("from the interpolated user_input (untrusted, escaped). An f-string's")
print("finished str has already lost that distinction. The same pattern gives")
print("safe SQL (bind each value as a parameter) and safe shell (quote each")
print("argument), which is why t-strings are the injection-safe interpolation")
print("primitive f-strings could never be.")
