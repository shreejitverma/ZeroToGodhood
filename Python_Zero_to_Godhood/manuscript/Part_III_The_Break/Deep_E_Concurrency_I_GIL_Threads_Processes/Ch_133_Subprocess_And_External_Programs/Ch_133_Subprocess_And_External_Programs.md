# Chapter 52: Subprocess and External Programs

Deep E's "processes" so far have meant Python worker processes (Chapter 47).
This chapter covers the other kind: **external programs**, any executable on the system, run from Python via the `subprocess` module.
Where `multiprocessing` runs your Python *functions* in child interpreters, `subprocess` runs `git`, `ffmpeg`, `grep`, another Python script, a compiled tool, and captures its output, exit code, and streams.
It is how Python acts as glue, orchestrating the command-line tools that do a job better than reimplementing them.

The chapter has two through-lines.
One is **safety**: pass arguments as a **list** (`["cmd", "arg"]`), which execs the program directly with no shell, so there is no shell-injection vulnerability, the single most important habit with `subprocess`, because `shell=True` on untrusted input is a classic remote-code-execution hole.
The other is **cost**: spawning a subprocess forks the process and execs a whole new program, costing **~2 milliseconds** (measured **~32,000x** an in-process call), so calling a subprocess *per item* in a loop is a serious anti-pattern, prefer a Python library, or call the tool once over a batch.

**This is Deep E's external-process chapter.**
It complements `multiprocessing` (Chapter 47, Python workers) with external programs, connects to the OS/IPC concerns of Deep R (pipes, streams), and shares the "amortize the boundary" rule with the whole volume (Chapters 43-51): the process-spawn boundary is expensive, so cross it rarely.

## Section index

- **52.1** `subprocess.run`: output, exit codes, and safe arguments
- **52.2** Safety and streams
- **52.3** Measurement: spawning is expensive
- **52.4** Edges and failure modes
- **52.5** Connections
- **52.6** Exercises
- **52.7** Summary and cross-references

Listings live under `code/ch133/` and are re-executed by `make verify` on both verification interpreters.

---

## 52.1 `subprocess.run`: output, exit codes, and safe arguments

```python
# code/ch133/l01_subprocess.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- run a command and capture its output ---
  stdout     : 'hello\n'
  returncode : 0   (0 = success)
--- the return code signals success or failure ---
  'false' returncode : 1
--- check=True raises on a nonzero exit (fail loudly) ---
  check=True raised CalledProcessError, returncode : 1
--- args as a LIST: no shell, so no injection (arguments are literal) ---
  python3 -c 'print(6*7)' -> '42'
--- pipe data to the program's stdin with input= ---
  wc -c of '12345' (byte count) : 5
--- the rule ---
  subprocess.run(list_args, capture_output=True, text=True); check the
  returncode (or check=True); pass args as a LIST, never shell=True on input
```

`subprocess.run` is the modern, high-level entry point, and its result object carries everything about the run.

- **Output capture:** `capture_output=True, text=True` collects the program's stdout and stderr as strings (`r.stdout` is `'hello\n'`). Without `text=True` you get bytes.
- **Exit code:** `r.returncode` is the program's exit status, **0 for success**, nonzero for failure (`false` exits 1). This is the Unix convention, and checking it is how you know whether the command worked.
- **`check=True`** turns a nonzero exit into a raised `CalledProcessError`, so failures are loud (an exception) rather than a silently-ignored return code, the right default for "this command must succeed."
- **`input=`** pipes data to the program's stdin (`wc -c` counts the 5 bytes of `"12345"`), so you can feed a program without a temporary file.

The **arguments-as-a-list** form is the security-critical detail.
`["python3", "-c", "print(6 * 7)"]` execs the program with those exact arguments, each passed *literally*, with **no shell** involved.
So a filename or user input in the list cannot be interpreted as shell syntax, an argument like `"; rm -rf /"` is just a (harmless) literal string argument, not a command.
This is why the list form is the default and correct way to call `subprocess`, and why `shell=True` (which passes the command to a shell for parsing) is dangerous on any input you do not fully control.

---

## 52.2 Safety and streams

Two aspects of `subprocess` deserve their own emphasis because getting them wrong is either a security hole or a hang.

**Never use `shell=True` with untrusted input.**
`shell=True` runs your command string through the system shell, which interprets metacharacters (`;`, `|`, `$(...)`, `&&`, redirects). So `subprocess.run(f"convert {filename} out.png", shell=True)` with `filename = "x.png; rm -rf ~"` executes the `rm`, a **shell-injection** remote-code-execution vulnerability, exactly the class of bug that tops security advisories.
The fix is the list form (§52.1): `subprocess.run(["convert", filename, "out.png"])` passes `filename` literally, so no metacharacter is interpreted.
Use `shell=True` only for a fixed, trusted command where you genuinely need shell features (a pipeline, a glob), never with interpolated input, and if you must interpolate, `shlex.quote` each part (and even then, prefer the list form). The rule: **list arguments by default; `shell=True` is a last resort for trusted, fixed commands.**

