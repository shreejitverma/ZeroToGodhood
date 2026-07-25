"""Benchmark 81.1 - per-test setup cost scales with the number of tests.

An expensive fixture built in setUp runs once per test, so a class of N tests pays
N times the setup. The same fixture built in setUpClass runs once and is shared, so
the class pays it once. This runs a class of tests with an expensive fixture both
ways and times them, so the multiplier is visible: per-test cost grows with the
test count, shared cost stays roughly flat.

Does its own timing (it runs test suites), guarded by __main__. See
_harness/bench.py.
"""

import io
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N_TESTS = 10


def expensive():
    total = 0
    for i in range(200_000):
        total += i * i
    return total


def _per_test_setup(self):
    self.data = expensive()


def _shared_setup(cls):
    cls.data = expensive()


def _test_method(self):
    self.assertTrue(self.data)


def make_per_test():
    body = {"setUp": _per_test_setup}
    for i in range(N_TESTS):
        body[f"test_{i:02}"] = _test_method
    return type("PerTest", (unittest.TestCase,), body)


def make_shared():
    body = {"setUpClass": classmethod(_shared_setup)}
    for i in range(N_TESTS):
        body[f"test_{i:02}"] = _test_method
    return type("Shared", (unittest.TestCase,), body)


def run_case(case):
    times = []
    for _ in range(5):
        # rebuild the suite each run: a TestSuite drops its tests (sets them to
        # None) after running to free memory, so it cannot be re-run.
        suite = unittest.TestLoader().loadTestsFromTestCase(case)
        t0 = time.perf_counter()
        unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(suite)
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    print(f"=== 81.1  {N_TESTS} tests: per-test setUp vs shared setUpClass ===")
    print(provenance())
    print()

    per_test = run_case(make_per_test())
    shared = run_case(make_shared())

    print(f"  tests in class            : {N_TESTS}")
    print(f"  per-test setUp   (N setups): {per_test * 1000:7.1f} ms")
    print(f"  shared setUpClass (1 setup): {shared * 1000:7.1f} ms")
    print(f"  ratio                      : {per_test / shared:7.1f}x")

    print()
    print("Reading this. The per-test fixture is built once per test, so a class of")
    print(f"{N_TESTS} tests pays {N_TESTS}x the setup; the shared fixture is built once. For a slow")
    print("fixture (a database, loaded data, a compiled resource) shared across many")
    print("tests, per-test setup can dominate the suite's runtime, and the gap grows")
    print("with the test count. But shared fixtures require the tests NOT to mutate")
    print("the shared state, or they leak between tests (order-dependent flakiness).")
    print("Prefer per-test isolation by default; move a fixture to shared scope only")
    print("when it is expensive AND read-only (or reset between tests).")


if __name__ == "__main__":
    main()
