# Chapter 81: Fixture Scope and Isolation

A test suite loads a database, seeds it, and connects, in `setUp`, so *every* test starts from a clean state.
It is correct, and it is slow: with the fixture rebuilt before each of the class's tests, a class of 10 tests
pays the expensive setup **10 times**. Measured, that per-test setup runs **9.7x** the cost of building the
fixture *once* in `setUpClass` and sharing it. The obvious fix, move the fixture to shared scope, is faster but
opens a second trap: shared fixtures are *shared mutable state*, so if one test mutates the fixture, later tests
see the change, an order-dependent leak that makes a test pass or fail depending on what ran before it. Fixture
scope is a genuine trade-off between **isolation** (per-test, correct, slow) and **speed** (shared, fast,
leak-prone), and choosing wrongly gives you either a slow suite or a flaky one.

This chapter continues **Deep O** with test fixture scope and isolation: how per-test and shared setup differ in
cost and safety, why the per-test cost scales with the test count, and how to get speed without leaks. It is a
testing chapter with a measured finding and a correctness caveat, both essential to a healthy suite.

## Section index

- **81.1** Per-test vs shared setup
- **81.2** Isolation vs speed
- **81.3** Measurement: setup cost scales with test count
- **81.4** Edges and failure modes
- **81.5** Connections
- **81.6** Exercises
- **81.7** Summary and cross-references

Listings live under `code/ch081/` and are re-executed by `make verify` on both interpreters.

---

## 81.1 Per-test vs shared setup

```python
# code/ch081/l01_fixture_scope.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- how often the fixture is built ---
  setUp (per-test)   called : 2 times (once per test)
  setUpClass (shared) called: 1 time (once total)
--- isolation ---
  per-test scope  : each test gets a fresh fixture (no leak)
  shared scope    : test_2 saw test_1's mutation [1, 2, 3, 99] (a leak)
--- the trade ---
  per-test setUp   : isolated, but pays the setup cost N times
  shared setUpClass: pays it once, but tests must NOT mutate shared state
```

`setUp` runs before **every** test method (per-test scope): the counter shows it called twice for the two-test
class, so each test gets a *fresh* fixture. `setUpClass` runs **once** for the whole class (shared scope): called
one time, its fixture reused by all tests. That is the cost axis, per-test builds N times, shared builds once,
measured in §81.3.

The isolation block is the safety axis, and it is where the danger lives. In the *per-test* class, `test_1`
appends `99` to its `items` list, but `test_2` sees the original `[1, 2, 3]`, because each test got its own list.
In the *shared* class, `test_1` mutates the *one* shared list, and `test_2` (running after it, unittest orders
tests alphabetically) sees the leaked `[1, 2, 3, 99]`. The shared fixture carried `test_1`'s mutation into
`test_2`, a test that passes or fails depending on execution order.

---

## 81.2 Isolation vs speed

The two scopes sit at opposite ends of a trade every suite must navigate.

**Per-test scope** (`setUp`, or a function-scoped pytest fixture) gives **isolation**: each test starts from a
freshly built fixture, so tests cannot affect each other, and a test's result depends only on that test. This is
the *correct default*, isolation is what makes tests independent, reorderable, and trustworthy, and a failing
test points at *itself*, not at whatever ran before. The cost is that an expensive fixture is rebuilt for every
test.

**Shared scope** (`setUpClass`/`setUpModule`, or class/module/session-scoped pytest fixtures) gives **speed**:
the fixture is built once and reused. The cost is that the fixture is now *shared mutable state*, and mutation
leaks between tests (§81.1), reintroducing exactly the coupling isolation was meant to prevent. A shared fixture
is safe *only* if tests treat it as read-only, or if it is reset between tests.

The rule: **default to per-test isolation; move a fixture to shared scope only when it is both expensive and
safely shareable** (read-only, or reset in `setUp`/a teardown). "Expensive" means the setup cost is a real
fraction of the suite's runtime (a database, a large data load, a compiled resource, a network connection);
"safely shareable" means no test mutates it, or a per-test reset restores it. When a fixture is cheap, always use
per-test scope, the isolation is free. When it is expensive but tests mutate it, keep per-test scope and optimize
the fixture itself (an in-memory database, a smaller dataset, a shared *connection* with per-test *transactions*
rolled back). Never trade isolation for speed silently; a leak is a flaky test waiting to fail in CI when the
order changes.

---

## 81.3 Measurement: setup cost scales with test count

**Methodology.** `code/ch081/bench_fixture.py`. A class of 10 tests with an expensive fixture, built per-test
(`setUp`) versus shared (`setUpClass`). `min` over runs (the suite is rebuilt each run, because a `TestSuite`
drops its tests after running). CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 10 tests, expensive fixture | min per run | ratio |
|---|---|---|
| shared `setUpClass` (1 setup) | **5.8 ms** | 1.00x |
| per-test `setUp` (10 setups) | **56.9 ms** | **9.7x** |

Per-test setup costs **9.7x** shared setup for this 10-test class, because it builds the fixture 10 times instead
of once. The multiplier is not fixed, it is *the number of tests*: a 100-test class would show ~100x, a 1000-test
suite ~1000x. So for a fixture whose build dominates a test's runtime, per-test scope makes the *whole suite's*
time scale with `tests x setup_cost`, which is how a suite that "was fast" becomes a ten-minute CI step as tests
accumulate.

