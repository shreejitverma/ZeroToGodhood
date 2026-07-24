# Chapter 25: Template Strings (Python 3.14)

Chapter 12 ended its f-string section with a warning: never build SQL, HTML, or a shell command from an
f-string with untrusted data, because f-strings interpolate, they do not escape. That warning was a
dead end. It told you what not to do but offered no in-language alternative, because the moment an
f-string runs, the untrusted value is already spliced into a finished string and the damage, an
injected `<script>` tag or a `'; DROP TABLE`, is done. The only defenses were external: parameterized
queries, template engines, manual escaping, all of which mean *not* using string interpolation for the
thing string interpolation is for.

Python 3.14 closes that gap. **PEP 750** adds *template strings*, `t"..."`, which look exactly like
f-strings but produce a `Template` *object* instead of a `str`. The template keeps the literal parts and
the interpolated values *separate*, so a processor can escape or validate each value before it becomes
part of a string. This is the injection-safe interpolation primitive f-strings could never be, and it is
the natural close to the ergonomics-and-typing arc: f-strings (Chapter 12) made interpolation pleasant;
t-strings make it safe.

> **Version note.** Template strings are Python 3.14 (PEP 750), with the `string.templatelib` module.
> This chapter's listings are gated `# requires: 3.14+` and verified on the 3.14 interpreter; on 3.13
> they are reported skipped.

## Section index

- **25.1** The problem: f-strings interpolate but cannot escape
- **25.2** `Template`: literals and values, kept apart
- **25.3** Writing a processor: safe-by-construction interpolation
- **25.4** t-strings versus f-strings
- **25.5** Edges and failure modes
- **25.6** Connections
- **25.7** Exercises
- **25.8** Summary and cross-references

Listings live under `code/ch025/` and are re-executed by `make verify` on the 3.14 interpreter.

---

## 25.1 The problem: f-strings interpolate but cannot escape

An f-string produces a `str`, and it produces it *eagerly*: `f"<p>{user}</p>"` evaluates `user`,
converts it to a string, and concatenates it with the literal parts, all before you get the result. By
the time you hold the string, there is no way to tell which characters came from the trusted template
(`<p>`, `</p>`) and which came from the untrusted interpolation (`user`). They are the same string.

That is why every injection defense has to happen *outside* the interpolation: a database driver's
parameter binding, an HTML template engine's autoescaping, `shlex.quote` for a shell. Each of them
exists precisely because the language's own interpolation, the f-string, cannot be made safe. The
untrusted value and the trusted template are fused too early.

The fix is to *not* produce a string. Keep the parts separate, and hand them to something that knows
how to combine them safely for the target language.

---

## 25.2 `Template`: literals and values, kept apart

A t-string produces a `Template`, an object that holds the literal string segments and the interpolated
values as separate sequences:

```python
# code/ch025/l01_template_strings.py   # requires: 3.14+
from string.templatelib import Template
name = "world"
count = 42
t = t"Hello {name}, you have {count} messages"
```

Verified output (CPython 3.14.6):

```text
--- a t-string produces a Template, not a str ---
  type(t)         : Template
  isinstance(t, str): False
--- the literal parts and the interpolated values are kept separate ---
  t.strings : ('Hello ', ', you have ', ' messages')
  t.values  : ('world', 42)
--- each interpolation carries its expression text and format spec ---
  expression='count' value=42 format_spec='04d'
```

The `Template` is *not* a `str`. Its `strings` are the literal segments (`'Hello '`, `', you have '`,
`' messages'`) and its `values` are the interpolated results (`'world'`, `42`), alternating. And each
interpolation is a rich object carrying not just the value but the *expression text* (`'count'`) and the
*format spec* (`'04d'`), so a processor can use the value, report the source expression in an error, or
apply the format itself. The template deferred the combination; nothing has been turned into a string
yet, and that deferral is the whole feature.

---

## 25.3 Writing a processor: safe-by-construction interpolation

A processor walks the template's alternating literals and interpolations, passing the literal template
text through untouched and escaping each interpolated value:

```python
# code/ch025/l02_safe_processing.py   # requires: 3.14+
def render_html(template: Template) -> str:
    parts = []
    for item in template:
        if isinstance(item, Interpolation):
            parts.append(html_module.escape(str(item.value)))   # untrusted -> escaped
        else:
            parts.append(item)                                   # literal template text
    return "".join(parts)
```

Verified output (CPython 3.14.6):

```text
--- an f-string would splice the script tag in verbatim (unsafe) ---
  f-string result: <p><script>alert('xss')</script></p>
--- the t-string processor escapes the interpolated value ---
  t-string result: <p>&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;</p>
```

The f-string spliced the `<script>` tag in verbatim, the classic XSS. The t-string processor escaped it,
because it could tell the literal `<p>` (from the template, trusted) from the interpolated `user_input`
(untrusted, escaped). That distinction, invisible in an f-string's finished string, is preserved in the
template and is exactly what makes safe interpolation possible. The same pattern gives safe SQL (bind
each interpolated value as a query parameter rather than concatenating it) and safe shell (quote each
argument). A library exposes one processor, `html(t"...")` or `sql(t"...")`, and the call site writes
interpolation that looks like an f-string but cannot inject.

---

## 25.4 t-strings versus f-strings

f-strings and t-strings share a syntax and split on *when* and *whether* they produce a string:

