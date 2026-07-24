# Chapter 2: Inception and the Executable Pipeline (Python 1.0-1.6)

A senior engineer arriving from C++ writes this, expecting a deep copy, and ships a bug:

```python
config = {"retries": 3}
defaults = config          # "save the defaults before I mutate"
config["retries"] = 10
# defaults["retries"] is now 10, not 3
```

The bug is not a typo. It is a wrong mental model of what a name is, and it survives code review
because the code looks obviously correct to anyone thinking in terms of variables-as-storage. Python
does not have variables in that sense. It has names bound to objects, and until that distinction is
in muscle memory it will keep producing bugs that the type checker cannot catch and the reviewer
cannot see.

This chapter builds the correct model from the bottom. It follows one line of source from text to
result through the five stages of CPython's pipeline, and it establishes the vocabulary that every
later chapter assumes: names, bindings, scopes, cells, code objects, frames, opcodes. It anchors in
Python's 1.x origins because the decisions made then, names as bindings, everything-is-an-object, a
static scope-analysis pass before execution, still govern how CPython 3.14 behaves today. Chapter 1
covered why Guido built the language; this chapter is the machine he built.

## Section index

- **2.1** Names are bindings, not storage
- **2.2** The execution pipeline, end to end
- **2.3** Parser evolution: LL(1) to PEG
- **2.4** The symbol table and static scope classification
- **2.5** Closures and cell objects
- **2.6** `PyCodeObject`: the compiled blueprint
- **2.7** The virtual machine: frames and the evaluation loop
- **2.8** Measurement: locals, globals, and a piece of overturned folklore
- **2.9** Edges and failure modes
- **2.10** Connections
- **2.11** Exercises
- **2.12** Summary and cross-references

Listings live under `code/ch001/` and are re-executed by `make verify` on both verification
interpreters.

---

## 2.1 Names are bindings, not storage

**The model.** A Python name lives in a namespace, a mapping from `str` to object. Assignment binds
the name to an object; it never copies the object and never mutates whatever the name referred to
before. Every object carries at least a reference count and a type pointer (Chapter 19 dissects the
header). So assignment is a constant two-step: bind the name, and increment the target's refcount.

The bug in the introduction is this model applied correctly to code written as if the other model
were true:

```python
# code/ch001/l01_names_are_bindings.py
a = [1, 2, 3]
b = a               # b is NOT a copy; a and b name the same list
b.append(4)
```

Verified output (CPython 3.13.5):

```text
after b.append(4):
  a       = [1, 2, 3, 4]
  b       = [1, 2, 3, 4]
  a is b  = True
  a == b  = True
```

`b.append(4)` is visible through `a` because there was only ever one list. Then the crucial contrast,
rebinding versus mutating:

```text
contrast: rebinding a name does not touch the object or the other name
  a       = [1, 2, 3, 4]
  c       = [1, 2, 3, 4, 5]
  a is c  = False
```

`c = c + [5]` builds a new list and binds `c` to it. `a` is untouched, because rebinding a name
changes the name, not the object. Mutating through a name (`append`) changes the shared object;
rebinding a name (`=`) changes only that one edge. Every copy-versus-alias surprise in Python is that
one distinction.

**The senior-engineer contrast.** This is exactly where systems intuition misleads:

| Concept | C / C++ | Java | Python (CPython) |
|---|---|---|---|
| What a variable *is* | typed storage at an address | a typed slot holding a primitive or a reference | a name bound to an object; the name has no type |
| `a = b` | copies bytes per the declared type | copies a primitive, or copies a reference | binds `a` to the same object `b` names; no copy |
| Type belongs to | the variable, fixed at compile time | the variable | the **object**, not the name |
| Lifetime | scope / `new`/`delete` / RAII | tracing GC | refcount to immediate free, plus a cyclic collector (Chapter 3) |

`is` compares identity, `==` compares value. In C, `a == b` on pointers already is identity, so the
language needs no separate operator. Python needs two because a name and an object are two different
things. Fix the model here and most of the language's surprises stop being surprising: **a Python
program is a graph of objects, and names are labelled edges into it.**

---

## 2.2 The execution pipeline, end to end

**Why this exists.** Python feels interpreted, you type a line and it runs, but nothing executes
until it has been compiled to bytecode. Knowing the pipeline tells you where each error is produced
(a `SyntaxError` cannot happen at runtime; a `NameError` cannot happen at compile time) and why
certain constructs are fast or slow.

