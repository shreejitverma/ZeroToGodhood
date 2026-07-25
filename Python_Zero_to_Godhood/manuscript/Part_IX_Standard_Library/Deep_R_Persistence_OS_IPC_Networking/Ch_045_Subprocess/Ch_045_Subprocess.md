# Chapter 45: Running Programs with `subprocess`

A file-processing service builds a command by interpolating a filename into a string and runs it with
`subprocess.run(f"convert {filename} out.png", shell=True)`. It works, until a filename is
`photo.jpg; rm -rf /data`, and the shell, doing exactly its job, runs the `rm` after the `convert`. This is
**command injection**, the shell-level twin of the SQL injection of Chapter 41, and it has the same cause
(mixing untrusted data into a string that an interpreter parses) and the same fix: pass the command as a
*list of arguments*, so the operating system executes the program directly and every element is a literal
argument that no shell ever sees. As a bonus, the safe form is also faster, `shell=True` starts a whole
extra shell process and runs about **2x slower** for a trivial command.

Two reasons, then, to avoid `shell=True`: it is a security hole, and it is slower. This chapter continues
**Deep R** with `subprocess`, the standard way to run external programs, and the argument-passing discipline
that keeps it safe. The parallel to Chapter 41 is exact and deliberate: data must be passed *as data*, never
spliced into a string an interpreter will execute.

## Section index

- **45.1** List args vs `shell=True`
- **45.2** Why the list form is safe (and the shell form is not)
- **45.3** Measurement: the cost of an extra shell
- **45.4** Edges and failure modes
- **45.5** Connections
- **45.6** Exercises
- **45.7** Summary and cross-references

Listings live under `code/ch045/` and are re-executed by `make verify` on both interpreters.

---

## 45.1 List args vs `shell=True`

```python
# code/ch045/l01_subprocess.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- UNSAFE: shell=True interprets the whole string ---
    Processing report.txt
    INJECTED-COMMAND-RAN
--- SAFE: a list of args; metacharacters are literal ---
    Processing report.txt; echo INJECTED-COMMAND-RAN
--- capturing output and checking the exit status ---
    stdout     : 'done'
    returncode : 0
    check=True raised on exit 1
```

The demonstration uses a benign injected command (`echo INJECTED-COMMAND-RAN`) so it is safe to run, but the
mechanism is the real one. The input `"report.txt; echo INJECTED-COMMAND-RAN"` contains a `;`, a shell
command separator. Under **`shell=True`**, the whole string is handed to `/bin/sh`, which sees the `;`,
splits it into two commands, and runs *both*, the injected `echo` executes, producing the second output
line. Substitute `rm -rf` for `echo` and the injection is catastrophic.

Under the **list form** `["echo", "Processing", user_input]`, the OS executes `echo` directly with three
arguments, and the third argument is the entire string `"report.txt; echo INJECTED-COMMAND-RAN"`, printed
verbatim on one line. No shell is involved, so the `;` has no special meaning, it is just a character in an
argument. The list form is not a style choice; it is the boundary that makes hostile input harmless.

The rest of the API: `capture_output=True, text=True` collects `stdout`/`stderr` as strings, `.returncode` is
the exit status, and `check=True` raises `CalledProcessError` on a non-zero exit (the `false` command exits
1), so failures surface as exceptions instead of being silently ignored.

---

## 45.2 Why the list form is safe (and the shell form is not)

There are two ways to start a program, and they differ in who parses the command. The list form calls the
OS `exec` family directly: Python hands the kernel a program path and an argument *vector* (an actual array
of strings), and the kernel starts that program with exactly those arguments. No string parsing happens;
there is no step at which a `;` or `|` or `$(...)` could be interpreted, because nothing interprets the
arguments as syntax. Whatever bytes are in an argument reach the program as that argument's value.

`shell=True` inserts a shell between Python and the program. Python starts `/bin/sh -c "<your string>"`, and
the shell parses that string with *full shell syntax*: word splitting, globbing, variable expansion, command
substitution, and command separators. Every one of those is a way for interpolated input to become code. The
shell is doing precisely what it is designed to do; the bug is asking it to parse a string that contains
untrusted data. This is why the fix is structural, not "escape the input": correctly escaping every shell
metacharacter for every shell is error-prone and fragile, whereas passing a list *removes the parser
entirely*. As with SQL parameters (Chapter 41), the robust defense is to never build the dangerous string in
the first place.

---

## 45.3 Measurement: the cost of an extra shell

**Methodology.** `code/ch045/bench_shell.py`. Running the trivial command `true` via a list of args (direct
`exec`) versus `shell=True` (via `/bin/sh`). `min` per run. Process spawning is OS-bound and noisy (the
harness flags runs machine-busy), so the ratio, not the absolute time, is the finding. CPython 3.13.5, Apple
M3 Pro, macOS 27.0, arm64.

| run `true` | min per run | ratio |
|---|---|---|
| list args (direct `exec`) | **~2.2 ms** | 1.00x |
| `shell=True` (via `/bin/sh`) | **~4.4 ms** | **~2x** |

The list form spawns one child process (the program). `shell=True` spawns *two*: the shell, and then the
command the shell runs, and it pays a full shell startup on top. For the trivial `true`, that doubles the
time. The absolute numbers are dominated by process-creation cost and vary with the machine, but the
structural fact, `shell=True` does strictly more work by interposing a shell, is stable.