**Streams and deadlock.**
A subprocess has stdin, stdout, and stderr, and mishandling them is the classic `subprocess` hang.
If you use `subprocess.Popen` (the low-level API) and write to the child's stdin while it writes to stdout, and you do not drain stdout, the child can *block* writing to a full pipe buffer while you block writing to its stdin, a **deadlock** (the same shape as the coordination deadlocks of Chapters 46-47).
`subprocess.run` and `Popen.communicate()` handle this correctly (they drain all streams), which is why `run`/`communicate` are strongly preferred over manually reading/writing `Popen` pipes.
So: **use `subprocess.run` (or `communicate`) rather than hand-managing `Popen` pipes**, and reach for `Popen` only when you need streaming interaction (reading output line-by-line as it is produced), handling the draining yourself.

`subprocess.run` also supports `timeout=` (kill the process if it runs too long, essential for untrusted or possibly-hanging commands), `cwd=` (working directory), and `env=` (environment), the controls you need to run external programs robustly.

---

## 52.3 Measurement: spawning is expensive

**Methodology.** `code/ch133/bench_subprocess.py`.
The cost of `subprocess.run(["true"])` (spawning a trivial external program) versus an in-process `os.getpid()`.
Wall-clock over 300 iterations.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | time | vs in-process |
|---|---|---|
| in-process `os.getpid()` | 61 ns | 1x |
| `subprocess.run(["true"])` | 1989 us (~2 ms) | **~32,000x** |

Spawning even the trivial `true` program costs **~2 milliseconds** (~32,000x an in-process call; ~53,000x on 3.14.6).
The cost is what a subprocess *does*: the OS **forks** the process, **execs** a new program image (loading the executable, linking, initialising), wires up **pipes** for its stdio, runs it, and **waits** for it to exit and reap it. That is a lot of kernel work for what may be a microsecond of actual computation.

The lesson is the volume's amortization rule at the **process-spawn** boundary.
Calling a subprocess *per item* in a loop, a thousand items, a thousand spawns, is *seconds* of pure overhead (a thousand times 2 ms), often dwarfing the work itself.
So:

- **Prefer a Python library over shelling out.** If a library does the job in-process, use it, do not spawn `grep` to search text (use `re` or `str` methods), do not spawn `curl` to fetch a URL (use `httpx`/`urllib`), do not spawn `jq` to parse JSON (use `json`). The library avoids the 2 ms spawn *and* the parsing of the tool's text output.
- **If you must call an external tool, call it once over a batch.** Pass *all* the inputs in one invocation (a whole file, a list of arguments) rather than spawning the tool per input. `grep pattern file` (one spawn over the whole file) not a spawn per line; `ffmpeg` once over a playlist not per frame.
- **The subprocess is worth it for genuinely external, coarse work:** running a compiler, a video transcode, a `git` operation, a whole separate program that does substantial work per invocation. There the 2 ms is negligible next to seconds of real work.

This mirrors every boundary in Deep E and Deep M: the FFI call (Chapter 43), the process pool task (Chapter 48), the pickled argument (Chapter 47), and now the subprocess spawn, each is a boundary with a fixed cost, so **cross it rarely with a lot of work each time**.
`subprocess` is glue for coarse-grained external work, not a substitute for doing the work in Python, and the ~2 ms spawn cost is the number that decides where that line falls.

---

## 52.4 Edges and failure modes

**`shell=True` with untrusted input is a security hole.** §52.2.
It enables shell injection (RCE). Use the list form; reserve `shell=True` for fixed, trusted commands, and even then prefer the list form.

**Spawning per item is a performance anti-pattern.** §52.3.
~2 ms per spawn. Prefer a library, or call the tool once over a batch. Never spawn a subprocess in a tight loop.

**Manual `Popen` pipes deadlock.** §52.2.
Writing stdin while not draining stdout can block both sides. Use `subprocess.run`/`communicate` (which drain correctly); use `Popen` only for streaming, and handle draining.

**Always set a `timeout` for untrusted or hangable commands.**
A subprocess with no timeout can hang forever (waiting on input, an infinite loop). `subprocess.run(..., timeout=...)` raises `TimeoutExpired` and kills the process.

**Check the return code (or use `check=True`).**
Ignoring `returncode` means a failed command passes silently. Use `check=True` to fail loudly, or inspect `returncode` explicitly.