Text to result is five stages:

```text
[ source text ]
      | tokenizer  (Parser/tokenizer.c): token stream, including INDENT/DEDENT
      v
[ token stream ]
      | parser  (Parser/, PEG since 3.9): builds the Abstract Syntax Tree
      v
[   AST   ]  ( the ast module exposes this tree )
      | symbol-table pass  (Python/symtable.c): classifies every name into a scope
      v
[ symbol table ]
      | compiler  (Python/compile.c): emits bytecode + metadata
      v
[ PyCodeObject ]   ( immutable: bytecode, constants, names, flags )
      | evaluation loop  (Python/ceval.c): runs per frame
      v
[  result  ]
```

The first four stages are ahead-of-time compilation; only the last is interpretation. Each boundary
is observable from the standard library: `tokenize` for stage 1 (Chapter 1 showed its INDENT/DEDENT
output), `ast` for stages 2-3, `symtable` for stage 4, `dis` for stage 5's input, and the running
program for the loop. The rest of this chapter takes each in turn.

---

## 2.3 Parser evolution: LL(1) to PEG (PEP 617)

**Why this exists.** For most of its life CPython used a hand-tunable **LL(1)** parser: **L**eft-to-
right scan, **L**eftmost derivation, **1** token of lookahead. It is fast and simple but structurally
limited, and its limits shaped the grammar, and therefore the language, for two decades. **PEP 617
(the PEG parser)** replaced it in Python 3.9 (Chapter 14).

**The LL(1) limitation: left recursion.** A top-down LL(1) parser cannot directly handle a left-
recursive rule, one whose right-hand side begins with the non-terminal itself:

$$A \rightarrow A\,\alpha \;\mid\; \beta$$

Asked to expand $A$, it would expand $A$ again before consuming input, recursing forever. The classic
fix rewrites the rule into an equivalent right-recursive pair:

$$A \rightarrow \beta A' \qquad A' \rightarrow \alpha A' \;\mid\; \varepsilon$$

This is equivalent as a *language* but distorts the grammar: the natural left-associative shape of
`a - b - c` has to be reconstructed afterward, and the grammar gets harder to read and evolve.

**The PEG parser.** A Parsing Expression Grammar parser is also top-down, but adds ordered choice
(alternatives tried in order, first match wins), unlimited lookahead via backtracking, packrat
memoization (each rule-at-position result cached, so backtracking stays linear and left recursion
works directly by seeding the memo table to a fixed point), and direct AST construction that skips
the old Concrete Syntax Tree.

```text
LL(1) pipeline (pre-3.9):
[source] -> [tokenizer] -> [Concrete Syntax Tree] -> [AST builder] -> [AST]

PEG pipeline (3.9+, PEP 617):
[source] -> [tokenizer] -> [PEG parser (memoized)] -> [AST]
```

**Old-versus-new, why it mattered.** The switch was not cosmetic. The structural pattern matching of
`match`/`case` (PEP 634, Chapter 16) is expressible largely *because* the grammar is no longer bound
by LL(1). The cost is that a PEG grammar can encode order-dependent rules, which puts more
responsibility on the grammar's authors; for the language's user, the result is strictly more
expressive syntax and better error messages.

> **Implementation detail, not language semantics.** The parser is a CPython concern. The *language*
> is defined by the grammar in the reference; whether it is parsed LL(1) or PEG is invisible to a
> correct program, with the narrow exception of newly expressible syntax. The formal grammar and
> lexical rules are **Deep S**.

---

## 2.4 The symbol table and static scope classification

**Why this exists.** Before emitting a single opcode, the compiler walks the AST to decide,
statically, what every name means: local to this function, a parameter, a global, a builtin, or a
free variable captured from an enclosing function. That classification is what lets CPython use
array-indexed local access (`LOAD_FAST`) instead of a dictionary lookup for every variable, the
single largest reason Python functions are not slower than they are.

CPython classifies each binding into local, explicit global (`global x`), implicit global (referenced
but never bound, resolved at runtime against module globals then builtins), or enclosing/free (bound
in an outer function and read, or with `nonlocal` rebound, by a nested one). The `symtable` module
exposes exactly this pass:

```python
# code/ch001/l02_symbol_table.py
import symtable
table = symtable.symtable(SRC, filename="<string>", compile_type="exec")
outer = table.lookup("outer_func").get_namespace()
```

Verified output (CPython 3.13.5):

