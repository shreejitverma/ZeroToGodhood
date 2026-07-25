# Chapter 54: Code Objects and Frames

Python source is not executed directly.
Between the text you write and the computation that runs sit two objects that this deep volume, the interpreter, is built around: the **code object** (the compiled form of your function) and the **frame** (the runtime state of one call).
When you write `def f(...)`, CPython compiles the body *once* into a code object, a block of bytecode plus tables of names and constants, and stores it as `f.__code__`.
When you *call* `f`, the interpreter creates a frame, a workspace holding that call's local variables and its position in the bytecode, links it to the frame of the caller, and runs the code object's bytecode inside it.
Understanding these two objects is understanding how CPython runs, and it demystifies tracebacks (a chain of frames), closures (frames and their variables), debuggers (which read frames), and performance (compilation is amortized into the code object).

The chapter's measurement grounds the "compiled once" claim: executing a pre-compiled code object is **2.9x** faster than recompiling the source each time, which is why the code object exists, `def` pays compilation *once*, at import, and every call reuses the artifact.
This is the first fact of interpreter performance, and the rest of Deep H (the evaluation loop, bytecode specialization, the JIT) builds on it.

**This opens Deep H, the interpreter volume.**
It is the execution-model foundation under the `dis` tool (Chapter 50, which inspects these code objects), the specializing interpreter (Chapter 17), and the bytecode cache (Chapter 66, which caches compiled code across runs). It uses version-stable APIs deliberately, the exact bytecode and constant table drift across releases (that drift is the *subject* of the specializing interpreter), so this chapter anchors on what is stable: the code object's structure and the frame's role.

## Section index

- **54.1** The code object: the compiled function
- **54.2** The frame: one call's runtime state
- **54.3** Measurement: compilation is amortized
- **54.4** Edges and failure modes
- **54.5** Connections
- **54.6** Exercises
- **54.7** Summary and cross-references

Listings live under `code/ch135/` and are re-executed by `make verify` on both verification interpreters.

---

## 54.1 The code object: the compiled function

```python
# code/ch135/l01_code_and_frames.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a code object: what `def greet` compiled to (once) ---
  co_argcount : 2   (name, count)
  co_varnames : ('name', 'count', 'prefix')   (locals incl. args, in order)
  co_nlocals  : 3
  'hi' is in co_consts (a literal constant) : True
  co_names (globals/attrs referenced)       : ()   (none here)
  co_code is compiled bytecode (bytes)      : True
  the SAME code object is reused every call : True
--- a frame: the runtime state of one call, with f_back = its caller ---
  inner's frame f_code.co_name        : 'inner'
  its caller via f_back.f_code.co_name : 'outer'   (the call stack)
--- a frame carries its own local variables ---
  f_locals of a frame with x, y : ['x', 'y']
--- the rule ---
  a code object is the compiled function (made once, reused per call);
  a frame is one call's live state; f_back chains frames into the call stack
```

A **code object** (`func.__code__`) is what the compiler produces from `def`, and it is a *static, immutable* description of the function's behaviour, separate from the function object itself (which adds defaults, closure, name, `__doc__`). Its tables are the compiler's output:

- **`co_argcount`** (2): how many positional parameters.
- **`co_varnames`** (`('name', 'count', 'prefix')`): the local variable names, arguments first, in slot order. Locals are accessed by *index* in the bytecode (fast), not by name, this tuple is the index-to-name map.
- **`co_nlocals`** (3): the number of local slots the frame will need.
- **`co_consts`**: the literal constants (`'hi'` here, plus possibly `None`), referenced by index. (Whether `None` appears is a version-specific optimization, so the listing tests membership rather than the exact tuple.)
- **`co_names`**: the *global* and *attribute* names the code references (empty here, `greet` uses only locals), the names looked up dynamically at runtime.
- **`co_code`**: the bytecode itself, a `bytes` object, the sequence of instructions the interpreter executes.

The decisive property is **"compiled once, reused every call"**: `greet.__code__ is c` stays the same object across the program's life. `def greet` compiled the source *one time* into this code object; every one of the millions of calls to `greet` runs *this same* bytecode, creating a fresh frame but reusing the compiled instructions. This separation, one static code object, many dynamic frames, is the core of CPython's execution model, and the reason compilation is a one-time import cost, not a per-call cost (§54.3).

---

## 54.2 The frame: one call's runtime state

Where the code object is static and shared, the **frame** is dynamic and per-call: each invocation of a function gets its own frame.

A frame holds everything specific to *one active call*:

