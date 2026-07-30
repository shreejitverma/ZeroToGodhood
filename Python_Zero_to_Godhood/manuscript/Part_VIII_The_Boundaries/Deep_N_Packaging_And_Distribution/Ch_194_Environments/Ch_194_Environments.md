# Chapter 113: Environments

Chapters 109 through 112 kept deferring one question: extract *where*? This chapter is the answer's whole mechanism, and it is smaller than its reputation: **a virtual environment is three files and a prefix rule.** At startup, the interpreter looks for `pyvenv.cfg` next to its executable; finding one, it sets `sys.prefix` to that directory while `sys.base_prefix` keeps pointing at the real installation, and the venv's `site-packages` is what lands on `sys.path`. No stdlib copies, no registry, and no shell magic, `activate` only edits `PATH` for your prompt's convenience, which the listing proves by never using it: four subprocess probes run the venv's interpreter *by path*, and the isolation works completely.

The listing creates a real venv offline (`with_pip=False`), prints the `pyvenv.cfg` keys, proves the prefix split from inside (`sys.prefix != sys.base_prefix : True`), installs Chapter 109's hand-built wheel by extraction into the venv's site-packages, `42` inside, `ImportError` in base, and demonstrates `.pth` files, `site`'s extension point and the mechanism under editable installs.

The benchmark reframes environments as a performance topic. Creation is **5.3 ms**, disposable by construction. The *empty venv starts faster than the base interpreter* (9.1 vs 11.9 ms), because the base drags a populated site-packages through `site` processing, the lean-environment argument in vivo. And the path toll prices clutter per import: **~23 us of stat calls per junk `sys.path` entry, on every cold import of every process**.

**This is a Deep N chapter.**
Deep G owns the finders that walk `sys.path`; the `site` module's startup role is Deep S's territory used here. This chapter owns the environment as an artifact: what it is, what it costs, and why modern workflows treat it as disposable.

## Section index

- **113.1** Three files and a prefix rule, proven
- **113.2** The model: prefixes, `site`, and `.pth`
- **113.3** Measurement: creation, startup, and the path toll
- **113.4** Edges and failure modes
- **113.5** Connections
- **113.6** Exercises
- **113.7** Summary and cross-references

Listings live under `code/ch194/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 113.1 Three files and a prefix rule, proven

```python
# code/ch194/l01_what_a_venv_is.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- creation: what venv.create actually writes ---
  pyvenv.cfg keys : ['command', 'executable', 'home', 'include-system-site-packages', 'version']
  bin/python exists (symlink on most platforms, a small COPY
  on macOS framework builds - never a second stdlib) : True
  site-packages exists and is empty : True
  a config file, a launcher, an empty directory: the environment
  is METADATA, and the interpreter does the rest at startup
--- the prefix split, proven from inside ---
  sys.prefix != sys.base_prefix : True
  venv site-packages on sys.path: True
  the stdlib still comes from base_prefix (never copied);
  site-packages comes from the venv; two prefixes, one rule
--- isolation, both ways ---
  import tinypkg in the venv : 42
  import tinypkg in base     : ImportError
  installing was extraction under the venv's prefix (Chapter
  109), and the base interpreter cannot see it - isolation is
  nothing but sys.path arithmetic
