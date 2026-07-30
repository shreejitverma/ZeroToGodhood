"""Benchmark 193.1 - resolution's two shapes: linear when lucky, exponential when not.

The listing's resolver, run over two synthetic universes:

  the HAPPY universe: a chain of N packages, newest of everything is
  mutually compatible - resolution visits each once, linear;

  the ADVERSARIAL universe: N packages each with K versions, and a bottom
  package whose constraint is only satisfied by the OLDEST version of
  everything - newest-first must explore and reject the K^N-shaped frontier.

This is Chapter 87's lesson (the exponent decides) applied to installers:
resolver runtime is a property of the CONSTRAINT GRAPH, not the tool, which
is why the same pip can be instant on one project and hang on another, why
resolvers invest in conflict-driven learning, and why the real fix is on the
user's side: tighter floors, fewer wildcards, and lockfiles (Chapter 114)
that skip the search entirely.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402
from ch193.l01_a_resolver_from_scratch import resolve  # noqa: E402


def happy_universe(n):
    universe = {}
    for i in range(n):
        deps = [(f"pkg{i+1}", ">=1.0", "")] if i + 1 < n else []
        universe[f"pkg{i}"] = {"2.0.0": deps, "1.0.0": deps}
    return universe


def adversarial_universe(n, k):
    universe = {}
    for i in range(n):
        versions = {}
        for v in range(k):
            deps = [(f"pkg{i+1}", ">=1.0", "")] if i + 1 < n else \
                   [("anchor", ">=1.0", "")]
            versions[f"1.{v}.0"] = deps
        universe[f"pkg{i}"] = versions
    # anchor only tolerates the OLDEST of pkg0..pkg{n-1}? It can't see them;
    # instead: every package's NON-oldest versions depend on a phantom that
    # conflicts with anchor, discovered only at the bottom.
    for i in range(n):
        for v in range(1, k):
            universe[f"pkg{i}"][f"1.{v}.0"].append(("phantom", ">=2.0", ""))
    universe["anchor"] = {"1.0.0": [("phantom", "<2.0", "")]}
    universe["phantom"] = {"2.5.0": [], "1.5.0": []}
    return universe


def timed_solve(universe, root):
    trace = []
    t0 = time.perf_counter()
    pins = resolve(universe, [(root, ">=1.0")], trace)
    return (time.perf_counter() - t0) * 1000, len(trace), pins


def main():
    sys.setrecursionlimit(100_000)
    print("=== 193.1  resolver runtime vs constraint-graph shape ===")
    print(provenance())
    print("method      : single solve per cell (deterministic algorithm)")
    print()
    print("  happy chain (all newest compatible):")
    for n in (10, 100, 1_000):
        ms, steps, pins = timed_solve(happy_universe(n), "pkg0")
        print(f"    {n:>5} packages : {ms:8.2f} ms   {steps:>7,} steps")

    print("  adversarial (only the oldest of everything survives):")
    for n, k in ((6, 4), (8, 4), (10, 4)):
        ms, steps, pins = timed_solve(adversarial_universe(n, k), "pkg0")
        ok = pins is not None
        print(f"    {n:>2} pkgs x {k} versions : {ms:10.2f} ms   "
              f"{steps:>9,} steps   solved={ok}")

    print()
    print("Reading this. The happy column is linear: visit, pin, descend.")
    print("The adversarial column multiplies by ~K per package added - the")
    print("K^N frontier - because every newest-first path ends at the same")
    print("contradiction and must be disproved branch by branch. Real")
    print("resolvers prune smarter (remembering WHY a branch failed), but no")
    print("cleverness changes the worst case's exponent, only its base. The")
    print("engineering answers live outside the resolver: constrain honestly")
    print("(every wildcard is frontier), keep dependency trees shallow, and")
    print("lock (Chapter 114) so the search runs once, not per install.")


if __name__ == "__main__":
    main()