```text
outer identifiers: ['inner_func', 'x', 'z']
'z' is_local in outer: True
'x' is_parameter in outer: True
inner free vars (closure): ('x', 'z')
'z' is_free in inner: True
```

`z` is local to `outer_func`, `x` is its parameter, and inside `inner_func` both are free variables
captured from the enclosing scope. (`get_frees()` returns an unordered set; the listing sorts it so
the output is stable, which is a habit worth keeping for any set-valued result you intend to print.)

> **A correctness note that cost a real debugging session.** Earlier drafts of this material called
> `Symbol.is_cell()`. That method does not exist in the `symtable` API; it raises `AttributeError` on
> 3.13.5. The supported predicates are `is_local`, `is_global`, `is_free`, `is_parameter`,
> `is_namespace`, `is_nonlocal`, `is_declared_global`, `is_assigned`, `is_referenced`, `is_imported`,
> `is_annotated`. To see which enclosing locals were promoted to cells, read the compiled code
> object's `co_cellvars` (§2.5), which is the authoritative view.

---

## 2.5 Closures and cell objects

**Why this exists.** A nested function can outlive the call that created it, yet still read the
enclosing function's locals. Those locals cannot live in the outer frame's fast-locals array, because
that array dies when the frame is popped. CPython promotes a captured local to a **cell**: a one-slot
heap object shared by reference between the enclosing and nested functions.

```c
/* Illustrative; Objects/cellobject.c. A cell is a one-slot indirection on the heap. */
typedef struct {
    PyObject_HEAD
    PyObject *ob_ref;   /* the captured object, shared by closure and enclosing scope */
} PyCellObject;
```

The compiler records on each code object which locals are cells (`co_cellvars`) and which names are
read from an enclosing scope (`co_freevars`):

```python
# code/ch001/l03_cells.py
top = compile(SRC, "<string>", "exec")
```

Verified output (CPython 3.13.5):

```text
outer_func co_cellvars: ('x', 'z')
inner_func co_freevars: ('x', 'z')

the cell is shared, so a closure sees LIVE updates, not a snapshot:
  bump() -> 1 2 3
```

Both `x` and `z` are cells in `outer_func` and free variables of `inner_func`. The shared cell is why
`bump()` returns 1, 2, 3 rather than 1, 1, 1: the closure sees live updates to the captured variable,
not a snapshot taken at closure-creation time. That same sharing is the mechanism behind the
notorious late-binding-closure-in-a-loop bug, which Chapter 3 dissects alongside comprehension scope.

---

## 2.6 `PyCodeObject`: the compiled blueprint

**Why this exists.** Compilation produces a `PyCodeObject`: an immutable, shareable description of a
unit of executable code (a module body, a function, a `lambda`, a comprehension, a class body). It is
immutable so it can be cached, shared across calls and threads, and reasoned about statically. A
*function* is a thin mutable wrapper (`__defaults__`, `__closure__`, `__globals__`) around an
immutable code object.

```c
/* Illustrative; fields from Include/cpython/code.h. The real struct changed across
   versions (notably the 3.11 frame/codeobject rework); these fields are stable and
   observable from Python as co_* attributes. */
struct PyCodeObject {
    PyObject_HEAD
    int co_argcount;        /* positional parameters */
    int co_posonlyargcount; /* positional-only parameters (PEP 570, 3.8+) */
    int co_kwonlyargcount;  /* keyword-only parameters */
    int co_nlocals;         /* number of local variables */
    int co_stacksize;       /* max evaluation-stack depth to reserve */
    int co_flags;           /* CO_OPTIMIZED, CO_NEWLOCALS, CO_GENERATOR ... */
    PyObject *co_consts;    /* tuple of literal constants */
    PyObject *co_names;     /* tuple of global/attribute names */
    PyObject *co_varnames;  /* tuple of local variable names */
    PyObject *co_freevars;  /* tuple of free (captured) names */
    PyObject *co_cellvars;  /* tuple of local names boxed into cells */
    /* bytecode, line table, exception table, etc. */
};
```

Every `co_*` field is readable from Python:

```python
# code/ch001/l04_code_object.py
def example_fn(a, b):
    local_val = 42
    return a + b + local_val
co = example_fn.__code__
```

Verified output (CPython 3.13.5):

```text
co_varnames : ('a', 'b', 'local_val')
co_consts   : (None, 42)
co_argcount : 2
co_nlocals  : 3
co_stacksize: 2
co_flags    : 0b11
```

