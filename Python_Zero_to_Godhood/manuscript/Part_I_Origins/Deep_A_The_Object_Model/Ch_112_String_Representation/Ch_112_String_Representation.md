# Chapter 27: String Representation

This chapter closes Deep A on the object's public face: how it turns into text.
Python gives every object *two* string forms and a formatting hook, and keeps them deliberately separate, `__repr__` for the developer, `__str__` for the user, `__format__` for the field in an f-string.
The separation is not decoration.
A log line, a debugger, a container's contents, and a REPL echo all use `__repr__`; `print` and user-facing messages use `__str__`; and `f"{x}"` routes through `__format__`.
Confusing them produces the two everyday annoyances of Python objects: a list that prints as `[<Thing object at 0x104…>, …]` because nobody defined `__repr__`, and a `print(obj)` that dumps an unreadable debug string because the class defined only `__repr__` and the author wanted a friendly `__str__`.

The rule that falls out is short and worth stating first: **define `__repr__` for every class you expect to debug; define `__str__` only when users need a different, friendlier form.**
`__repr__` is the one that has fallbacks pointing *at* it (`__str__` and `__format__` both default to it), so it is the representation that is always reachable, and the one the tooling you debug with actually shows.

**This is the canonical home for object-to-text conversion.**
It uses Chapter 20 (`repr`, `str`, `format` are special-method dispatch), Chapter 19 (the default `__repr__`'s `0x…` address is the object's `id`), and hands the *grammar* of format specs (`:>10.2f`, the mini-language) and locale/i18n to **Deep D** (text) and **Deep Q** (string services).

## Section index

- **27.1** `__repr__` versus `__str__`: two forms, two audiences
- **27.2** `__format__` and the f-string conversion flags
- **27.3** Measurement: f-strings are the fastest formatting
- **27.4** Edges and failure modes
- **27.5** Connections
- **27.6** Exercises
- **27.7** Summary and cross-references

Listings live under `code/ch112/` and are re-executed by `make verify` on both verification interpreters.

---

## 27.1 `__repr__` versus `__str__`: two forms, two audiences

```python
# code/ch112/l01_repr_vs_str.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- repr() is dev-facing; str() is user-facing ---
  repr(b) : Both(unambiguous)
  str(b)  : a readable Both
--- __str__ falls back to __repr__ when not defined ---
  repr(o) : OnlyRepr(unambiguous)
  str(o)  : OnlyRepr(unambiguous)   (fell back to __repr__)
--- containers use __repr__ of their elements, even via str() ---
  str([b, b]) : [Both(unambiguous), Both(unambiguous)]   (list shows repr, not str)
--- print() uses str(); the values differ ---
  print(b) shows : a readable Both
--- with neither defined, the default __repr__ has a stable shape ---
  starts with '<' : True
  contains 'Plain object at 0x' : True
--- the rule ---
  define __repr__ always (unambiguous, for devs/logs/containers);
  define __str__ only when users need a different, readable form
```

`repr(x)` calls `__repr__`, the **unambiguous** representation aimed at a developer, and by convention it should be as close as possible to valid Python that recreates the object (`Point(1, 2)`, `datetime.date(2026, 7, 25)`), so that reading a log or a REPL echo tells you exactly what the object is.
`str(x)` calls `__str__`, the **readable** representation aimed at an end user, and `print` uses it.
`Both` shows them diverging: `repr(b)` is `Both(unambiguous)`, `str(b)` is `a readable Both`.

Three propagation rules make `__repr__` the more important of the two.
First, **`__str__` falls back to `__repr__`** when undefined: `OnlyRepr` defines only `__repr__`, and `str(o)` returns it.
So a class with just `__repr__` is fully usable, both `repr` and `str` work, whereas a class with just `__str__` still has the ugly default `__repr__`.
Second, **containers use `__repr__` of their elements**, even when the container itself is being `str`-ified: `str([b, b])` shows `Both(unambiguous)`, not the `str` form.
This is why a list of your objects prints readably only if you defined `__repr__`, `__str__` does not help inside a container.
Third, the **default `__repr__`** (when you define neither) has the shape `<module.Class object at 0x…>`, where the hex is the object's `id` (Chapter 19), useless for understanding the object's *value*.

Hence the rule: define `__repr__` on essentially every class you will debug (which is all of them), and add `__str__` only when the user-facing string genuinely differs from the developer-facing one.
For many classes a single good `__repr__` is all you need.

---

## 27.2 `__format__` and the f-string conversion flags

```python
# code/ch112/l02_format.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- conversion flags pick the method ---
  f'{b}'   (default/__format__ -> __str__) : Both(str)
  f'{b!s}' (force str)  : Both(str)
  f'{b!r}' (force repr) : Both(repr)
--- __format__ receives the spec after the colon ---
  f'{t}'    (empty spec) : 20.0C
  f'{t:f}'  (spec 'f')   : 68.0F
--- format() is the same protocol without an f-string ---
  format(t, 'f') : 68.0F
--- the rule ---
  f'{x}' and format() call __format__ (defaults to __str__); !s/!r/!a
  force str/repr/ascii; a format spec after ':' is passed to __format__
```

