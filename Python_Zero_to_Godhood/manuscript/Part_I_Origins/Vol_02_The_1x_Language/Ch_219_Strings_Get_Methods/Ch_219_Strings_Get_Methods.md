# Chapter 9: Strings Get Methods

The 1.x line closes with a change small in code and large in how Python reads: in **Python 1.6 (2000)**, string operations moved from the `string` *module* onto the `str` *type* as methods. Where early Python wrote `string.upper(s)`, `string.split(s, sep)`, and `string.join(words, sep)`, importing a module to operate on a string, modern Python writes `s.upper()`, `s.split(sep)`, and `sep.join(words)`, the operation living on the object it operates on.

The constraint was a mismatch with the founding decision. Chapter 4 established that everything is an object, and an operation on an object belongs *on* the object, `list.append` mutates the list it is called on, `dict.get` reads the dict it is called on. Strings were the anomaly: their operations lived in a separate module, so `string.upper(s)` violated the "operation on the object" model that the rest of the language followed. Python 1.6 fixed the anomaly by making string operations methods, which also enabled *chaining* (`s.strip().split().title()` reads as a pipeline) and made string code read as operations on a value rather than function calls on an argument. The `string` module's common functions were deprecated and removed by Python 3.

This is the volume's closing note on how the 1.x line turned the founding decisions into idiom: consistency was pursued release by release, and even string operations were brought into the "everything is an object" fold.

## Section index

- **9.1** The constraint: strings were the object-model anomaly
- **9.2** Operations on the object, not in a module
- **9.3** join on the separator, and why it surprises
- **9.4** Chaining: the readability the method form unlocked
- **9.5** Where the operations belong: the str type as an interface
- **9.6** Edges: the method form's own subtleties
- **9.7** Connections
- **9.8** Exercises
- **9.9** Summary and cross-references

Listings live under `code/ch219/` and are re-executed by `make verify` on the verification interpreters.

---

## 9.1 The constraint: strings were the object-model anomaly

By the late 1990s Python's object model was consistent almost everywhere: you called `list.append(x)`, `dict.keys()`, `file.read()`, methods on the objects, because "everything is an object" (Chapter 4) meant operations lived on the values they operated on. Strings broke the pattern. String operations were functions in the `string` module: `string.upper(s)`, `string.strip(s)`, `string.split(s, sep)`. To uppercase a string you imported a module and passed the string *as an argument*, exactly the C-style "function on data" model that the rest of Python had left behind.

The mismatch was not merely aesthetic. It meant string code read differently from all other code (function-call style, not method style); it prevented chaining (you could not write `s.strip().upper()` because there were no methods to chain); and it required an import for the most basic operations. As Python matured and its object-oriented consistency became a selling point, the string anomaly stood out. Python 1.6 resolved it by adding the operations as methods on `str`, bringing strings into the same model as every other object, which is the constraint this chapter's release answered.

---

## 9.2 Operations on the object, not in a module

```python
# code/ch219/l01_strings_get_methods.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- string operations are methods on the str object ---
  s.strip()          : 'Trade: ACME buy 100'
  s.upper()          : '  TRADE: ACME BUY 100  '
  s.split()          : ['Trade:', 'ACME', 'buy', '100']
  s.replace('buy','sell') : 'Trade: ACME sell 100'
```

**The operation lives on the string, which is Chapter 4's decision applied to text.**
`s.strip()`, `s.upper()`, `s.split()`, `s.replace(...)`, each is a method called *on* the string `s`, returning a new string (strings are immutable, Deep A). This is the object model made consistent: just as `list.append` operates on its list, `str.upper` operates on its string, and text stopped being the one type whose operations lived elsewhere. The change is why modern string code reads uniformly with the rest of Python, `s.upper()` has the same shape as `lst.sort()` and `d.get(k)`, and a reader who knows the method-call model reads string code with no special case.

**Returning new strings, not mutating, is the other half of the model.**
`s.upper()` does not change `s`; it returns a new uppercased string, because strings are immutable (Deep A, Chapter 89 measures why immutability enables sharing and interning). This is a deliberate consequence of the object model: a string's methods are *queries and transforms*, not mutations, so `s.strip()` gives you a new stripped string and leaves `s` alone. Code that expects `s.strip()` to modify `s` in place (a common newcomer error) misreads the immutability, and the method-returns-new-string pattern is uniform across all string operations.

---

## 9.3 join on the separator, and why it surprises