Three details to internalize:

- `co_consts` contains `None` although the source never mentions it: it is the implicit return
  value's constant. `42` is interned into the pool and referenced by index.
- `co_flags == 0b11` sets `CO_OPTIMIZED | CO_NEWLOCALS`, the flags meaning "a real function: use fast
  array-indexed locals and a fresh locals namespace per call." A module or class body sets neither,
  which is precisely why module-level code uses dictionary-based `LOAD_NAME` and is slower (§2.8).
- The listing also demonstrates the immutability boundary: setting `example_fn.__defaults__` changes
  the *function wrapper* and leaves the code object untouched. The blueprint is frozen; the wrapper
  around it is where all runtime configurability lives.

There is a fourth detail you will meet in disassembly of large functions: **`EXTENDED_ARG`**. An
opcode's inline argument is one byte, so to reference the 300th constant the compiler prefixes an
`EXTENDED_ARG` that supplies the high bits, which the VM shifts and combines, allowing arguments up to
32 bits wide.

---

## 2.7 The virtual machine: frames and the evaluation loop

**Why this exists.** CPython is a stack-based virtual machine. Each call creates a frame holding the
code object, the local variables, and an evaluation stack onto which operands are pushed and from
which results are popped. A single C function, `_PyEval_EvalFrameDefault` in `Python/ceval.c`,
dispatches opcodes in a loop until the frame returns.

```c
/* Illustrative shape, Python/ceval.c. The modern loop uses computed-goto threaded
   dispatch and inline caches, but the skeleton is this. */
PyObject *_PyEval_EvalFrameDefault(PyThreadState *tstate,
                                   _PyInterpreterFrame *frame, int throwflag) {
    for (;;) {
        _Py_CODEUNIT word = *next_instr++;
        switch (word.op.code) {
            case LOAD_FAST: {                 /* push a local by array index */
                PyObject *v = GETLOCAL(word.op.arg);
                Py_INCREF(v); PUSH(v); DISPATCH();
            }
            case RETURN_VALUE:
                return POP();
        }
    }
}
```

Do not trust the textbook picture of the bytecode; read what *this* interpreter emits. Listing 2.5
prints the instruction stream as opname plus argument, which is stable regardless of where the
function lands in a file:

```python
# code/ch001/l05_bytecode.py
for ins in dis.get_instructions(example_fn):
    ...
```

Verified output (CPython 3.13.5):

```text
bytecode of example_fn (opname [arg]):
  RESUME
  LOAD_CONST  42
  STORE_FAST  local_val
  LOAD_FAST_LOAD_FAST  a, b
  BINARY_OP  +
  LOAD_FAST  local_val
  BINARY_OP  +
  RETURN_VALUE
```

This single listing demolishes several outdated mental models:

- **`RESUME`** opens every code object since 3.11. It is a no-op hook for the specializing adaptive
  interpreter and for debuggers; its presence tells you that you are reading modern bytecode.
- **`BINARY_OP +`**, not `BINARY_ADD`. Python 3.11 collapsed the per-operator binary opcodes into one
  `BINARY_OP` whose argument selects the operation. Material still showing `BINARY_ADD` predates 3.11.
- **`LOAD_FAST_LOAD_FAST a, b`** is a superinstruction: the compiler fused two adjacent `LOAD_FAST`s
  into one opcode to cut dispatch overhead. The VM is no longer one opcode per source operation.
- There is no trailing `LOAD_CONST None` / `RETURN_VALUE`, because the function ends in an explicit
  `return` and the compiler does not append the implicit `return None`.

> **Version drift, and why this book runs the listing on both interpreters.** Every opcode above
> except `RESUME`, `STORE_FAST`, `BINARY_OP`, and `RETURN_VALUE` is different on CPython 3.14. There,
> `LOAD_CONST 42` becomes **`LOAD_SMALL_INT`** (small integers are no longer even constants; they are
> produced directly), `LOAD_FAST_LOAD_FAST` becomes **`LOAD_FAST_BORROW_LOAD_FAST_BORROW`**, and the
> plain `LOAD_FAST` becomes **`LOAD_FAST_BORROW`**. The `_BORROW` family is a 3.14 optimization that
> pushes a *borrowed* reference (no refcount increment) where the compiler can prove the local
> outlives the use, eliminating a great many incref/decref pairs. Both interpreters' output is
> recorded under `code/ch001/expected/`; a book that showed only one and called it "the bytecode"
> would be wrong within a year. This is the drift the whole verification harness exists to catch.

