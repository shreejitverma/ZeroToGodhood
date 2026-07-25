# Chapter 83: Mocking

Two mocking mistakes waste more debugging time than any others, and both produce a *passing* test that proves
nothing. The first is patching the wrong target: you `mock.patch("clock.now")` to fake the clock, run the test,
and it still gets the real time, because the code under test did `from clock import now` and holds its *own*
reference `app.now`, patching `clock.now` (where it is *defined*) never touches it. You must patch
`app.now` (where it is *used*). The second is trusting a bare `Mock`: it accepts *any* call, `m(1, 2, 3,
key="x")` succeeds no matter what the real function's signature is, so a test passes against a mock that no
longer matches the code, a false green that survives a refactor. `create_autospec` fixes this by constraining the
mock to the real signature (a wrong call raises `TypeError`), at **32x** the creation cost of a bare `Mock`,
negligible for test setup and worth it for the bugs it catches.

This chapter continues **Deep O** with mocking: where to patch, why bare mocks hide signature bugs, and the
autospec fix. It is a testing chapter about the failure mode unique to mocks, tests that pass while testing
nothing.

## Section index

- **83.1** Patch where used; spec the mock
- **83.2** Why bare mocks lie
- **83.3** Measurement: the cost of autospec
- **83.4** Edges and failure modes
- **83.5** Connections
- **83.6** Exercises
- **83.7** Summary and cross-references

Listings live under `code/ch083/` and are re-executed by `make verify` on both interpreters.

---

## 83.1 Patch where used; spec the mock

```python
# code/ch083/l01_mocking.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- patch where DEFINED (clock.now): no effect on app ---
  app.timestamp() : 'at REAL-TIME'  (still real: app has its own 'now')
--- patch where USED (app.now): works ---
  app.timestamp() : 'at FAKE'  (mocked)
--- a bare Mock accepts ANY call (hides signature bugs) ---
  bare Mock accepted 4 args : True
--- autospec constrains the mock to the real signature ---
  autospec accepted 0 args  : True
  autospec rejected 3 args  : True  (a bare Mock would not)
```

The **patch-target** rule follows from how names bind (Chapters 2-3, 67). `svc/app.py` does `from svc.clock
import now`, which copies the *reference* `now` into `app`'s namespace, `app.now` and `clock.now` are two names
for the same function object, but they are *independent bindings*. Patching `clock.now` rebinds the name in
`clock`'s namespace, but `app` still holds its own `app.now`, so `app.timestamp()` still calls the real one
(`'at REAL-TIME'`). Patching `app.now`, the name the code under test actually *looks up*, works (`'at FAKE'`).
The rule: **patch the name in the module that uses it, not the module that defines it.**

The **autospec** rule addresses a subtler lie. A bare `Mock` accepts *any* call, `m(1, 2, 3, key="anything")`
succeeds, so if the code calls the mocked function wrongly (or the real function's signature changed and the code
was not updated), the mock happily passes. `create_autospec(app.timestamp)` builds a mock *constrained to the
real signature*: `app.timestamp()` takes no arguments, so the autospec mock *accepts* a zero-argument call and
*rejects* `spec(1, 2, 3)` with `TypeError`, exactly as the real function would. The test now fails when the call
does not match reality.

---

## 83.2 Why bare mocks lie

A mock's job is to *stand in* for a real object, and a bare `Mock` stands in for *anything*: every attribute
access returns a new mock, every call succeeds and returns a mock, with no constraints. That flexibility is
convenient and dangerous. It means a mock can pass calls the real object would *reject*, and can have attributes
the real object does *not have*. So a test using a bare mock verifies that your code *ran*, not that it used the
dependency *correctly*.

The failure this causes is insidious because it appears during *maintenance*, not authoring. You write code and
a test with a bare mock; both pass. Later, someone renames the real function's parameter, or changes its
signature, or the code starts calling a method the dependency no longer has. The *real* integration is now
broken, but the *test still passes*, because the bare mock accepts the now-wrong calls. The test has decoupled
itself from reality; it is green while production is red. This is the deepest hazard of mocking, over-mocked
tests that test the mock's behavior instead of the code's contract with its dependency.

`create_autospec` (and `spec=`/`spec_set=` on `Mock`/`patch`) reconnects the mock to reality by copying the
real object's *interface*: the autospec mock has the same attributes and the same call signatures, so a call the
real object would reject, the autospec rejects too, and an attribute the real object lacks raises
`AttributeError`. This turns "the test passed" back into "the code used the dependency correctly". The rule:
**spec your mocks (`autospec`/`spec=`) whenever they stand in for a real callable or object**, so that a change
to the real interface *fails the test* instead of silently passing. Reserve bare `Mock`/`MagicMock` for genuinely
shapeless stand-ins (a sentinel, a throwaway callback) where there is no real signature to honor.

---

## 83.3 Measurement: the cost of autospec

**Methodology.** `code/ch083/bench_autospec.py`. Creating a bare `mock.Mock()` versus `mock.create_autospec(target)`
for a function with a real signature. `min` per call; ratio relative to `Mock`. CPython 3.13.5, Apple M3 Pro,
macOS 27.0, arm64.

| create a mock | min per call | ratio |
|---|---|---|
| `mock.Mock()` | **6,217 ns** | 1.00x |
| `mock.create_autospec(target)` | **200,550 ns** | **32.3x** |

