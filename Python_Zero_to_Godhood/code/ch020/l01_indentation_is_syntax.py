"""Listing 20.1 - indentation is not a convention, it is a token.

ABC used indentation for grouping, and Python inherited it. In most languages
that describe themselves as indentation-sensitive, whitespace is handled by a
preprocessing step or a linter. In Python the *lexer* emits INDENT and DEDENT as
real tokens, and the grammar consumes them exactly as another language's grammar
consumes `{` and `}`.

This listing shows the tokens, which is the evidence that the design decision is
structural rather than stylistic.
"""

import io
import tokenize

SOURCE = """\
def f(x):
    if x:
        return 1
    return 0
"""

print("--- the source ---")
print(SOURCE)

print("--- what the lexer emits ---")
for tok in tokenize.generate_tokens(io.StringIO(SOURCE).readline):
    name = tokenize.tok_name[tok.type]
    if name in {"INDENT", "DEDENT", "NEWLINE", "NAME", "OP", "NUMBER", "KEYWORD"}:
        shown = tok.string.replace("\n", "\\n")
        print(f"  {name:8} {shown!r}")

print()
print("--- INDENT and DEDENT are structural, so a bad indent is a SyntaxError ---")
for label, src in [
    ("inconsistent dedent", "def f():\n    if 1:\n        pass\n  return\n"),
    ("unexpected indent  ", "x = 1\n    y = 2\n"),
]:
    try:
        compile(src, "<t>", "exec")
    except (SyntaxError, IndentationError) as exc:
        print(f"  {label} -> {type(exc).__name__}: {exc.msg}")

print()
print("--- and the compiled result is identical to a brace language's ---")
print("  indentation carries no runtime cost: it is consumed at lex time")
code = compile(SOURCE, "<t>", "exec")
print("  co_consts of the module:", [type(c).__name__ for c in code.co_consts])
