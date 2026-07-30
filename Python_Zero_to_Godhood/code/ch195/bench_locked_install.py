"""Benchmark 195.1 - what the lock buys, and what verification costs.

195.1a  install a 100-package environment twice: resolving first (Chapter
        112's happy-path search over a synthetic universe), and from a lock
        (hash-check plus extraction only). The delta is the search, memoised
        - and this is the HAPPY path; against Chapter 112's adversarial
        table the lock's advantage is unbounded.

195.1b  verification throughput: sha256 over wheel-sized artifacts, the
        per-byte price of the trust anchor. It runs at memory-bandwidth
        scale, which is why hash-checking everything is affordable policy.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import hashlib
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402
from ch193.l01_a_resolver_from_scratch import resolve  # noqa: E402

PACKAGES = 100


def make_universe_and_wheels(directory: Path):
    universe = {}
    wheels = {}
    for i in range(PACKAGES):
        name = f"pkg{i:03}"
        deps = [(f"pkg{i+1:03}", ">=1.0", "")] if i + 1 < PACKAGES else []
        universe[name] = {"2.0.0": deps, "1.0.0": deps}
        wheel = directory / f"{name}-2.0.0-py3-none-any.whl"
        with zipfile.ZipFile(wheel, "w") as zf:
            zf.writestr(f"{name}.py", f"NAME = {name!r}\n")
            zf.writestr(f"{name}-2.0.0.dist-info/METADATA",
                        f"Metadata-Version: 2.4\nName: {name}\nVersion: 2.0.0\n")
        wheels[name] = wheel
    return universe, wheels


def main():
    print("=== 195.1a  100-package environment: resolve+install vs locked ===")
    print(provenance())
    print("method      : min of 5 runs per row")
    print()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        universe, wheels = make_universe_and_wheels(work)
        hashes = {n: hashlib.sha256(w.read_bytes()).hexdigest()
                  for n, w in wheels.items()}

        def resolving_install():
            site = Path(tempfile.mkdtemp(dir=work))
            pins = resolve(universe, [("pkg000", ">=1.0")], [])
            for name in pins:
                with zipfile.ZipFile(wheels[name]) as zf:
                    zf.extractall(site)

        def locked_install():
            site = Path(tempfile.mkdtemp(dir=work))
            for name, wheel in wheels.items():
                assert hashlib.sha256(
                    wheel.read_bytes()).hexdigest() == hashes[name]
                with zipfile.ZipFile(wheel) as zf:
                    zf.extractall(site)

        for label, fn in (("resolve, then install", resolving_install),
                          ("from the lock (verify+extract)", locked_install)):
            runs = []
            for _ in range(5):
                t0 = time.perf_counter()
                fn()
                runs.append(time.perf_counter() - t0)
            print(f"  {label:<30} : {min(runs) * 1000:7.1f} ms")

    print()
    print("=== 195.1b  sha256 throughput (the price of trust) ===")
    payload = bytes(range(256)) * (4 * 1024 * 16)   # 16 MB
    runs = []
    for _ in range(5):
        t0 = time.perf_counter()
        hashlib.sha256(payload).hexdigest()
        runs.append(time.perf_counter() - t0)
    best = min(runs)
    print(f"  16 MB artifact : {best * 1000:6.1f} ms "
          f"({len(payload) / best / 1e9:4.1f} GB/s)")

    print()
    print("Reading this. On a HAPPY graph the lock saves the resolver's")
    print("linear walk - real but modest; the lock's true value is Chapter")
    print("112's other table, where the search is exponential and the lock's")
    print("saving is unbounded, plus the network round-trips per candidate")
    print("that this offline benchmark cannot show. Verification, meanwhile,")
    print("runs at gigabytes per second: hashing every artifact on every")
    print("install is effectively free, which is why 'verify always' is the")
    print("correct default and not a paranoid luxury.")


if __name__ == "__main__":
    main()
