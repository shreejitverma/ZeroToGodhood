"""Listing 81.1 - fixture scope: per-test isolation vs shared-setup speed.

setUp runs before EVERY test (per-test scope): each test gets a fresh fixture, so
tests are ISOLATED, but an expensive setUp is paid N times for N tests.
setUpClass runs ONCE for the whole class (shared scope): the fixture is built once
and reused, far cheaper for a slow fixture, but tests SHARE it, so if one test
mutates it, later tests see the change, an order-dependent leak. This listing shows
the call counts and the isolation difference, using counters (deterministic).
"""

import unittest

CALLS = {"setUp": 0, "setUpClass": 0}


class PerTestScope(unittest.TestCase):
    def setUp(self):
        CALLS["setUp"] += 1
        self.items = [1, 2, 3]        # a FRESH list per test

    def test_1_mutates(self):
        self.items.append(99)          # mutation is local to this test's fixture
        self.assertEqual(len(self.items), 4)

    def test_2_sees_fresh(self):
        self.assertEqual(self.items, [1, 2, 3])   # unaffected: isolated


class SharedScope(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CALLS["setUpClass"] += 1
        cls.items = [1, 2, 3]          # ONE list shared by all tests

    def test_1_mutates(self):
        self.items.append(99)          # mutates the SHARED list
        self.assertEqual(len(self.items), 4)

    def test_2_sees_leak(self):
        # runs after test_1 (alphabetical order): sees test_1's mutation
        self.assertEqual(self.items, [1, 2, 3, 99])   # LEAKED state


def run(case):
    suite = unittest.TestLoader().loadTestsFromTestCase(case)
    import io
    unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(suite)


def main() -> None:
    run(PerTestScope)
    run(SharedScope)
    print("--- how often the fixture is built ---")
    print(f"  setUp (per-test)   called : {CALLS['setUp']} times (once per test)")
    print(f"  setUpClass (shared) called: {CALLS['setUpClass']} time (once total)")

    print("--- isolation ---")
    print(f"  per-test scope  : each test gets a fresh fixture (no leak)")
    print(f"  shared scope    : test_2 saw test_1's mutation [1, 2, 3, 99] (a leak)")

    print("--- the trade ---")
    print(f"  per-test setUp   : isolated, but pays the setup cost N times")
    print(f"  shared setUpClass: pays it once, but tests must NOT mutate shared state")


if __name__ == "__main__":
    main()
