# Chapter 75: Name Lookup: Locals, Globals, and Builtins

A name in a Python function body looks like one thing in the source and is three different mechanisms at runtime, and which one you get is decided by the **compiler**, from syntax alone, before the function has ever run.
A **local** is an index into a flat array attached to the frame; there is no hashing, no string, no dictionary.
A **global** is a probe into the module's `globals()` dictionary.
A **builtin** is the *same* opcode as a global, which misses `globals()` and then probes the builtins mapping, so it is two probes rather than one.

That hierarchy is the origin of the oldest micro-optimization in the language, `_len = len` at the top of a hot function, and of one of its most common bugs, `UnboundLocalError` on a name that "obviously" refers to a module-level variable.
Both fall out of a single rule: **a name assigned anywhere in a function body is local everywhere in that body**, and the compiler freezes that decision into the code object.

**This is a Deep H performance chapter.**
It is about what the interpreter does to resolve a name, what each path costs on a modern specializing interpreter, and how much of the folklore around hoisting survives measurement.

## Section index

- **75.1** Three mechanisms, chosen at compile time
- **75.2** Hoisting, and the rule that bites
- **75.3** Measurement: what each lookup path costs
- **75.4** Edges and failure modes
- **75.5** Connections
- **75.6** Exercises
- **75.7** Summary and cross-references

Listings live under `code/ch156/` and are re-executed by `make verify` on both verification interpreters.

---

## 75.1 Three mechanisms, chosen at compile time

```python
# code/ch156/l01_name_lookup.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the compiler picks the mechanism per NAME, at compile time ---
  uses_local.total           LOAD_FAST*  (array slot)
  uses_local.range           LOAD_GLOBAL (dict probe)
  uses_global.MODULE_LEVEL   LOAD_GLOBAL (dict probe)
  uses_builtin.len           LOAD_GLOBAL (dict probe)
  hoisted._len               LOAD_FAST*  (array slot)
--- co_varnames is the indexed array; co_names is probed by string ---
  uses_local.co_varnames  : ('n', 'total', 'i')
  uses_local.co_names     : ('range',)
  uses_global.co_varnames : ('n',)
  uses_global.co_names    : ('MODULE_LEVEL',)
--- a builtin is not a separate opcode: LOAD_GLOBAL misses, then probes builtins ---
  uses_builtin.co_names   : ('len',)
  'len' in module globals : False
  'len' in builtins       : True
--- hoisting: bind it to a local once, then index the array ---
  hoisted.co_varnames     : ('xs', '_len', 'total', 'x')
  hoisted.co_names        : ('len',)
  hoisted(['ab', 'cde'])  : 5
--- the rule has teeth: assignment anywhere makes the name local everywhere ---
  MODULE_LEVEL at module scope        : 7
  looks_global_but_is_not.co_varnames : ('MODULE_LEVEL',)
  calling it raises                   : UnboundLocalError
--- the rule ---
  locals are array slots; globals and builtins are dict probes (two, for a
  builtin). In a hot loop, hoist the name you read repeatedly into a local
```

**The decision is static, and it is visible in the code object.**
`co_varnames` is the ordered tuple of local names; each one is an *index* into the frame's local-variable array, and `LOAD_FAST i` is an indexed read of that array. `co_names` is the tuple of names that must be resolved *by string* at runtime: globals, builtins, and attribute names. `uses_local` has `total` in `co_varnames` and `range` in `co_names`; `uses_global` has `MODULE_LEVEL` in `co_names`. Nothing about this is decided while the function runs. The compiler classified every name when it built the code object (Chapter 54), and the classification is permanent for the life of that code object.

**The senior-engineer contrast.**
In C or Rust a local is a stack slot and a global is a fixed address, both resolved by the linker; nothing is looked up by name at runtime. Python's local is genuinely the same shape as C's stack slot, an indexed read of a contiguous array, which is why it is fast. Its *global* is the surprise: a module global is a **dictionary entry**, mutable by anyone holding the module object, so the interpreter cannot bake in an address. The whole cost difference in this chapter comes from that one design choice, that module-level namespaces are ordinary mutable dictionaries.

**A builtin is not a third opcode.**
`len` compiles to `LOAD_GLOBAL`, exactly as `MODULE_LEVEL` does. The listing confirms `'len' in globals()` is `False` and `'len' in vars(builtins)` is `True`: at runtime `LOAD_GLOBAL` probes the module's `globals()` dict, **misses**, and then probes the builtins dict, where it hits. That is the entire "builtins scope" mechanism, a fallback probe inside one opcode. So a builtin read costs, in the unspecialized case, *two* dict lookups where a module global costs one, and that ordering, locals cheapest, then globals, then builtins, is what §75.3 measures.