There is a *third* representation method, `__format__(self, spec)`, and it is the one `f"{x}"` and the built-in `format(x, spec)` actually call.
It receives the **format specification**, the text after the colon in `f"{x:spec}"`, and for an empty spec it defaults to `__str__`.
`Temperature.__format__` uses the spec to choose units: `f"{t}"` (empty spec) gives Celsius `20.0C`, `f"{t:f}"` gives Fahrenheit `68.0F`, and `format(t, "f")` is the identical protocol without an f-string.
This is how numeric types implement `f"{x:.2f}"` and `f"{x:>10}"`: the spec is a mini-language their `__format__` interprets.

The **conversion flags** `!s`, `!r`, `!a` override the method choice, bypassing `__format__`:

- `f"{x}"` calls `x.__format__("")` (defaults to `str`).
- `f"{x!s}"` forces `str(x)`.
- `f"{x!r}"` forces `repr(x)`, the most useful in practice, for debug output: `f"{value!r}"` shows the unambiguous form, quoting strings and revealing types.
- `f"{x!a}"` forces `ascii(x)` (repr with non-ASCII escaped).

`Both` shows `f"{b}"` and `f"{b!s}"` giving the `str` form and `f"{b!r}"` giving the `repr` form.
The practical takeaway: **use `!r` in log and debug f-strings** (`logger.debug(f"processing {item!r}")`), because it disambiguates `"5"` (a str) from `5` (an int) and shows exactly what you have, which the default `str` conversion hides.

---

## 27.3 Measurement: f-strings are the fastest formatting

**Methodology.** `code/ch112/bench_format.py`.
Building `"order-42"` four ways: an f-string, `str.format()`, `%`-formatting, and manual concatenation with `str()`.
`min` of 5 runs, 5,000,000 builds.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| build `"order-42"` | ns | vs f-string |
|---|---|---|
| f-string `f"{name}-{n}"` | 48.6 | 1.0x |
| `%`-formatting `"%s-%s" % (…)` | 52.8 | 1.1x |
| concatenation `name + "-" + str(n)` | 51.5 | 1.1x |
| `str.format()` `"{}-{}".format(…)` | 84.5 | **1.7x** |

The f-string is the fastest, and `str.format()` is the slowest at **1.7x** (1.6x on 3.14.6); `%`-formatting and manual concatenation land just behind the f-string.
The reason is *when the template is parsed*.
An f-string is parsed by the **compiler**, once, into formatting bytecode (`FORMAT_SIMPLE`/`FORMAT_WITH_SPEC` and the field conversions inline), so at runtime there is no template to interpret, just the conversions.
`str.format()` carries its template `"{}-{}"` as a runtime string and must **parse it on every call**, locate the fields, and dispatch through a method, that per-call parse is the extra 36 ns.
`%`-formatting and concatenation avoid the method dispatch and stay close to the f-string.