Tracing the evaluation stack for `a + b` makes the stack discipline concrete:

```text
  LOAD_FAST_LOAD_FAST(a,b)   BINARY_OP(+)        ...        RETURN_VALUE
  +---------+                +---------+                    +---------+
  |    b    |                |  a + b  |                    | (empty) |
  +---------+                +---------+        -->         +---------+
  |    a    |       -->      | (empty) |                    | (empty) |
  +---------+                +---------+                    +---------+
```

> **3.11+ reality: the specializing adaptive interpreter.** Modern CPython does not execute a fixed
> opcode stream forever. As code runs hot, generic opcodes are specialized in place into faster
> variants, backed by inline caches stored in the code units. This is not the JIT (PEP 744); it is
> interpretation that rewrites itself, and it is the direct reason the folklore in §2.8 no longer
> holds the way it once did. Chapter 17 covers it in full.

---

## 2.8 Measurement: locals, globals, and a piece of overturned folklore

Every intermediate Python guide teaches the same optimization: bind a global or a method to a local
before a hot loop, because a local read is `LOAD_FAST` (an array index) while a global read is
`LOAD_GLOBAL` (a dict probe of module globals, then builtins). The advice is correct in direction.
The interesting question, which the guides never answer, is *how large the effect actually is on a
current interpreter*.

**Methodology.** `code/ch001/bench_locals_vs_globals.py`, run through `_harness/bench.py`. A
1000-element list comprehension calling `math.sqrt` per element, resolved either as a global-plus-
attribute each iteration or hoisted to a local once. Fifteen batches, `min` as the headline statistic
(microbenchmark noise is one-sided), median and RSD as diagnostics. CPython 3.13.5, `-O2`, computed
gotos on. Apple M3 Pro, macOS 27.0, arm64. Ratios are within this one interpreter.

| case | min (ns/loop) | ratio |
|---|---|---|
| global lookup per item | 22,820 | 1.00x |
| hoisted local per item | 21,851 | 0.96x |

**The hoist saves about 4%.** Not the dramatic win the folklore implies, and the reason is §2.7's
specializing interpreter. Confirmed directly:

```python
# after warming the function, the global load has specialized
>>> [op for op in opnames(uses_global) if op.startswith("LOAD_GLOBAL")]
['LOAD_GLOBAL_MODULE']
```

Since 3.11, a hot `LOAD_GLOBAL` specializes into **`LOAD_GLOBAL_MODULE`**, an inline-cached read that
skips the hashing and probing and is nearly as cheap as `LOAD_FAST`. The optimization that mattered in
Python 2, where every global read was a full dict lookup, was largely absorbed into the interpreter.
It remains a real constant-factor win for genuine hot loops and nothing else; in cold code it buys
nothing and costs a line of clarity.

This is the chapter's methodological point in miniature: **an optimization's value is a number, not a
belief, and the number changes as the interpreter does.** Measure on the interpreter you ship on.

---

## 2.9 Edges and failure modes

**The copy-that-was-not.** §2.1. `b = a` aliases; it does not copy. When you need a copy, say so:
`b = a.copy()`, `b = list(a)`, or `copy.deepcopy(a)` for a recursive one. The introduction's config
bug is this failure in the wild.

**The dynamic-namespace trap.** If the compiler cannot statically know a function's locals, because it
contains `exec()` against an implicit namespace, it abandons fast locals and falls back to dictionary-
based `LOAD_NAME`, searching local then global then builtin at runtime. (`from module import *` at
function scope, which would cause the same problem, is a `SyntaxError` in Python 3 precisely to
prevent it.) Keep function scopes statically analyzable; dynamic features defeat the single most
important optimization the compiler performs.

**`SyntaxError` versus `NameError`, and where they live.** Parsing and symbol analysis happen before
any execution, so a malformed expression is rejected at compile time and can never reach the VM. An
unbound name is a runtime `NameError`, because name resolution against globals and builtins is a
runtime operation. Knowing which stage owns an error tells you where to look.

**Do not fight code-object immutability.** Code objects are immutable by design; patching bytecode at
runtime is a stunt, not an optimization. The supported lever is the function wrapper: decorators,
`functools.partial`, closures.

**Do not benchmark cold code.** §2.8's numbers are steady-state, after the specializer has warmed. A
first-call measurement runs generic opcodes and measures something you will never ship. This is the
discipline of **Deep K**.