- **f-string** (`f"..."`, Chapter 12): interpolates *eagerly* into a finished `str`. Fastest and most
  convenient for trusted, display-only text (logging aside, per Chapter 12's eager-evaluation trap). It
  cannot be made injection-safe, because the value and the template fuse before you can act.
- **t-string** (`t"..."`, this chapter): produces a `Template` that keeps literals and values *separate*
  for a processor to combine safely. The right tool whenever an interpolated value crosses a boundary
  where its characters have meaning, SQL, HTML, shell, a URL, a log format that a SIEM parses.

The rule: **f-strings for trusted display text, t-strings whenever untrusted or structured data is
interpolated into a target language.** A t-string is not a drop-in faster f-string; it is a different
tool with a required processing step, and that required step is the point, it is where the safety lives.
Do not reach for a t-string for a plain display string; do not reach for an f-string for a query.

---

## 25.5 Edges and failure modes

**Using a `Template` where a `str` is expected.** A `Template` is not a `str` (§25.2). Passing `t"..."`
to something expecting a string, `print`, string concatenation, a function typed `str`, fails or
misbehaves until you run it through a processor. The processing step is mandatory.

**Forgetting to process.** A t-string with no processor is inert; its interpolated values are never
escaped or combined. If a t-string reaches output unprocessed, either it does nothing useful or a naive
`str()` of it defeats the safety. Always pair a t-string with its processor at the boundary.

**A processor that does not escape.** The safety is in the *processor*, not the t-string. A processor
that concatenates values without escaping is exactly as unsafe as an f-string. t-strings *enable* safe
interpolation; they do not enforce it. Use a vetted processor.

**f-string habits.** Reaching for `t"..."` for ordinary display text adds a required processing step for
no benefit. Match the tool to the target: display is f-strings.

**Cross-version code.** `t"..."` is a `SyntaxError` before 3.14. Code that must run on older
interpreters cannot use it; there is no `__future__` import. Guard by version or keep to f-strings plus
external escaping until 3.14 is your floor.

---

## 25.6 Connections

**Backward.** f-strings, their eager interpolation, and the injection warning this chapter answers are
Chapter 12. The `__match_args__`-style structured access to a template's parts echoes the destructuring
of Chapter 15. The processing loop over interpolations is ordinary iteration (Chapter 9).

**Forward.** The security treatment of injection, `pickle` as RCE, and safe interpolation across
boundaries is **Deep O**. String and text processing in full, and the codecs, are **Deep P**.

**Across books.** t-strings are how Book II safely interpolates untrusted data at every boundary it
shares. A retrieval service in **Book III** builds prompts and queries from user input; a t-string
processor that escapes or delimits each interpolated field is the safe way to assemble them, where an
f-string would risk prompt or query injection. A command sent to a **Book I** subprocess is built with a
shell-quoting t-string processor. **Deep O** owns the security methodology; this chapter is the language
primitive that makes safe-by-construction interpolation possible at those seams.

---

## 25.7 Exercises

**1. Inspect a template.** Build a t-string with three interpolations of different types and print its
`strings`, `values`, and `interpolations`. Confirm `len(strings) == len(values) + 1` and explain why the
literal segments always outnumber the values by one.

**2. Write a SQL processor.** Write a processor that turns a t-string into a parameterized query: the
literal parts become the query text with `?` placeholders, and the values become the parameter tuple.
Show that `sql(t"select * from users where name = {user}")` produces a query and a separate parameter,
never a concatenated string. Explain why this is injection-proof.

**3. Break a bad processor.** Write a processor that concatenates values *without* escaping and show it is
exactly as unsafe as an f-string. Explain, using §25.5, why the safety lives in the processor and not the
t-string, and what a vetted library guarantees that a hand-rolled processor does not.

**4. Use the expression text.** Write a processor that, on a validation failure, reports *which
interpolated expression* was invalid using `Interpolation.expression`. Explain why an f-string could
never do this.

**5. The design question.** PEP 750 chose to make t-strings produce a `Template` object requiring a
processor, rather than adding an "autoescaping f-string" mode. Argue why the object-plus-processor design
is better than a magic escaping f-string. Your answer must address how a single escaping rule cannot fit
SQL, HTML, and shell at once, and how the processor design lets one syntax serve all three targets
safely.

---

## 25.8 Summary and cross-references

- **PEP 750 (3.14)** adds **template strings** (`t"..."`), which produce a **`Template`** object, not a
  `str`, keeping the literal segments (`strings`) and interpolated values (`values`) separate, with each
  interpolation carrying its expression text and format spec.
- Because the parts are separate, a **processor** can escape or validate each interpolated value before
  it becomes a string, making **safe-by-construction** SQL, HTML, and shell interpolation possible, the
  injection defense f-strings could never provide.
- **f-strings for trusted display text, t-strings whenever untrusted or structured data is interpolated
  into a target language.** The required processing step is where the safety lives; the t-string enables
  safety but a bad processor does not enforce it.
- A `Template` is not a `str`; it must be processed, and `t"..."` is a `SyntaxError` before 3.14.

**Cross-references.** f-strings and the injection warning → Chapter 12. Destructuring and iteration →
Chapters 9 and 15. Security and injection in depth → Deep O. Text processing and codecs → Deep P. The
safe-interpolation seams to Books I and III → Deep O.
