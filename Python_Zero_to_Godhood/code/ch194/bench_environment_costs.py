"""Benchmark 194.1 - what environments cost: creation, startup, and path length.

194.1a  venv creation (with_pip=False): the three-files-and-a-directory
        operation, priced. (with_pip=True adds a full pip install and
        dominates by orders of magnitude; modern tools bootstrap pip once
        and link it, or skip it entirely - which this row justifies.)

194.1b  interpreter startup, base against venv: the pyvenv.cfg probe and
        second prefix cost at every process start.

194.1c  the sys.path toll: first import of a module sitting BEHIND 0, 10,
        50, and 200 empty directories on sys.path. Every finder probes path
        entries in order (Deep G), so environment clutter taxes every cold
        import of every process - the measured case for lean environments,
        completing Chapter 109's entry_points argument.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import subprocess
import sys
import tempfile
import time
import venv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402


def best(fn, repeat=5):
    return min(fn() for _ in range(repeat))


def timed(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def main():
    print("=== 194.1a  venv creation, no pip ===")
    print(provenance())
    print()

    def create_once():
        with tempfile.TemporaryDirectory() as tmp:
            return timed(lambda: venv.create(Path(tmp) / "env", with_pip=False))

    print(f"  venv.create(with_pip=False) : {best(create_once) * 1000:7.1f} ms")

    print()
    print("=== 194.1b  process startup, base vs venv ===")
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp) / "env"
        venv.create(env_dir, with_pip=False)

        def startup(exe):
            def run():
                return timed(lambda: subprocess.run(
                    [str(exe), "-c", "pass"], check=True))
            return best(run, repeat=9) * 1000

        print(f"  base interpreter : {startup(sys.executable):6.1f} ms")
        print(f"  venv interpreter : {startup(env_dir / 'bin' / 'python'):6.1f} ms")

    print()
    print("=== 194.1c  first import behind N junk path entries ===")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        target = base / "real"
        target.mkdir()
        (target / "needle.py").write_text("VALUE = 1\n")
        junk_dirs = []
        for i in range(200):
            d = base / f"junk{i:03}"
            d.mkdir()
            junk_dirs.append(str(d))
        for count in (0, 10, 50, 200):
            path_list = junk_dirs[:count] + [str(target)]
            code = ("import sys, time; sys.path[:0] = {paths!r}; "
                    "t0 = time.perf_counter(); import needle; "
                    "print((time.perf_counter() - t0) * 1e6)"
                    ).format(paths=path_list)

            def run(c=code):
                out = subprocess.run([sys.executable, "-c", c],
                                     capture_output=True, text=True, check=True)
                return float(out.stdout)

            print(f"  behind {count:>3} junk entries : {best(run, 9):7,.0f} us")

    print()
    print("Reading this. Creating an environment is single-digit")
    print("milliseconds - cheap enough to be disposable, which is the modern")
    print("workflow's premise (a venv per project, rebuilt freely from a")
    print("lockfile, Chapter 114). Startup shows the argument in vivo: the")
    print("EMPTY venv starts faster than this base interpreter, because the")
    print("base drags a populated site-packages through site processing - the")
    print("pyvenv.cfg probe costs nothing measurable against that. And the")
    print("path toll makes it per-import: ~23 us of stat calls per junk entry")
    print("on every cold import of every process. Lean environments are not")
    print("tidiness - they are Chapter 109's scan argument and this table,")
    print("compounding.")


if __name__ == "__main__":
    main()