```text
--- join is a method on the SEPARATOR, which surprises newcomers ---
  ','.join(words)  : 'ACME,buy,100'
  ' '.join(words)  : 'ACME buy 100'
```

**`join` is a method on the separator, `sep.join(iterable)`, which is the single most-surprising string method and also the correct design.**
Newcomers expect `words.join(',')` (join the list with a comma), but the method is `','.join(words)` (the comma joins the words). The reason is that `join` is a *string* operation, it produces a string, and the object that knows how to stitch pieces together is the *separator string*, not the list. The separator is applied between elements, so it owns the operation, and the argument can be *any iterable of strings* (a list, a generator, a tuple), which a list method could not accept as generally. The design is right and the surprise is real, and it is one of Python's most-explained gotchas precisely because the object-model logic (the operation belongs on the string that does the work) is not the newcomer's first intuition.

**And `join` is the efficient way to build strings, which Chapter 74 owns.**
`','.join(parts)` builds the result in one pass, where `result = ""; for p in parts: result += p + ","` is quadratic (each `+=` copies the growing string, Chapter 74's accumulation lesson). So `join` is not just idiomatic but *efficient*, and the method-on-separator form is how Python expresses "stitch these pieces together in one allocation". The surprise pays for itself: once you know `sep.join(iterable)`, you have the fast string-building primitive.

---

## 9.4 Chaining: the readability the method form unlocked

```text
--- methods chain, which the module form could not do cleanly ---
  raw.strip().split(',') then strip each : ['ACME', 'buy', '100']
  chained: lower().replace().title()     : 'Acme Buy 100'
```

**Methods chain left-to-right, and that reads as a pipeline where the module form read inside-out.**
`"ACME-BUY-100".lower().replace("-", " ").title()` reads as a sequence of transforms: lowercase, then replace hyphens, then title-case, each applied to the result of the last, left to right, as you would describe the operation aloud. The equivalent in the `string` module, `string.title(string.replace(string.lower(s), "-", " "))`, reads *inside-out*: you must find the innermost call and work outward to understand the order. The method form made string processing a readable chain, which is "readability counts" (Chapter 3) realised in the string API, and it is why string-transformation code in modern Python is a fluent sequence rather than a nest of function calls.

**Chaining is a consequence of methods returning the object type.**
`s.lower()` returns a `str`, which has a `.replace` method, which returns a `str`, which has a `.title` method, the chain works because each method returns a value of the type whose methods continue the chain. This is a general pattern (fluent interfaces, builder patterns) that the method form enables and the module form cannot: functions returning values can be nested but not chained, because there is no object to call the next operation on. The 1.6 change gave strings the chainable, fluent style that reads as a pipeline.

---

## 9.5 Where the operations belong: the str type as an interface

```text
--- the str type is where the operations belong ---
  str has 47 public methods
  a few: ['capitalize', 'casefold', 'center', 'count', 'encode', 'endswith']
```

**Putting the operations on `str` makes the type its own documentation and its own discoverable interface.**
`str` has 47 public methods, and they *are* the string interface: `dir(str)` lists them, autocomplete offers them after a dot, and the type's documentation is the operations' documentation. A newcomer discovers `casefold`, `center`, `count`, and `encode` by typing `s.` and looking, where the module form hid them in `string`'s namespace, requiring the programmer to know the module existed and to read its docs separately. Methods-on-the-type is *discoverable* in a way module functions are not, and discoverability is a real ergonomic advantage of the object model (which Deep S's introspection tools amplify).

**And subclasses inherit the interface, which the module form could not offer.**
Because `str` is subclassable (Chapter 4), a custom string type inherits all 47 methods for free, `class Symbol(str)` gets `.upper()`, `.split()`, and the rest without redefinition, and can override or add. The module form gave no such inheritance: `string.upper` took a `str`, and a subclass had to hope the module's functions accepted it. Methods on the type participate in the object model's inheritance, so string operations compose with subclassing, which is the object-model consistency the 1.6 change completed for text.

---

## 9.6 Edges: the method form's own subtleties

**`join` on a non-string element raises, and the message confuses.**
`','.join([1, 2, 3])` raises `TypeError` because `join` requires an iterable of *strings*; the elements must be pre-converted (`','.join(map(str, nums))`). The error is common and its cause (join does not stringify) is a frequent trip-up, the method operates on strings, so its inputs must already be strings.