`create_autospec` is **32x** a bare `Mock`, ~200 us versus ~6 us, because it *introspects* the target (reads its
signature, attributes, and members) to build a constrained mock, while `Mock()` builds an empty do-anything
object. In *absolute* terms 200 us is significant per mock, but it is a *test-setup* cost, paid a handful of
times per test, not in a hot loop, so a test that creates a few autospec mocks pays sub-millisecond, invisible
against the test's own work.

The rule: **pay for autospec; it catches a class of bugs a bare mock hides.** The 32x is a per-mock-creation
cost that does not scale with anything in production (mocks exist only in tests), and the correctness it buys,
tests that fail when the real interface changes, is exactly what makes a test *trustworthy*. Reach for a bare
`Mock` only when there is no real signature to honor (a shapeless stand-in) or in the rare case you create so
many mocks that 200 us each is measurable, where you would reconsider the test design anyway. As across Deep O,
the small, bounded cost buys a real guarantee, here, that a green test means the code is correct, not merely that
it ran.

---

## 83.4 Edges and failure modes

**Patching where defined, not used.** §83.1. `from mod import name` binds a separate reference; patch the name in
the *using* module. (Patching the *module attribute* `import mod; mod.name(...)` is why `import mod` style is
more patch-friendly than `from mod import name`.)

**Bare mocks passing wrong calls.** §83.2. A `Mock` accepts any call and any attribute, so tests survive
interface changes that break production. Use `autospec`/`spec=` for real stand-ins.

**Over-mocking.** Mocking everything (including code you own) tests the mocks, not the integration. Mock only the
*boundaries* you cannot control (network, time, external services); prefer real objects for code under test, or
an integration test.

**Not asserting the interaction.** A mock records calls; a test that mocks a dependency but never asserts *how it
was called* (`assert_called_once_with(...)`) only checks that code ran, not that it used the dependency correctly.
Assert the interaction, ideally with an autospec mock so the asserted call is signature-valid.

**Leaking patches.** A `patch` not undone (a manual `start()` without `stop()`, or patching outside a
`with`/decorator/fixture) leaks the mock into other tests, an isolation failure (Chapter 81). Use `patch` as a
context manager, decorator, or fixture so it is always undone.

**Mocking a method vs the instance.** Patching a class method affects all instances; patching an instance
attribute affects one. Know which scope you mean, and prefer patching the specific name the code under test
resolves.

---

## 83.5 Connections

**Backward.** The name binding that makes patch-target matter, `from x import y` copying a reference, is Chapters
2-3 (namespaces) and 67 (import). Test isolation (patches must be undone) is Chapter 81. The signature
introspection `autospec` performs is Chapter 49 (`inspect`).

**Forward.** Dependency injection (passing dependencies in rather than importing them) reduces the need for
patching and is a design topic. Fakes and test doubles beyond mocks (in-memory implementations) are Deep O
testing material. Contract/integration testing that verifies the *real* boundary is the complement to mocking.

**Across books.** Correctly-scoped, spec'd mocks are how Book II tests the seams into **Book III** without
letting tests drift from reality. A **Book III** test mocks the *external* boundaries (a model API, a vector
store, a clock) with `autospec` so a change to those interfaces fails the test, and uses real objects for its own
logic, so green tests mean the integration is correct, not merely exercised. The §83.2 false-green is exactly the
maintenance-time rot, tests passing while production breaks, that **Deep U** guards against in the CI pipeline.

---

## 83.6 Exercises

**1. Fix the patch target.** Reproduce §83.1: patch a function where it is defined (no effect) and where it is
used (works), for code that did `from mod import func`. Explain the two independent name bindings.

**2. Expose the false green.** Write a test with a bare mock that passes, then change the real function's
signature, and show the test *still* passes (wrongly). Switch to `autospec` and show it now fails. Explain the
maintenance hazard.

**3. Measure autospec.** Run §83.3's benchmark and confirm `create_autospec` is far costlier than `Mock`. Explain
what it introspects and why the cost is negligible for test setup.

**4. Assert the interaction.** Mock a dependency, call the code, and assert *how* the dependency was called
(`assert_called_once_with`) using an autospec mock. Explain why asserting the interaction (not just the result)
matters, and why the assertion should be signature-valid.

**5. The design question.** Bare mocks are flexible; autospec mocks are faithful. Argue when to use each, and why
over-mocking is a test smell. Your answer must use the §83.3 cost, the §83.2 false-green, and distinguish mocking
external boundaries from mocking code you own.

---

## 83.7 Summary and cross-references

- **Patch where a name is *used*, not where it is *defined*:** `from mod import func` binds a separate reference
  in the using module, so patch `using_module.func`, not `mod.func`.
- A **bare `Mock` accepts any call and attribute,** so tests pass even when the code calls the dependency wrongly
  or the real interface changed, a **false green**. **`create_autospec`/`spec=`** constrains the mock to the real
  signature, so wrong calls fail.
- **Measured:** `create_autospec` is **32x** a bare `Mock` (200 us vs 6 us) because it introspects the target;
  negligible for test setup, and it buys tests that fail when the real interface changes.
- **Mock only boundaries you do not control;** assert *how* dependencies were called; always undo patches
  (context manager/decorator/fixture) to preserve isolation.

**Cross-references.** Name binding and namespaces → Chapters 2-3, 67. Test isolation and patch cleanup → Chapter
81. Signature introspection (`inspect`) → Chapter 49. Integration testing and DI → Deep O. The CI seam → Deep U.