The rule: **share expensive, read-only fixtures; keep cheap or mutated fixtures per-test.** The §81.3 multiplier
is the argument for sharing when a fixture is genuinely expensive and the suite is large, a 9.7x (or 100x)
speedup on the dominant cost is real. But it is *conditional* on safe sharing (§81.2): the moment a shared
fixture is mutated, you have traded minutes of CI time for a flaky test that fails when the order changes, a far
worse cost. So the decision is two-dimensional: share only where it is *both* worth it (expensive, large suite)
*and* safe (read-only or reset). As with the rest of the book, measure before optimizing, most fixtures are cheap
enough that per-test isolation is free, and only the measured-expensive ones are worth the sharing risk.

---

## 81.4 Edges and failure modes

**Mutating a shared fixture.** §81.1. Leaks state to later tests, an order-dependent flake. Keep shared fixtures
read-only, or reset them per-test, or use per-test scope.

**Order-dependent tests.** A test that passes only when another runs first (or fails when the order changes) is
relying on leaked state. Run tests in random order (pytest `-p randomly`, or shuffle) to surface these; a
well-isolated suite passes in any order.

**Expensive per-test setup in a large suite.** §81.3. Multiplies by the test count and dominates CI time. Share
the fixture if it is read-only, or make the fixture cheaper (in-memory DB, smaller data, connection reuse with
per-test transactions).

**Missing teardown.** A fixture that acquires a resource (file, connection, temp dir) must release it in
`tearDown`/`tearDownClass` (or a fixture `yield`), or the suite leaks resources across tests. Pair every setup
with a teardown.

**Shared module/global state, not just fixtures.** Tests can leak through *any* shared mutable state, a module
global, a class attribute, a singleton, a monkeypatch not undone, not only the declared fixture. Reset or
patch-and-restore all shared state, not just `setUp` fixtures.

**`setUpClass` and instance state confusion.** `setUpClass` sets *class* attributes (`cls.data`); assigning
`self.x` in a test does not persist to the next test (a new instance), but mutating a shared *object* on the
class does. Know which you are touching.

---

## 81.5 Connections

**Backward.** The mutable-shared-state hazard is the mutable-default-argument and aliasing theme of Chapters 4
and 14, applied to test fixtures. The expensive fixture's cost is measured with the book's benchmark discipline.
The `setUp`/`tearDown` lifecycle is a context-manager-like protocol (Chapter 5, and pytest fixtures use `yield`
like Chapter 74).

**Forward.** Mocking and patching (and undoing patches to avoid leaks) are Deep O testing topics. Property-based
and randomized testing (which surface order dependence) are Deep O. Parallel test execution (which *requires*
isolation) connects to Chapters 8 and 48.

**Across books.** Fast, isolated tests are how Book II keeps the code feeding **Book III** trustworthy and CI
quick. A **Book III** test suite shares genuinely expensive read-only fixtures (a loaded model, a fixed corpus)
at session scope while keeping per-test isolation for anything mutated (a fresh index, a scratch database),
getting speed without flakiness. The §81.1 leak is exactly the order-dependent flake that erodes trust in a
suite, which **Deep U** guards against in the CI pipeline. Isolation is also what makes the parallel test
execution of a large suite correct.

---

## 81.6 Exercises

**1. Count the setups.** Reproduce §81.1: show `setUp` runs per test and `setUpClass` runs once, and demonstrate
the shared-fixture leak between two tests. Explain why the leak is order-dependent.

**2. Measure the multiplier.** Run §81.3's benchmark, then change the test count and show the ratio tracks it.
Explain why per-test setup makes suite time scale with `tests x setup_cost`.

**3. Share safely.** Take a suite with an expensive fixture that tests mutate, and make it shareable by resetting
the fixture per-test (or using a transaction rolled back in teardown). Show it is both fast and isolated. Explain
the pattern.

**4. Surface a flake.** Write two tests that pass in definition order but where one leaks state to the other, and
show randomizing the order can fail. Explain why random ordering is a good CI practice.

**5. The design question.** Test frameworks offer both per-test and shared fixture scopes. Argue how to choose.
Your answer must use the §81.3 measurement and the §81.1 leak, state the two conditions for sharing (expensive
*and* safely shareable), and explain why isolation is the correct default.

---

## 81.7 Summary and cross-references

- **`setUp` (per-test scope)** builds the fixture before *every* test, giving **isolation** (each test fresh) at
  the cost of building it N times. **`setUpClass` (shared scope)** builds it **once**, giving **speed** but making
  it **shared mutable state** that leaks between tests if mutated (order-dependent flakiness).
- **Measured:** per-test setup is **9.7x** shared setup for 10 tests, and the multiplier is the **test count**, so
  an expensive per-test fixture makes suite time scale with `tests x setup_cost`.
- **Default to per-test isolation;** share a fixture only when it is **both expensive and safely shareable**
  (read-only or reset). Pair every setup with a teardown; reset *all* shared state, not just fixtures.
- **Run tests in random order** to surface order-dependent leaks; a well-isolated suite passes in any order.

**Cross-references.** Mutable shared state and aliasing → Chapters 4, 14. Benchmark discipline → the book's
method. `setUp`/`tearDown` and `yield` fixtures → Chapters 5, 74. Mocking, randomized testing → Deep O. Parallel
execution → Chapters 8, 48. The CI seam → Deep U.