**Some `string` module constants survived the migration.**
`string.ascii_letters`, `string.digits`, and `string.punctuation` are still in the `string` module, because they are *data*, not operations, and data does not belong as a method on `str`. The migration moved *operations* to methods and left *constants* in the module, a clean division that the modern `string` module reflects, it is now a small module of constants and a couple of helpers (`Template`, `Formatter`), not the operation library it was.

**Immutability means chained methods allocate at each step.**
`s.lower().replace(...).title()` creates three intermediate strings, each method returns a new string (§9.2), so a long chain over a large string allocates repeatedly (Chapter 89's memory arithmetic). For hot paths over large text, this is a real cost, and the fix is the same as always: build once (a single pass, a `join`, or a `str.translate` for character-level maps) rather than chaining many transforms. The readability of chaining trades against allocation, the usual Deep K tension.

**And the method form does not make strings mutable.**
No string method changes its string; `s.replace(a, b)` returns a new string and leaves `s` unchanged, so `s.replace(a, b)` *without using the result* is a no-op bug (the result is discarded). This is the immutability edge: string methods are transforms that return, not mutations that modify, and forgetting to capture the return is a silent error the type's immutability guarantees.

---

## 9.7 Connections

**Backward.**
The object model that made methods-on-the-type the right design is Chapter 4; the values (consistency, readability) that motivated the migration are Chapter 3; the PyObject and immutability that shape string methods are Chapter 6 (this volume) and Deep A.

**Forward.**
Efficient string building (`join` over `+=`) is Chapter 74 (Deep H); the case model behind `casefold`/`lower` and Unicode string operations is Deep D; string formatting (`%`, `.format`, f-strings) is Chapter 12; the `str` type's memory and the boxing of characters are Chapter 89; introspection that makes methods discoverable is Deep S.

**Across books.**
Method-on-the-type is universal object-oriented design, **Book I**'s C++ `std::string` has methods too, though its free-function algorithms (`std::transform`) coexist with them the way Python's `str.translate` coexists with method chains. The shared system's text handling (parsing order messages, formatting responses) uses string methods on the Python side for exactly the readability the 1.6 migration bought.

---

## 9.8 Exercises

**1. Migrate module-style code.** Take five `string.func(s, ...)`-style operations (from old code or reconstructed) and rewrite each as a method chain; note where chaining improves readability and where it does not.

**2. Explain join to a newcomer.** Write the two-sentence explanation of why `join` is `sep.join(iterable)` and not `iterable.join(sep)`, grounded in "the operation belongs on the object that does the work" and "the argument can be any iterable".

**3. Find the discarded-result bug.** Write `s.replace(a, b)` without using the result (the no-op bug); explain how immutability guarantees the original is unchanged and how a linter catches the discarded return.

**4. Measure the chain cost.** For a chain of five string transforms over a 1 MB string, measure the allocation with `tracemalloc` (Chapter 89); then rewrite as a single `str.translate` or one-pass transform and compare. Report the readability-vs-allocation trade.

**5. The design question.** Python moved operations to methods but left constants (`string.digits`) in the module. Argue whether this operation-vs-data division is the right criterion for what belongs on a type versus in a module, and find one standard-library type where the division is drawn differently, with reasons.

---

## 9.9 Summary and cross-references

- **Python 1.6 (2000) moved string operations from the `string` module onto the `str` type as methods** (`s.upper()` for `string.upper(s)`), resolving strings' status as the object-model anomaly, an operation on an object belongs on the object (Chapter 4).
- **`join` is a method on the separator** (`sep.join(iterable)`), which surprises newcomers but is correct (the separator does the stitching, the argument is any iterable) and efficient (one-pass building, Chapter 74, not quadratic `+=`).
- **Methods chain left-to-right** as a readable pipeline where the module form read inside-out, and chaining works because each method returns a `str` whose methods continue the chain, "readability counts" in the string API.
- **The operations on `str` are its discoverable, inheritable interface**: `dir(str)`/autocomplete find them, subclasses (Chapter 4) inherit them, where module functions were neither discoverable nor inherited.
- **The edges are immutability's**: methods return new strings (a discarded result is a no-op bug), chains allocate per step (Chapter 89), `join` needs string elements, and `string`'s data constants stayed in the module.

**Cross-references.** The object model → Chapter 4. Consistency and readability values → Chapter 3. Immutability and the PyObject → Chapter 6, Deep A. Efficient string building → Chapter 74. Unicode string operations and case → Deep D. String formatting → Chapter 12. Memory → Chapter 89. Introspection → Deep S.