So the two reasons align: the list form is safe *and* faster, and `shell=True` is a security hole *and*
slower. The rule: **pass a list of arguments by default; use `shell=True` only for trusted, fixed commands
that genuinely need shell features (a pipeline, a glob, redirection), and never with interpolated untrusted
input.** When you do need a pipeline, prefer wiring `subprocess` pipes together in Python (each stage a list-
form process) over handing a shell string, keeping the injection-free property end to end.

---

## 45.4 Edges and failure modes

**`shell=True` with interpolated input.** §45.1. Command injection. Never do it. Use a list of args; if you
truly need a shell feature, keep the untrusted parts as list arguments and the shell string fixed.

**Ignoring the exit status.** `subprocess.run` does *not* raise on a non-zero exit by default, it returns a
`CompletedProcess` with a non-zero `.returncode`. Pass `check=True` to turn failures into
`CalledProcessError`, or you will silently proceed after a failed command.

**Deadlock on large output without `capture_output`/pipes drained.** Writing to `stdout=PIPE` and not reading
it while the child fills the OS pipe buffer deadlocks (the child blocks on a full pipe, the parent waits for
the child). Use `subprocess.run(..., capture_output=True)` or `communicate()`, which drain the pipes
correctly.

**Not setting a timeout.** A child that hangs hangs the parent forever. Pass `timeout=` to `run`/`communicate`
to bound it (it raises `TimeoutExpired`), especially for anything touching the network or untrusted work.

**`text=True` and encoding.** Without `text=True`, `stdout`/`stderr` are `bytes`. With it, they are decoded
with the locale (or `encoding=`) codec, and undecodable bytes raise. Set `encoding=` explicitly for
predictable behavior (Chapter 7).

**PATH and the program not found.** The list form looks the program up on `PATH` (unless given an absolute
path) and raises `FileNotFoundError` if it is missing, a clearer failure than a shell's "command not found"
on stderr. Prefer absolute paths for security-sensitive invocations so a hostile `PATH` cannot substitute a
program.

---

## 45.5 Connections

**Backward.** The injection parallel is Chapter 41 (SQL): both are "data spliced into a string an interpreter
parses," and both are fixed by passing data *as data*. The `stdout`/`stderr` pipes are the file objects of
Chapter 40, and their `text=True` decoding is Chapter 7's encoding boundary. The process model, a child with
its own descriptors, connects to Chapter 8's process-vs-thread discussion.

**Forward.** Wiring multiple `subprocess` pipes into a pipeline, and the OS process/`fork`/`exec` model, are
deeper **Deep R** and OS-internals material. Concurrency across many child processes overlaps with
`multiprocessing` (the IPC material later in Deep R) and the GIL story of Chapter 8. Sandboxing and dropping
privileges for untrusted children is a security topic in **Deep S**.

**Across books.** `subprocess` is how Book II shells out to external tools, an encoder, a model runner, a
CLI, at the seams into **Book III**, and the list-form discipline is what keeps a filename or user parameter
from becoming a shell exploit at that boundary. A **Book III** pipeline that invokes an external converter or
inference binary passes every dynamic value as a list argument, never as shell text, so untrusted document
metadata cannot inject commands. **Deep U** owns the process-boundary seam; **Deep S** owns the sandbox.

---

## 45.6 Exercises

**1. Demonstrate the injection (safely).** Reproduce §45.1 with a benign injected command and confirm it runs
under `shell=True` but not under the list form. Explain, in terms of who parses the string, why the list form
is immune.

**2. Handle failure.** Run a command that exits non-zero, first without `check=True` (and observe the
non-zero `.returncode` is easy to ignore) then with `check=True` (and catch the `CalledProcessError`).
Explain why `check=True` is the safer default.

**3. Capture and decode.** Run a command that prints non-ASCII output, capture it with `text=True` and an
explicit `encoding=`, and show the decoded string. Explain what `text=True` does and why the encoding should
be explicit.

**4. Bound a hang.** Run a command that sleeps longer than a `timeout=` you set, and catch `TimeoutExpired`.
Explain why every subprocess that could hang needs a timeout.

**5. The design question.** `subprocess` offers both a safe list form and a dangerous `shell=True`. Argue why
`shell=True` exists at all, given the injection risk. Your answer must identify the legitimate uses (fixed,
trusted commands needing shell features), explain why "escape the input" is the wrong fix, and connect the
list-form defense to the SQL-parameter defense of Chapter 41.

---

## 45.7 Summary and cross-references

- **Pass a list of arguments.** The OS `exec`s the program directly with each element a literal argument; no
  shell parses anything, so metacharacters in untrusted input are harmless.
- **`shell=True` is command injection** when input is interpolated: the shell parses the whole string with
  full syntax, and a `;`/`|`/`$(...)` in the data becomes code. It is the shell twin of SQL injection
  (Chapter 41); the fix is structural (a list), not escaping.
- **Measured:** `shell=True` is **~2x slower** for a trivial command because it spawns an extra shell
  process. So the list form is safe *and* faster.
- **Also:** use `check=True` (raise on non-zero exit), `capture_output`/`communicate` (avoid pipe deadlock),
  `timeout=` (bound hangs), and explicit `encoding=` with `text=True`.

**Cross-references.** SQL injection parallel → Chapter 41. Pipes as file objects and `text=True` encoding →
Chapters 40 and 7. Process vs thread → Chapter 8. `multiprocessing` IPC → the rest of Deep R. Sandboxing
untrusted children → Deep S. The process-boundary seam → Deep U.
