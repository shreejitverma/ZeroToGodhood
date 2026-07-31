"""Listing 279.1 - Python 3.12 (2023): PEP 701, f-strings become part of the grammar.

For six years f-strings were parsed by a separate, limited sub-parser with
frustrating restrictions: you could not reuse the SAME quote character inside the
braces (f"{d["k"]}" was a SyntaxError - you had to switch to single quotes), you
could not put a backslash in the expression part, comments were forbidden, and
nesting was shallow. Python 3.12's PEP 701 formalized f-strings in the real PEG
grammar (Chapter 15), removing every one of those limits: any quote reuse,
backslashes, multi-line expressions, and arbitrary nesting all just work. Deep J
owns the tokenizer/parser; this is the release that made an f-string's braces
hold ANY valid expression, not a restricted subset. Verified on current
interpreters (which all post-date 3.12, so these forms parse).
"""


def main() -> None:
    print("--- reuse the SAME quote character inside the braces ---")
    data = {"name": "Ada", "role": "engineer"}
    # Pre-3.12: f"{data["name"]}" was a SyntaxError - the inner " closed the f-string.
    result = f"{data["name"]} is a {data["role"]}"
    print(f"  f'{{data[\"name\"]}} ...' -> {result}")
    print("  the inner double quotes no longer collide with the f-string's outer")
    print("  ones. before 3.12 you HAD to switch the inner subscript to single")
    print("  quotes; now the same quote nests freely")

    print("--- backslashes are allowed in the expression part ---")
    rows = ["a", "b", "c"]
    joined = f"{'\n'.join(rows)}"                 # '\n' inside the braces: was forbidden
    print(f"  f\"{{'\\n'.join(rows)}}\" produced {len(joined.splitlines())} lines")
    print("  a backslash escape like '\\n' inside the braces used to be a")
    print("  SyntaxError, forcing an awkward temporary variable. now the escape")
    print("  works directly in the expression")

    print("--- arbitrary nesting of f-strings ---")
    width = 8
    value = 42
    nested = f"{f'{value:>{width}}'}"             # an f-string inside an f-string
    print(f"  nested f-string result : {nested!r}   (right-aligned in {width})")
    print("  f-strings nest to any depth now - here an inner f-string computes a")
    print("  width-aligned value that the outer one embeds. the old sub-parser")
    print("  choked on deep nesting; the real grammar does not")

    print("--- multi-line expressions inside the braces ---")
    numbers = [1, 2, 3, 4, 5]
    summary = f"{
        sum(n for n in numbers if n % 2 == 0)
    }"                                           # the expression spans lines
    print(f"  a multi-line f-string expression summed evens to : {summary}")
    print("  the expression between the braces can now span multiple physical")
    print("  lines and be laid out for readability - impossible under the old")
    print("  single-line-only f-string parser")

    print("--- it is the SAME formatting, just without the parse limits ---")
    price = 1234.5
    print(f"  a normal f-string still works exactly as before : {price:,.2f}")
    print("  PEP 701 changed only what the PARSER accepts inside the braces, not")
    print("  what f-strings MEAN. every old f-string still behaves identically;")
    print("  the new forms are additions, not changes (Chapter 246's mini-language")
    print("  is untouched)")

    print("--- the constraint answered ---")
    print("  f-strings were parsed by a separate, restricted sub-parser that")
    print("  banned same-quote reuse, backslashes, comments, and deep nesting.")
    print("  PEP 701 (3.12) folded them into the real PEG grammar, so the braces")
    print("  accept ANY valid expression. the arbitrary limits are gone; the")
    print("  meaning is unchanged")


if __name__ == "__main__":
    main()