**`text=True` versus bytes.**
Without `text=True` (or `encoding=`), stdout/stdin are bytes. Binary output (an image, a compressed stream) must stay bytes; text output is more convenient as `str`. Choose per the data, and know a wrong encoding assumption corrupts text (Deep D).

**The child inherits (or is given) an environment and cwd.**
By default the child inherits the parent's environment and working directory. For reproducibility or isolation, pass `env=` and `cwd=` explicitly. A command that works interactively but fails from Python is often an environment difference (`PATH`, etc.).

**`subprocess` is not `multiprocessing`.**
`subprocess` runs external *programs* (any executable, communicating via pipes/exit codes); `multiprocessing` runs Python *functions* in child interpreters (communicating via pickling/shared memory). Use `subprocess` to orchestrate tools, `multiprocessing` to parallelize Python.

---

## 52.5 Connections

**Backward.**
`subprocess` runs external programs where `multiprocessing` (Chapter 47) runs Python workers, both are child processes with the fork/exec and pipe machinery. The spawn cost is the OS process creation underlying Chapter 47's worker startup. Text-versus-bytes output is Deep D (encodings). The deadlock hazard is the pipe/coordination deadlock of Chapters 46-47.

**Forward.**
`Popen` and streaming interaction, pipes, and the lower-level OS process/IPC APIs (`os.fork`, `os.pipe`, `os.exec*`) are Deep R (OS/IPC). `asyncio.create_subprocess_exec` (running subprocesses without blocking) is Deep F. `shlex` (safe command parsing/quoting) is a Deep Q/security topic. The amortization rule is shared with Chapters 43-51.

**Across books.**
`subprocess` is **Book I**'s tool for orchestrating external systems: invoking a compiled pricing engine, running a `git` operation for reproducibility, calling a vendor CLI, launching a data-processing tool. The order-book system uses `subprocess.run` with list arguments (never `shell=True` on any external input) to call the few external tools it depends on, always with a `timeout` and a checked return code, and it calls each tool *once over a batch* (a whole dataset per invocation) rather than per record, respecting the §52.3 spawn cost, and it prefers in-process Python libraries wherever one exists, reserving subprocess for genuinely external programs, the glue-not-substitute discipline this chapter prescribes.

---

## 52.6 Exercises

**1. Run and check.** Reproduce §52.1: run a command, capture output, inspect the return code, use `check=True` to raise on failure, and pipe input. Explain what each part of the result object tells you.

**2. Prevent injection.** Write a function that runs an external tool on a user-supplied filename. Do it with the list form and show that a malicious filename (`"x; rm -rf ~"`) is harmless. Then do it with `shell=True` and show the injection. Explain the difference.

**3. Measure the spawn.** Reproduce §52.3. Confirm a subprocess costs ~2 ms. Then write two versions of a task, one spawning a tool per item, one calling it once over a batch, and measure. Explain the amortization.

**4. Avoid the hang.** Write a `Popen` that writes a lot to a child's stdin without draining stdout and observe (or reason about) the deadlock. Fix it with `communicate`. Explain the pipe-buffer deadlock.

**5. The design question.** `subprocess` makes it trivial to shell out to external tools, which is powerful glue and a temptation to overuse. Argue when shelling out is right (coarse external work) versus when a Python library is better (§52.3), and why the list-argument form should always be the default over `shell=True`.

---

## 52.7 Summary and cross-references

- **`subprocess.run`** runs **external programs** (any executable) and captures **output** (`capture_output=True, text=True`), **exit code** (`returncode`, 0 = success; `check=True` raises on failure), and pipes **input** (`input=`). It complements `multiprocessing` (Python workers) with external tools.
- **Pass arguments as a LIST** (`["cmd", "arg"]`): execs directly, **no shell, no injection**. **`shell=True` with untrusted input is a shell-injection (RCE) hole**, reserve it for fixed, trusted commands.
- **Use `run`/`communicate`, not hand-managed `Popen` pipes** (which deadlock on undrained streams). Always set a **`timeout`** for hangable commands; check the return code.
- **Measured:** spawning even `true` costs **~2 ms** (~32,000x an in-process call), because it forks, execs a new program, wires pipes, and waits. **Never spawn a subprocess per item**, prefer a Python library, or call the tool once over a batch (amortize the spawn boundary).
- **Edges:** `text=True` vs bytes; child inherits env/cwd (pass explicitly for reproducibility); `subprocess` runs programs, `multiprocessing` runs Python functions.

**Cross-references.** Python worker processes → Chapter 47. Text vs bytes output → Deep D. `Popen`, pipes, OS IPC → Deep R. `asyncio` subprocesses → Deep F. Amortize the boundary → Chapters 43-51. `shlex` (safe quoting) → Deep Q.