---

## 2.10 Connections

**Backward.** Chapter 1 covered why Guido reversed ABC's flaws, and showed the tokenizer emitting the
INDENT/DEDENT tokens this chapter's parser consumes. The design commitments named there, everything-
is-an-object and names-as-bindings, are the model §2.1 makes precise.

**Forward.** The `PyObject` header whose refcount §2.1 increments is Chapter 19 (**Deep A**). Cyclic
garbage collection and the late-binding-closure bug are Chapter 3. The PEG parser that replaced LL(1)
is Chapter 14 (Python 3.9). The specializing adaptive interpreter that overturned §2.8's folklore is
Chapter 17. The `_BORROW` opcode family and the full `ceval.c` loop are **Deep J**. Benchmarking
discipline is **Deep K**.

**Across books.** The pipeline stops at bytecode, and bytecode is an interpreter's internal affair,
which is why crossing into **Book I** means leaving it entirely: a C++ function reached through
`nanobind` is not compiled to a `PyCodeObject` and never enters this loop. Understanding where the
Python pipeline ends is understanding where the C boundary begins, and that boundary is **Deep M**.

---

## 2.11 Exercises

**1. Predict the aliasing.** Without running it, state the final value of every name:

```python
x = [1, 2]
y = x
z = x[:]
y.append(3)
z.append(4)
```

Then run it. Which of `y` and `z` is a copy, and which single character made the difference? Explain
in terms of §2.1.

**2. Read the scopes.** Write a three-level nested function where the innermost reads a name from the
outermost, skipping the middle. Use `symtable` (Listing 2.2) to show how each level classifies that
name, then use `co_freevars`/`co_cellvars` (Listing 2.3) to show how the cell is threaded through the
middle function that never uses it. Why must the middle function carry a free variable it does not
reference?

**3. Find `EXTENDED_ARG`.** §2.6 claims the compiler emits `EXTENDED_ARG` when an argument exceeds one
byte. Construct the smallest function whose disassembly contains one, and confirm it with `dis`.
Predict the number of constants or locals needed before writing the function.

**4. Reproduce and extend the measurement.** Run `bench_locals_vs_globals.py`. Then modify it so the
loop body does *less* work per item than `math.sqrt`, and predict, before running, whether the hoist's
advantage grows or shrinks. Explain the result in terms of §2.7's specialization, and state the
condition under which the classic advice would still be worth a line of readability.

**5. The design question.** §2.8 shows that a headline optimization from Python 2 was largely absorbed
into the interpreter by 3.11. Argue what this implies for how a performance-minded engineer should
learn Python: which knowledge has a short half-life, which is durable, and how you would tell the
difference before spending effort on it. Name one other optimization in this chapter that you expect
the interpreter to eventually absorb, and say why.

---

## 2.12 Summary and cross-references

- A Python program is a **graph of heap objects**; names are **bindings**, not typed storage.
  Assignment rebinds and adjusts refcounts; it never copies. `is` is identity, `==` is value. The
  aliasing bug in the introduction is this one fact, misunderstood.
- Source is **compiled ahead of time** through tokenizer, PEG parser (PEP 617, 3.9+), symbol table,
  and compiler into an immutable **`PyCodeObject`**. Only the **evaluation loop** is interpretation.
- The **symbol table** statically classifies every name, enabling array-indexed `LOAD_FAST` locals
  and **cell**-based closures that share live state.
- Modern bytecode (3.11+) carries `RESUME`, the unified `BINARY_OP`, and fused **superinstructions**,
  and it **specializes itself** as it runs. On **3.14** the `LOAD_FAST` family became
  `LOAD_FAST_BORROW`; read `dis` on your interpreter, not folklore.
- **Measured:** hoisting a global to a local saves about **4%** here, not the classic dramatic win,
  because 3.11+ specializes `LOAD_GLOBAL` into an inline-cached `LOAD_GLOBAL_MODULE`. An
  optimization's value is a number, and the number moves with the interpreter.

**Cross-references.** The `PyObject` header and reference counting → Chapter 19 (Deep A). Cyclic GC
and closure/comprehension scope → Chapter 3. The PEG parser → Chapter 14. The specializing adaptive
interpreter → Chapter 17. The `ceval.c` loop and the `_BORROW` opcodes → Deep J. Benchmarking
discipline → Deep K. The formal grammar and lexical rules → Deep S. The C-API boundary → Deep M.