There is a fourth path, `LOAD_DEREF`, for names captured from an enclosing function scope; a closure cell is a one-slot indirection, cheaper than a dict probe and dearer than an array slot. Closures are Deep F's subject and this chapter only notes the opcode exists.

---

## 75.2 Hoisting, and the rule that bites

**Hoisting is converting a `co_names` read into a `co_varnames` read.**
`hoisted` in the listing binds `_len = len` once, at function entry, and every read inside the loop is then `LOAD_FAST`. The code object shows the split cleanly: `len` still appears in `co_names` (the one binding read at entry), and `_len` appears in `co_varnames` (every read in the loop). One dict-shaped lookup replaces `n` of them.

This is the oldest performance idiom in Python and, on a modern interpreter, the most over-applied. §75.3 measures what it is actually worth now. The short version: for a module global on a warm site the saving is close to nothing, for a builtin it is real but small, and for an *attribute* (`self.method`, `np.array`) it is the largest of the three, which is the opposite of where the folklore points.

**The compile-time rule has teeth.**
`looks_global_but_is_not` reads `MODULE_LEVEL` on its first line and assigns it on its last. The read raises `UnboundLocalError`. The listing shows why in one line: `co_varnames` is `('MODULE_LEVEL',)`. Because the name is assigned *somewhere* in the body, the compiler classified it as local for the *entire* body, emitted `LOAD_FAST` for the read, and the array slot is still empty when that read executes.

This is not a special case or a wart bolted on; it is the direct consequence of deciding scope statically so that locals can be array slots. A language that let the same name be global on line 1 and local on line 3 could not compile either read to an index. The error message is the price of the array.

The two escape hatches are `global NAME` (bind the name in the module namespace, so every read and write is `LOAD_GLOBAL` / `STORE_GLOBAL`) and `nonlocal NAME` (bind it in the nearest enclosing function scope, so it becomes a cell). Both are declarations *to the compiler*, and both exist because the classification is otherwise inferred from assignment alone.

**What this means for how you write hot code.**
The useful form of the advice is not "hoist your globals". It is: **know which of your loop's reads are `co_names` reads, and hoist the ones that are both dict-shaped and executed per iteration.** `fn.__code__.co_names` is the list, and it is one line to print. A read that appears in `co_names` and runs a million times is a candidate; a read that runs once is not, and turning it into a local costs you a name for nothing.

---

## 75.3 Measurement: what each lookup path costs

**Methodology.** `code/ch156/bench_name_lookup.py`.
Four loops that differ in exactly one instruction, the opcode that reads a name, plus an `empty` row that measures the shared loop machinery. The loop body is **unrolled to 20 reads per iteration**; with one read per iteration the `FOR_ITER` and the store cost several times the read and the four rows come out indistinguishable. `min` of 15 batches, 2,000 calls per batch, 1,000 iterations per call.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| one name read | per read | vs local |
|---|---|---|
| local (array slot) | 3.2 ns | 1.00x |
| global (globals dict) | 3.3 ns | 1.02x |
| builtin (globals miss, builtins hit) | 3.8 ns | 1.18x |
| attribute (`obj.attr`) | 3.9 ns | 1.22x |

Figures are per read with the empty loop's cost subtracted, reproducible to about one decimal place across runs on this machine.

**The headline is that the global row is not slower.**
A module-global read costs, within measurement error, the same as a local read on 3.13. That is not because the dict probe is free; it is because there is no dict probe. Since 3.11 the specializing adaptive interpreter rewrites a warm `LOAD_GLOBAL` into `LOAD_GLOBAL_MODULE`, which caches the dict's *version tag* and the entry's index in the inline cache attached to the instruction. The steady-state work is: check the version tag, index the entry. That is a guard and an array read, which is why it lands next to `LOAD_FAST`. The mechanism is Chapter 76's subject.

**Builtins cost more, and for a structural reason.**
The builtin row is about 18% dearer. Its unspecialized form does two dict probes rather than one, and its *specialized* form (`LOAD_GLOBAL_BUILTIN`) must guard **two** dict versions, the module's and the builtins', because either one changing could change what `len` resolves to. Two guards instead of one is the residue that specialization cannot remove.

**Attribute access is the most expensive of the four**, at about 22% over a local, even fully specialized, because `LOAD_ATTR` guards the object's *type* in addition to the layout it caches. This is the number that should redirect the folklore: in a loop that reads `self.price` or `np.float64` a million times, the read worth hoisting is the attribute, not the global.