--- .pth files: site's extension point ---
  module reachable only via .pth : via-pth
  each line of a .pth in site-packages is appended to sys.path
  by the site module at startup - the mechanism under editable
  installs (Chapter 109's shims) and path-manipulating tools
```

**The creation block is an inventory, and the inventory is tiny.**
`pyvenv.cfg` (whose `home` key points at the real installation), a launcher (symlinked on most platforms, *copied* on macOS framework builds, the listing states both because the first draft asserted "symlink" and the machine said otherwise), and an empty `site-packages`. The stdlib is never copied: the environment is metadata, and the interpreter's startup logic does the rest, which is why creation costs 5.3 ms and why environments are cheap enough to be per-project, per-CI-job, per-experiment.

**The prefix split is the entire mechanism, and it is testable from inside.**
`sys.prefix != sys.base_prefix : True` is the venv detected; the stdlib resolves against `base_prefix`, site-packages against `prefix`. Every tool question ("which environment am I in?") reduces to these two variables, and every environment bug reduces to which interpreter *actually ran*, which is why the listing's by-path subprocess technique is also the right debugging technique.

**Isolation both ways closes Chapter 109's loop.**
Install-by-extraction under the venv's prefix; `42` inside, `ImportError` outside. No installer participated, isolation is `sys.path` arithmetic, and knowing that converts "my package disappeared" from mystery to `print(sys.path)`.

**And `.pth` files are the documented backdoor.**
A text file in site-packages whose lines are appended to `sys.path` by `site` at startup, `via-pth` proves it. This is the load-bearing mechanism under editable installs and development tools, and (as §113.4 notes) `.pth` lines beginning with `import` *execute*, which makes the backdoor also a supply-chain surface (Chapter 116).

---

## 113.2 The model: prefixes, `site`, and `.pth`

**Startup's environment logic runs in a fixed order.**
The launcher's location is found; `pyvenv.cfg` beside it is read (`home` locating the base); prefixes are set; then the `site` module runs: it computes the site-packages for `sys.prefix`, appends it, processes every `.pth` there, and honours `include-system-site-packages` (the cfg key that lets a venv *see through* to base's packages, off by default, and the right default). Everything observable in §113.1 is this sequence's output, and `-S` (skip `site`) is the diagnostic that isolates it.

**The venv is one species of a general mechanism.**
`sysconfig`'s installation schemes define where things go for *any* prefix; a venv is a prefix with a cfg file; conda environments are prefixes with their own convention; relocatable app bundles are prefixes found relative to the binary. Tools that respect `sysconfig.get_paths()` work in all of them, and tools that hardcode `/usr/lib/python...` are the ones that break in any of them.

**`activate` deserves its demotion, explicitly.**
It prepends the venv's `bin` to `PATH` and sets `VIRTUAL_ENV`; deactivation undoes it. Nothing about *isolation* involves it, the listing never activated anything, which is why CI, cron jobs, shebangs, and IDEs should invoke `venv/bin/python` directly, and why "it works when I activate" always means "PATH found a different interpreter", never anything deeper.

**Build isolation (Chapter 111) is this chapter applied recursively**: the frontend creates a disposable environment, installs `[build-system] requires` into it, and runs the backend with that venv's interpreter. The 5.3 ms creation cost is why the strategy is affordable; caching of build environments is why it is fast in practice; and the same disposability underwrites Chapter 114's workflow, where the environment is a *derived artifact* of the lockfile, deleted and rebuilt without ceremony.

---

## 113.3 Measurement: creation, startup, and the path toll

**Methodology.** `code/ch194/bench_environment_costs.py`.
`min` of 5 (9 for subprocess rows); 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Creation**: `venv.create(with_pip=False)` costs **5.3 ms**. (`with_pip=True` adds a full pip bootstrap and dominates by orders of magnitude, which is why modern tools install pip once and link it, or skip it and install with an external tool.)

**b. Startup**:

| interpreter | `python -c pass` |
|---|---|
| base (populated site-packages) | 11.9 ms |
| venv (empty site-packages) | **9.1 ms** |

**c. The path toll**, first import behind N junk `sys.path` entries:

| junk entries | first import |
|---|---|
| 0 | 78 us |
| 10 | 326 us |
| 50 | 1,255 us |
| 200 | 4,696 us |

**The startup table's inversion is the chapter's best argument.**
The venv pays the `pyvenv.cfg` probe *and still wins*, because the base interpreter drags a populated site-packages through `site` processing at every start. Environment overhead is not the venv; it is the *contents*, and an empty room is faster than a full one even when the empty room is rented.

**The path toll generalises it per import.**
~23 us per junk entry per cold import: the finders (Deep G) stat their way down `sys.path` in order for every module not yet cached, so clutter is a tax multiplied by (modules imported) x (processes started). Together with Chapter 109's `entry_points()` scan, this is the measured case that **a small environment is a performance feature**: fewer entries, fewer distributions, faster starts, cheaper scans, and (Chapter 112) smaller resolution frontiers. Hygiene arguments age poorly; multiplication tables do not.

**Book I**'s parallels are exact: chroots/containers as "prefixes with metadata", `LD_LIBRARY_PATH` length as the same per-load toll, and its deployment chapter's rule, ship the minimal closure, is this section with `ldd` in place of finders.

---

## 113.4 Edges and failure modes

**The wrong interpreter is ninety percent of environment bugs.**
`pip` on `PATH` belonging to one Python, `python` to another; an IDE remembering an old venv; a shebang bypassing everything. The diagnostic is always the same triple, `sys.executable`, `sys.prefix`, `sys.base_prefix`, printed from *inside the failing process*, and the listing's by-path invocation is the pattern that makes the question unaskable.

**Venvs do not survive their base moving.**
`pyvenv.cfg`'s `home` is an absolute path: upgrade or relocate the base interpreter and the venv half-breaks (launcher may resolve, stdlib may not, or versions skew). The modern answer is not repair but §113.2's disposability: delete, recreate from the lock. Treat venvs as cache, never as state.

**`include-system-site-packages` reintroduces every problem it inherits.**
The flag makes base's packages visible *behind* the venv's own, version shadowing, surprise imports, and resolution (Chapter 112) computing against a world that differs from runtime. It exists for heavyweight system packages (GPU stacks); use it knowingly or not at all.

**Executable `.pth` lines run at every startup of every process in that environment.**
A line starting with `import` executes arbitrary code during `site` processing, before your first statement. Legitimate uses exist (coverage hooks, editable-install shims); the audit, `grep -r '^import' site-packages/*.pth`, belongs in Chapter 116's supply-chain checklist, and the mechanism is why "just installing" a hostile package can own the interpreter without ever being imported.

**`--user` installs are a third prefix that predates venvs.**
User site (`~/.local/...`) is searched for *non-venv* interpreters and silently ignored inside venvs (by default), a common "where did my package go" when switching workflows. `python -m site` prints the truth for the interpreter that runs it.

**And the free-threaded build keeps its own environments.**
A venv is bound to the interpreter that created it, `cp314t`'s environments carry the `t` ABI world (Chapter 110's disjoint universe) down to every wheel installed within. The matrix discipline this book runs, one venv per interpreter per purpose, is the same discipline production needs.

---

## 113.5 Connections

**Backward.**
Extraction targets and dist-info (this chapter supplies the *where* for Chapter 109's *what*); build isolation's disposable environments (Chapter 111); resolution computing against an environment's contents (Chapter 112). The finders that make `sys.path` matter are Deep G; `site` and startup sequencing are Deep S.

**Forward.**
Lockfiles make environments derived artifacts, Chapter 114, this chapter's disposability is its premise. Compiled wheels install per-ABI into per-interpreter environments, Chapter 115. The `.pth` execution surface joins the trust story, Chapter 116.

**Across books.**
A venv is a chroot that only chroots `sys.path`; a container is the same idea with the OS included; **Book I**'s deployment chapter walks `RPATH`/`RUNPATH` as its `pyvenv.cfg` and reaches the identical operational rule: environments are build outputs, rebuilt from manifests, never hand-tended pets.

---

## 113.6 Exercises

**1. Break it by moving it.** Create a venv, move the *base* interpreter (or the venv itself), and catalogue exactly what breaks and what survives, against `pyvenv.cfg`'s contents. Then implement the correct fix (recreate) as a one-line make target.

**2. The `-S` bisection.** Take any environment mystery (a shadowed import, a surprise module) and bisect with `python -S` and `python -m site`. Write the four-step runbook you actually used.

**3. Executable `.pth` audit.** Write the auditor: list every `.pth` in an environment, flag executable lines, and diff against a fresh venv. Run it on your largest real environment and report findings.

**4. Price `with_pip`.** Measure `venv.create` with and without pip; then measure uv's or virtualenv's creation. Attribute the differences (seed packages? symlink farms?) and state when each tool's trade is right.

**5. Reproduce the inversion.** Measure §113.3b's startup pair on your machine, then progressively fill the venv's site-packages (10, 50, 200 distributions from Chapter 109's generator) and plot startup against contents. Find your environment's slope.

**6. The design question.** `pyvenv.cfg` is read by the *interpreter binary* itself (PEP 405), not by Python code, which is why isolation needs no activation but also why the mechanism is frozen per interpreter version. Argue the alternative that lost, a `site`-only, pure-Python mechanism (as virtualenv originally shipped): what binary-level detection buys (correct `sys.executable`, no bootstrap paradox, `-S` still isolated), what it cost (venvs bound to bases, the moving edge above), and why PEP 405 chose the binary. Then design the *relocatable* venv (cfg with relative `home`?) and enumerate which of this chapter's proofs would break.

---

## 113.7 Summary and cross-references

- **A venv is three files and a prefix rule**: `pyvenv.cfg` beside the launcher flips `sys.prefix` while `sys.base_prefix` keeps the stdlib; the venv's site-packages joins `sys.path`; `activate` is PATH cosmetics, and the listing proves isolation both ways without it.
- **`site` is the runtime half**: it appends site-packages, processes `.pth` files (lines join `sys.path`; `import` lines *execute*, a supply-chain surface), and honours system-site passthrough. `sysconfig` schemes make venvs one species of a general prefix mechanism.
- **Measured**: creation **5.3 ms** (disposable by construction); the **empty venv starts faster than the populated base** (9.1 vs 11.9 ms), site processing of contents is the real overhead; and clutter costs **~23 us per junk path entry per cold import**, small environments are a performance feature, compounding with Chapter 109's scans and Chapter 112's frontiers.
- **The edges**: wrong-interpreter bugs (print the prefix triple from inside), venvs die when bases move (rebuild, never repair), system-site passthrough reintroduces shadowing, user-site is a third prefix, and `t`-build environments are their own ABI universe.

**Cross-references.** Extraction and dist-info → Chapter 109. Build isolation → Chapter 111. Resolution's environment → Chapter 112. Lockfiles and disposability → Chapter 114. Per-ABI wheels → Chapters 110, 115. `.pth` in the trust story → Chapter 116. Finders → Deep G. `site` at startup → Deep S.
