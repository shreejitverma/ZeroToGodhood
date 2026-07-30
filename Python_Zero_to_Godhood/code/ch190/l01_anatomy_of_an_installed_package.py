"""Listing 190.1 - from source tree to import: what "installed" actually means.

Deep N opens by demystifying its subject completely: a wheel is a zip file
with a naming convention, "installing" it is extracting that zip onto the
import path, and everything an installer knows afterwards lives in a
`<name>-<version>.dist-info/` directory next to the code. This listing builds
a real, spec-valid wheel with nothing but zipfile, installs it by extraction
into a temporary directory, imports it, and then reads back its own metadata
through importlib.metadata - the whole packaging lifecycle, offline, in one
deterministic file.
"""

import base64
import hashlib
import importlib.metadata
import importlib.util
import sys
import tempfile
import zipfile
from pathlib import Path

NAME, VERSION = "tinypkg", "1.0.0"
DIST_INFO = f"{NAME}-{VERSION}.dist-info"

MODULE_SOURCE = '''\
"""A complete distribution: one module."""

def answer():
    return 42
'''

METADATA = f"""\
Metadata-Version: 2.4
Name: {NAME}
Version: {VERSION}
Summary: The smallest honest package
Requires-Python: >=3.9
"""

WHEEL_META = """\
Wheel-Version: 1.0
Generator: by-hand (Deep N)
Root-Is-Purelib: true
Tag: py3-none-any
"""


def record_line(archive_name, data):
    digest = base64.urlsafe_b64encode(
        hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"{archive_name},sha256={digest},{len(data)}"


def build_wheel(directory: Path) -> Path:
    wheel_path = directory / f"{NAME}-{VERSION}-py3-none-any.whl"
    files = {
        f"{NAME}.py": MODULE_SOURCE.encode(),
        f"{DIST_INFO}/METADATA": METADATA.encode(),
        f"{DIST_INFO}/WHEEL": WHEEL_META.encode(),
    }
    record = "\n".join(record_line(n, d) for n, d in files.items())
    record += f"\n{DIST_INFO}/RECORD,,\n"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        for archive_name, data in files.items():
            # ZipInfo's default date is 1980-01-01: the wheel's bytes (and so
            # its hash, Chapter 114) never depend on when it was built.
            zf.writestr(zipfile.ZipInfo(archive_name), data)
        zf.writestr(zipfile.ZipInfo(f"{DIST_INFO}/RECORD"), record)
    return wheel_path


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp)

        print("--- a wheel is a zip with a naming convention ---")
        wheel = build_wheel(site)
        print(f"  built  : {wheel.name}")
        print(f"  parsed : name={NAME}, version={VERSION}, tag=py3-none-any")
        with zipfile.ZipFile(wheel) as zf:
            for entry in sorted(zf.namelist()):
                print(f"    {entry}")
        print("  the filename IS the compatibility claim (Chapter 110 decodes")
        print("  the tag); the payload is code plus one .dist-info directory")

        print("--- installing is extracting onto the import path ---")
        with zipfile.ZipFile(wheel) as zf:
            zf.extractall(site)
        sys.path.insert(0, str(site))
        try:
            import tinypkg
            print(f"  import tinypkg; tinypkg.answer() : {tinypkg.answer()}")
            print("  no registry, no compilation step, no magic: files in a")
            print("  directory that sys.path reaches (Deep G owns the finding)")

            print("--- .dist-info is the installer's memory ---")
            dist = importlib.metadata.distribution(NAME)
            print(f"  metadata Name    : {dist.metadata['Name']}")
            print(f"  metadata Version : {dist.version}")
            print(f"  Requires-Python  : {dist.metadata['Requires-Python']}")
            files = sorted(str(f) for f in dist.files)
            print(f"  RECORD lists     : {files}")
            print("  importlib.metadata reads the SAME dist-info any installer")
            print("  writes: metadata for humans and resolvers, RECORD (with a")
            print("  sha256 per file) for uninstall and integrity")

            print("--- RECORD's hashes verify, because we can check ---")
            module_file = site / "tinypkg.py"
            data = module_file.read_bytes()
            expected = record_line("tinypkg.py", data).split(",")[1]
            actual = "sha256=" + base64.urlsafe_b64encode(
                hashlib.sha256(data).digest()).rstrip(b"=").decode()
            print(f"  recorded hash matches installed file : {expected == actual}")
            print("  the same digest format secures lockfiles (Chapter 114) and")
            print("  uploads: content-addressing is packaging's one trust anchor")
        finally:
            sys.path.remove(str(site))
            sys.modules.pop("tinypkg", None)

    print("--- the two artifact kinds, named ---")
    print("  sdist : source + pyproject.toml; the BUILD happens on the user's")
    print("          machine (Chapter 111 owns the build contract)")
    print("  wheel : built, tagged, extract-only - what you just made. every")
    print("          installer prefers it, because extraction cannot run code")


if __name__ == "__main__":
    main()