**What did not reproduce, and why it is not in the table.**
On 3.14.6 the same benchmark's *local* row would not stabilize on this machine: the minimum drifted between 1.3 ns and 2.5 ns across repeated runs, with relative standard deviation above 20%, while the other three rows held to within a few percent. By this book's rule, an unstable min is a benchmark that should not be cited, so no 3.14 ratio is given here. The suspected cause is worth naming even unmeasured: 3.14 introduced `LOAD_FAST_BORROW`, which reads a local *without* incrementing its reference count when the compiler can prove the borrow is safe, removing an atomic-capable increment/decrement pair from the hottest opcode in the interpreter. That is precisely the kind of change that would make the local row faster *and* more sensitive to the surrounding code. Confirming it needs two builds with identical flags, which this machine does not have.

**The practical conclusion.**
The hierarchy from §75.1, locals cheapest, globals next, builtins next, is still the right mental model of the *mechanism*, but on a warm site the specializing interpreter has compressed the first two rungs to nearly nothing. Hoisting a global out of a loop is now a rounding error; hoisting a builtin is worth about 18% of the read; hoisting an attribute is worth more than either. And all three are worth far less than not doing the lookup at all, which is what §75.2's advice really points at: the fastest name read is the one the loop does not perform.
**Book I**'s hot paths do not have this problem to solve, a C++ member access is an offset known at compile time, and that contrast is the honest framing for a Python hot loop: every name read in the inner loop is a guard the interpreter must re-check, and the way to win is to move the read out of the loop, not to make it marginally cheaper.

---

## 75.4 Edges and failure modes

**`UnboundLocalError` is a compile-time classification, not a runtime accident.** §75.2.
Assigning a name anywhere in a body makes it local everywhere in that body. Reading it before that assignment raises. Fix with `global` / `nonlocal`, or by not shadowing.

**`global` at module level is a no-op, and `nonlocal` at module level is a `SyntaxError`.**
`nonlocal` requires an enclosing *function* scope; there is no cell to bind to at module level.

**Class bodies do not create a closure scope.**
A name defined in a class body is not visible to methods defined in that body, because the class body executes in its own namespace which is *not* an enclosing function scope. Methods reading such a name get a global lookup and usually a `NameError`. This is a frequent surprise and belongs to the class-creation machinery (Deep C).

**`exec`, `eval`, and `locals()` do not add locals.**
Because the local array is sized at compile time, code executed by `exec` cannot introduce a new local into the enclosing function. Assignments inside `exec` land in the dict it is given, not in `co_varnames`. On 3.13+ `locals()` in a function returns an independent snapshot (PEP 667); mutating it does not write through to the array.

**Shadowing a builtin is legal and silent.**
`list = [1, 2]` at module level rebinds the name `list` for that module; every later `list(...)` in the module gets your list and a `TypeError`. Nothing warns. The lookup order made it possible, and the diagnostic is `co_names` plus the fact that `list` is now in `globals()`.

**The 3.14 opcode rename.** §75.3.
`LOAD_FAST` reads split into `LOAD_FAST` and `LOAD_FAST_BORROW` in 3.14, and superinstructions such as `LOAD_FAST_LOAD_FAST` and `STORE_FAST_LOAD_FAST` fuse two operations into one dispatch. Tools that pattern-match on `opname == "LOAD_FAST"` break across versions and across *positions within one version*. The listing collapses to families for exactly this reason. The book's verification queue carries an open entry for a full inventory of the 3.14 opcode renames; what is verified here is narrower and enough for this chapter, that on 3.14.6 the local reads in these functions are emitted as `LOAD_FAST_BORROW` and the fused forms, and that matching on the family is the only stable way to classify them.

**Hoisting changes semantics when the global can change.**
`_fn = some_global` captures the binding *at that moment*. If another thread, a decorator, a plugin, or a test's monkeypatch rebinds the module attribute afterwards, the hoisted local keeps the old object. That is usually what you want in a hot loop and occasionally a real bug; it is the reason `mock.patch` on a hoisted name does not take effect.

**Do not hoist for style.** §75.3.
`_len = len` in a function that runs once, or that calls `len` twice, buys nothing and costs a reader a name. The measurement is the justification, and it applies only to per-iteration reads in a loop that actually matters.

---

## 75.5 Connections

**Backward.**
The code object that holds `co_varnames` and `co_names`, and the frame that holds the local array, are Chapter 54. Function call overhead, which is what allocates that array, is Chapter 55. The compile-time nature of the decision is the same compiler pass that folds constants, Chapter 56.