The recommendation is unambiguous and matches the readability recommendation, which is the nice case: **prefer f-strings.**
They are the fastest *and* the most readable (the values appear inline where they are used), so there is no trade to make for the common case of a template known at compile time.
`str.format()` earns its keep only when the template is *not* known at compile time, chosen at runtime from configuration, a translation table, or user input, because an f-string's template is fixed in the source and a `.format()` template can be a runtime value.
`%`-formatting is legacy (still used by the logging module's lazy `%s` interpolation, deliberately, so the format only happens if the message is emitted).
This closes Deep A on the same note it has sounded throughout: the ergonomic, readable default (here the f-string) is also the fast one, and you reach for the alternative only for a specific capability (a runtime template) it uniquely provides.

---

## 27.4 Edges and failure modes

**Define `__repr__`, not just `__str__`.** §27.1.
`__str__` falls back to `__repr__`, containers use `__repr__`, and the default `__repr__` is useless. A single good `__repr__` covers most needs; `__str__` is the optional extra.

**A `__repr__` that raises breaks debugging.**
If `__repr__` throws (an uninitialized attribute, a failing computation), then the debugger, the REPL, logging, and any container's `repr` all fail on the object, often masking the original error. Keep `__repr__` total and cheap; guard against half-constructed state.

**`eval(repr(x)) == x` is a goal, not a guarantee.**
The convention that `repr` is reconstructable holds for simple value types but not for objects with unreconstructable state (open files, connections). For those, use the `<Class: useful summary>` angle-bracket form (as the default does) rather than a misleading pseudo-constructor.

**`__format__` with a spec it does not understand should raise, not ignore.**
If your `__format__` receives a spec it cannot honour, raise `ValueError` (as built-ins do for `f"{5:q}"`), do not silently ignore it, or callers get wrong output with no signal. If you do not need custom specs, do not define `__format__`; the default forwards to `__str__` and rejects non-empty specs.

**`!r` versus `!s` in logs.** §27.2.
`f"{x}"` uses `str`, which can hide types (`"5"` vs `5`, `None` vs `"None"`). Use `!r` in debug/log output for unambiguity.

**`str.format()` re-parses its template every call.** §27.3.
In a hot loop, that per-call parse is real. Prefer f-strings; if the template must be dynamic, consider caching or restructuring.

**Do not eagerly format log messages.**
`logger.debug(f"{expensive!r}")` builds the string even when debug logging is off. `logger.debug("%r", expensive)` defers the formatting to the logging layer, which skips it if the level is disabled, one of the few places `%` interpolation is still the right choice.

**`__repr__` and `__str__` are looked up on the type.**
As with all special methods (Chapter 20), an instance-level `__repr__` is ignored. Define them on the class.

---

## 27.5 Connections

**Backward.**
`repr`, `str`, and `format` are special-method dispatch (Chapter 20), looked up on the type; the conversion flags and `__format__`'s default-to-`__str__` are that protocol's rules. The default `__repr__`'s `0x…` is the object's `id` and address (Chapter 19). This chapter is the last of Deep A, and it is the object's *output* side, complementing construction (Chapter 25) and the equality/ordering/truthiness that define its *behaviour* (Chapters 23, 24, 26).

**Forward.**
The format-spec mini-language (`[[fill]align][sign][#][0][width][,][.prec][type]`) and its numeric/`datetime` implementations, plus locale-aware and i18n formatting, are **Deep D** (text) and **Deep Q** (string services). `@dataclass`'s generated `__repr__` (which produces `Class(field=value, …)` for free) is a **Deep C** ergonomics topic and the modern way to get a good `__repr__` without writing one. `reprlib` (length-limited reprs for large structures) is **Deep Q**.

**Across books.**
Good `__repr__`s are an operational asset in **Book I**: every domain object, order, price level, fill, position, defines a `__repr__` that reads like its constructor, so a log line or a stack trace shows the actual values, not `<Order object at 0x…>`, which is the difference between diagnosing a production incident in minutes and in hours. The order-book system's objects use `__repr__` for logs and debugging and `!r` in every diagnostic f-string, and it prefers f-strings on its hot paths (the §27.3 result) while using the logging module's lazy `%s` for messages that may not be emitted, the §27.4 deferred-formatting discipline applied where message volume is high.

---

## 27.6 Exercises

**1. Two forms.** Reproduce §27.1: a class with distinct `__repr__` and `__str__`. Confirm `repr`, `str`, `print`, and a list of them each pick the right one. Then remove `__str__` and show everything still works via the fallback. Explain why a list uses `__repr__`.

**2. Reconstructable repr.** Write a `Point` whose `__repr__` returns `Point(1, 2)` such that `eval(repr(p))` recreates it. Then write a `Connection` where that is impossible and use the angle-bracket summary form instead. Explain the convention and its limit.

**3. Custom format.** Reproduce §27.2's `Temperature`: a `__format__` honouring a spec (`"c"`/`"f"`/`"k"`). Raise `ValueError` for an unknown spec. Show `f"{t:f}"` and `format(t, "k")` both work, and `f"{t:q}"` raises.

**4. Measure formatting.** Reproduce §27.3. Then add a case where the template is chosen at runtime (from a dict) and show why an f-string cannot express it while `str.format()` can. Argue when each is correct, using both the speed result and the runtime-template need.

**5. The design question.** Python has three representation methods (`__repr__`, `__str__`, `__format__`) where a language could have one. Argue what the split buys, using the developer-versus-user audience (§27.1) and the format-spec mini-language (§27.2). Then argue the cost (three methods to keep consistent, the fallbacks to remember) and whether `@dataclass`'s auto-`__repr__` resolves it for the common case.

---

## 27.7 Summary and cross-references

- An object has two string forms and a formatting hook: **`__repr__`** (unambiguous, developer-facing, used by `repr`, the REPL, and containers), **`__str__`** (readable, user-facing, used by `str`/`print`), and **`__format__`** (used by `f"{x}"` and `format`).
- **`__str__` and `__format__` fall back to `__repr__`**; **containers use `__repr__`** of elements; the default `__repr__` is the useless `<Class object at 0x…>`. So **define `__repr__` always**; add `__str__` only when the user form differs.
- **f-string conversion flags** pick the method: `f"{x}"` -> `__format__` (defaults to `str`), `!s` -> `str`, `!r` -> `repr`, `!a` -> `ascii`. Use **`!r` in debug/log output** for unambiguity.
- **Measured:** f-strings are the fastest formatting; `str.format()` is **1.7x** slower (84.5 vs 48.6 ns) because it re-parses its template per call, while an f-string is parsed once at compile time. Prefer f-strings; use `str.format()` only for runtime-chosen templates, and lazy `%s` for deferred logging.
- **Edges:** keep `__repr__` total and cheap (a raising `__repr__` breaks debugging); `__format__` should raise on specs it cannot honour; do not eagerly format disabled log messages.

**Cross-references.** `repr`/`str`/`format` as special-method dispatch → Chapter 20. The default `__repr__`'s address as `id` → Chapter 19. The rest of the object model (construction, equality, ordering, truthiness) → Chapters 25, 23, 24, 26. The format-spec mini-language, locale, i18n → Deep D, Deep Q. `@dataclass` auto-`__repr__` → Deep C.