- **Its local variables** (`f_locals`): the frame that ran `x, y = 10, 20` has `x` and `y` in its locals. Each call has its own, which is why recursion works (each recursive call's frame has independent locals) and why closures capture per-call state.
- **Its position in the bytecode** (the instruction pointer, `f_lasti`): where execution currently is, so the interpreter knows what to run next and can resume after a call returns.
- **Its code object** (`f_code`): the compiled function being run (`f_code.co_name` is the function's name, `'inner'`).
- **A link to its caller** (`f_back`): the frame that called this one.

That last field is profound: **the chain of `f_back` links *is* the call stack.**
The listing walks it, `inner`'s frame's `f_back` is `outer`'s frame (`f_back.f_code.co_name` is `'outer'`), and following `f_back` repeatedly gives the full stack of active calls.
This is *exactly* what a **traceback** is: when an exception propagates, Python walks the `f_back` chain and prints each frame's function, file, and line, so the traceback you read is a rendering of the live frame stack at the moment of the error.
It is also what **debuggers** read (to show you the call stack and each frame's locals), what `inspect` exposes, and what `sys._getframe()` hands you directly.

So the execution model is: the interpreter runs a **code object**'s bytecode inside a **frame**, the frame holds that call's locals and instruction pointer, calling a function pushes a new frame (linked via `f_back` to the caller), and returning pops it.
The **frame stack** (the `f_back` chain) is the program's control state, the thing that grows with recursion (until `RecursionError`), that a generator suspends and resumes (Deep F), and that a traceback renders.
Two objects, one static (code) and one dynamic (frame), compose into all of Python's control flow.

---

## 54.3 Measurement: compilation is amortized

**Methodology.** `code/ch135/bench_compile.py`.
Executing a **pre-compiled** code object versus recompiling the same source on every execution.
`min` of 5 runs, 100,000 executions.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| execute a small snippet | us | vs pre-compiled |
|---|---|---|
| `exec(pre-compiled code object)` | 4.5 | 1.0x |
| `exec(compile(src) each time)` | 12.8 | **2.9x** |

Recompiling the source each time is **2.9x** slower (2.8x on 3.14.6), because compilation, lexing, parsing, building the AST, and emitting bytecode, is real work.
Executing a code object skips all of it and just runs the bytecode.

This is the payoff of §54.1's "compiled once."
`def` compiles the function body *one time* into a code object and every call reuses it, so you pay compilation at *import* (when the `def` runs), not per call.
The interpreter never re-parses your source to run a function; it runs the cached bytecode.
This amortization extends *across runs* via the **bytecode cache** (Chapter 66): the `.pyc` files in `__pycache__` store the compiled code objects of imported modules, so the *next* process skips even the import-time compilation and loads the code objects directly, the first call in a fresh process runs pre-compiled bytecode.

The practical lesson is a rule and a caution.
The rule: **compile once, run many**, which Python does for you (`def`, imports, the `.pyc` cache), so ordinary code never pays repeated compilation.
The caution: do not *defeat* it by compiling in a loop, `exec`/`eval` of a *source string* per iteration recompiles every time (the 2.9x, per iteration), and dynamically building and `compile`-ing code in a hot path is a classic performance mistake. If you must run generated code repeatedly, `compile` it *once* into a code object and reuse that.
This first Deep H measurement sets the volume's theme: interpreter performance comes from *not doing work twice*, compilation amortized into the code object here, and, in the chapters ahead, the specializing interpreter caching the *types* it sees so it need not re-check them, and the JIT compiling hot code objects to machine code so it need not re-interpret them. All three are the same idea, do the expensive analysis once and reuse the result, applied at compilation, at type-checking, and at machine-code generation.

---

## 54.4 Edges and failure modes

**The exact bytecode and constants are version-specific.** §54.1.
`co_code`, and whether `None` is in `co_consts`, change across releases (that drift is the specializing interpreter's doing). Reason about code objects via their *structure* (`co_argcount`, `co_varnames`), not exact bytecode; never assert on specific opcodes across versions.

**`f_locals` is a snapshot, and writing it may not stick.**
Reading `frame.f_locals` builds a dict from the frame's fast-local slots; historically, *writing* to that dict did not reliably update the actual locals (the fast slots). Python 3.13 (PEP 667) made `f_locals` a live proxy in more cases, but relying on mutating another frame's locals is fragile. Read frames for introspection; do not mutate them.

**Holding frame references keeps everything alive.**
A frame references its locals, its code object, and (via `f_back`) the entire call stack above it. Storing a frame (or a traceback, which holds frames) keeps all those objects alive, a common memory leak (Chapter 31): a cached exception traceback pins every frame and local in the stack at the time it was raised. Clear tracebacks/frames you store (`del`, or `traceback.clear_frames`).

**`sys._getframe` is a CPython implementation detail.**
The frame API (`f_back`, `f_locals`, `sys._getframe`) is CPython-specific; other implementations may not expose it the same way. Use `inspect` for portable-ish introspection, and treat direct frame manipulation as implementation-coupled.

**Deep recursion exhausts the frame stack.**
Each call pushes a frame; unbounded recursion hits `RecursionError` (`sys.getrecursionlimit`, default ~1000) before it exhausts the C stack and crashes. The limit exists to turn a C-stack overflow (a crash) into a catchable Python exception.

**A code object is not a function.**
`func.__code__` (the compiled body) is separate from `func` (which adds `__defaults__`, `__closure__`, `__globals__`, `__name__`). Two functions can share a code object (e.g. a closure factory's inner function); the code object is the shared compiled logic, the function object binds it to an environment.

**`compile`/`exec`/`eval` on untrusted input is dangerous.**
Compiling and executing arbitrary source is arbitrary code execution. Never `exec`/`eval` untrusted strings; the fact that you *can* build and run code at runtime (§54.3) is a security hazard as much as a feature.

---

## 54.5 Connections

**Backward.**
The `dis` tool (Chapter 50) disassembles the `co_code` this chapter describes. The bytecode cache (`.pyc`, Chapter 66) stores code objects across runs. Frames holding their locals is the mechanism behind closures and nonlocal scope (Deep F / scoping). A traceback rendering the `f_back` chain is exceptions-as-control-flow. Frame references pinning memory is Chapter 31 (reference counting).

**Forward.**
The **evaluation loop** (`ceval`, the giant `switch` over opcodes that runs `co_code` inside a frame), the **specializing adaptive interpreter** (Chapter 17, which rewrites hot bytecode with type-specialized opcodes), and the **JIT** (which compiles hot code objects to machine code) are the rest of **Deep H**. Generators and coroutines (Deep F) are frames that suspend and resume rather than being popped on return. `inspect` and `sys.settrace` (debuggers/profilers reading frames) are Deep S.

**Across books.**
The code-object/frame model underlies **Book I**'s tooling and performance work: profilers sample the frame stack to attribute time, debuggers walk `f_back` to show the call path, and the "compile once, run many" rule shapes how generated code (a strategy compiled from a config, a query plan) is handled, compiled once to a code object and reused, never recompiled per invocation. The order-book system, where it generates code (a compiled fast-path from a strategy specification), compiles it a single time into a code object at startup and calls it in the hot loop, never `exec`-ing source per event, the §54.3 rule as an architectural requirement, and it clears stored tracebacks to avoid the §54.4 frame-pinning leak in a long-running process.

---

## 54.6 Exercises

**1. Read a code object.** Reproduce §54.1: inspect a function's `co_argcount`, `co_varnames`, `co_nlocals`, `co_consts` (membership), `co_names`, and confirm `__code__` is the same object across calls. Add a global reference and show it appear in `co_names`. Explain why locals are a tuple (index-addressed) and globals are names.

**2. Walk the stack.** Reproduce §54.2: use `sys._getframe` and `f_back` to print the chain of function names from a nested call. Relate it to what a traceback shows. Explain why `f_back` *is* the call stack.

**3. Measure compilation.** Reproduce §54.3. Confirm executing a pre-compiled code object beats recompiling. Then simulate the anti-pattern (a loop that `exec`s a source string) and fix it (compile once). Explain the amortization and how `.pyc` extends it across runs.

**4. The frame leak.** Raise and catch an exception, store its traceback, and show (with `gc`/`tracemalloc`) that it pins the frames and their locals. Clear it and show the memory released. Explain the reference chain.

**5. The design question.** CPython separates the static code object from the dynamic frame, one compiled artifact, many per-call states. Argue what this buys (compilation amortized, recursion, closures, suspendable generators, debuggability) and its costs (frame allocation per call, the frame-pinning leak). How does this model set up the specializing interpreter and JIT (Deep H) to optimize *without* changing your source?

---

## 54.7 Summary and cross-references

- CPython runs your program via two objects: a **code object** (`func.__code__`, the **compiled** function, made **once** by `def`) and a **frame** (one call's **runtime state**). One static code object serves many dynamic frames.
- A **code object** holds the bytecode (`co_code`) plus tables: `co_argcount`, `co_varnames` (locals, index-addressed), `co_consts` (literals), `co_names` (globals/attrs). It is reused every call.
- A **frame** holds one call's **locals** (`f_locals`), its **instruction pointer**, its code object (`f_code`), and a link to its caller (`f_back`). **The `f_back` chain is the call stack**, which is what a traceback renders and a debugger walks.
- **Measured:** executing a pre-compiled code object is **2.9x** faster than recompiling the source each time. `def` and imports compile **once** (paid at import); the **`.pyc` cache** extends this across runs. **Compile once, run many**; never `exec` source in a hot loop.
- **Edges:** exact bytecode/constants are version-specific (reason about structure); frames pin their stack (traceback leaks, clear them); `f_locals` mutation is fragile; frame APIs are CPython-specific; deep recursion hits `RecursionError`; `exec`/`eval` of untrusted input is arbitrary code execution.

**Cross-references.** Disassembling `co_code` → Chapter 50. The `.pyc` bytecode cache → Chapter 66. The specializing interpreter and JIT → Chapter 17 and the rest of Deep H. Frames that suspend (generators) → Deep F. Frame introspection (debuggers, profilers) → Deep S. Frame-pinning leaks → Chapter 31.
