"""Listing 195.1 - the lockfile: resolution memoised, trust made checkable.

Chapter 112 ended with the advice to run the search once; this is the file
that holds the answer. A lockfile records the SURVIVORS - exact versions,
exact artifacts, exact hashes - so installation becomes verification plus
extraction, no resolver in the loop. PEP 751 (pylock.toml) standardised the
format in 2025 so the answer is portable between tools.

This listing generates a pylock.toml from real artifacts (the wheels built in
Chapters 109 and 111), proves the generation DETERMINISTIC (same inputs, same
bytes), installs from the lock with hash verification, and then commits the
volume's most instructive crime: it flips one byte in a wheel and watches the
lock refuse it. Offline, byte-checkable, and identical across the matrix.
"""

import base64
import hashlib
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ch190.l01_anatomy_of_an_installed_package import build_wheel  # noqa: E402
from ch192.l01_the_build_contract import (build_wheel as build_contract_wheel,  # noqa: E402
                                          MODULE, PYPROJECT)


def sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_lock(pins: dict[str, tuple[str, Path]]) -> str:
    lines = ['lock-version = "1.0"',
             'created-by = "deepn (Chapter 114)"',
             'environments = ["python_version >= \\"3.11\\""]', ""]
    for name in sorted(pins):
        version, wheel = pins[name]
        lines += [f"[[packages]]",
                  f'name = "{name}"',
                  f'version = "{version}"',
                  "",
                  "[[packages.wheels]]",
                  f'name = "{wheel.name}"',
                  f'hashes = {{ sha256 = "{sha256_hex(wheel)}" }}',
                  ""]
    return "\n".join(lines)


def install_from_lock(lock_text: str, wheel_dir: Path, site: Path) -> list[str]:
    lock = tomllib.loads(lock_text)
    report = []
    for package in lock["packages"]:
        entry = package["wheels"][0]
        wheel = wheel_dir / entry["name"]
        actual = sha256_hex(wheel)
        if actual != entry["hashes"]["sha256"]:
            report.append(f"REFUSED {package['name']}: hash mismatch")
            continue
        with zipfile.ZipFile(wheel) as zf:
            zf.extractall(site)
        report.append(f"installed {package['name']}=={package['version']}"
                      f" (hash verified)")
    return report


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        source = work / "src"
        source.mkdir()
        (source / "pyproject.toml").write_text(PYPROJECT)
        (source / "contractpkg.py").write_text(MODULE)

        tiny = build_wheel(work)
        contract = work / build_contract_wheel(work, _source=source)
        pins = {"tinypkg": ("1.0.0", tiny),
                "contractpkg": ("2.0.0", contract)}

        print("--- the lock: survivors, artifacts, hashes ---")
        lock_text = generate_lock(pins)
        for line in lock_text.splitlines():
            print(f"  {line}")

        print("--- generation is deterministic ---")
        again = generate_lock(pins)
        digest = hashlib.sha256(lock_text.encode()).hexdigest()[:16]
        print(f"  two generations byte-identical : {again == lock_text}")
        print(f"  lockfile's own sha256 (prefix) : {digest}")
        print("  sorted packages, exact pins, content hashes: nothing in the")
        print("  file depends on time, machine, or tool mood - so the lock")
        print("  itself can be reviewed, diffed, and hashed like source")

        print("--- installing FROM the lock: verify, then extract ---")
        site = work / "site"
        site.mkdir()
        for line in install_from_lock(lock_text, work, site):
            print(f"  {line}")
        sys.path.insert(0, str(site))
        try:
            import contractpkg
            import tinypkg
            print(f"  imports work : {tinypkg.answer()}, "
                  f"{contractpkg.main()!r}")
        finally:
            sys.path.remove(str(site))
            sys.modules.pop("tinypkg", None)
            sys.modules.pop("contractpkg", None)
        print("  no resolver ran: Chapter 112's search was memoised into the")
        print("  file, and installation reduced to hash-check plus Chapter")
        print("  109's extraction - which is why locked installs are fast AND")
        print("  reproducible")

        print("--- the tamper test ---")
        data = bytearray(tiny.read_bytes())
        data[-1] ^= 0xFF
        tiny.write_bytes(bytes(data))
        site2 = work / "site2"
        site2.mkdir()
        for line in install_from_lock(lock_text, work, site2):
            print(f"  {line}")
        print("  one flipped byte, anywhere in the artifact, and the lock")
        print("  refuses it: the hash pins CONTENT, not names or versions -")
        print("  a compromised mirror or a swapped upload fails identically")


if __name__ == "__main__":
    main()