**Forward.**
Specialization and inline caches, which are why the global row is not slower, are Chapter 76. Comprehension inlining, which changes which frame a comprehension's names live in, is Chapter 77. The dispatch loop that executes all of these opcodes is Chapter 78. Closures and cells (`LOAD_DEREF`) are Deep F. Attribute lookup semantics, as distinct from its cost, are Deep A. Class-body scoping is Deep C. Dictionary internals, which is what a namespace *is*, are Deep Q.

**Across books.**
The contrast that makes the cost model legible is **Book I**'s: a C++ member read is a compile-time offset and a C++ global is a link-time address, so neither is a lookup at all. Python pays for mutable namespaces with a guard per read, and the specializing interpreter's job is to make that guard as close to free as a guard can be. On the shared order-book system, the Python-side hot loop hoists the attribute reads it performs per tick and leaves module globals alone, which is what the measurement in §75.3 supports rather than what the folklore recommends.

---

## 75.6 Exercises

**1. Classify the names.** Take a function you have written that runs in a loop, print `fn.__code__.co_varnames` and `fn.__code__.co_names`, and say for each name in `co_names` whether it is read once or per iteration. Predict which hoists would pay before measuring.

**2. Reproduce the error.** Write a function that reads a module global on its first line and assigns it on its last. Explain, from `co_varnames`, why the read raises `UnboundLocalError` rather than reading the module value. Then fix it twice, once with `global` and once by renaming, and say which you would ship.

**3. Measure it yourself.** Reproduce §75.3. Then reduce `UNROLL` to 1 and re-run. Explain why the four rows collapse into each other, and what that says about microbenchmarks whose effect is smaller than their scaffolding.

**4. Find the guard.** Using the benchmark's structure, add a row that reads a *closure* variable (`LOAD_DEREF`) and place it in the hierarchy. Explain the result from the mechanism, a cell is one indirection with no guard.

**5. Break the specialization.** Write a loop that reads a module global while another part of the program rebinds a *different* module global on every iteration. Explain what happens to the dict version tag, and predict, then measure, the effect on the read. This is Chapter 76's subject arriving early.

**6. The design question.** Python could have made module globals immutable after import, which would allow the compiler to resolve them to indices exactly as it does locals. Argue both sides: what that would buy in the measurement of §75.3, and what it would cost in monkeypatching, plugin systems, circular-import repair, and interactive development.

---

## 75.7 Summary and cross-references

- A name read in a function body compiles to **one of three mechanisms**, chosen by the compiler from syntax alone: **local** (`LOAD_FAST` family, an indexed read of the frame's local array), **global** (`LOAD_GLOBAL`, a probe of the module's `globals()` dict), or **builtin** (the *same* `LOAD_GLOBAL`, which misses globals and then probes builtins).
- The decision is **frozen into the code object**: `co_varnames` is the indexed local array, `co_names` is the set of names resolved by string at runtime.
- **A name assigned anywhere in a body is local everywhere in that body.** Reading it before the assignment raises `UnboundLocalError`. This is the price of making locals array slots, and `global` / `nonlocal` are the declarations that override it.
- **Measured on 3.13.5:** local 3.2 ns, global 3.3 ns (**1.02x**), builtin 3.8 ns (**1.18x**), attribute 3.9 ns (**1.22x**) per read. The global row is not slower because 3.11+ **specializes** a warm `LOAD_GLOBAL` into a version-guarded inline cache; the builtin row keeps a residue because it must guard **two** dict versions.
- **The revised advice:** hoisting a module global out of a loop is a rounding error on a modern interpreter; hoisting a **builtin** is worth about 18% of the read; hoisting an **attribute** is worth the most. Best of all is not performing the lookup per iteration at all.
- **Edges:** class bodies are not closure scopes; `exec` cannot create locals; `locals()` is a snapshot on 3.13+ (PEP 667); shadowing a builtin is silent; hoisting captures a binding and defeats later monkeypatching; 3.14 split `LOAD_FAST` into `LOAD_FAST` / `LOAD_FAST_BORROW` and fuses superinstructions, so match on families, not names.

**Cross-references.** Code objects and frames → Chapter 54. Call overhead → Chapter 55. Compile-time decisions → Chapter 56. Specialization and inline caches → Chapter 76. Comprehension inlining → Chapter 77. The dispatch loop → Chapter 78. Closures and cells → Deep F. Attribute semantics → Deep A. Class-body scope → Deep C. Dict internals → Deep Q.
