"""Listing 192.1 - pyproject.toml and the build contract, implemented.

Three PEPs turned "run setup.py and hope" into a contract. PEP 518: a project
DECLARES its build tool in [build-system], so the installer can set it up
first. PEP 517: the tool is a module exposing two hooks - build_wheel and
build_sdist - so any frontend can drive any backend. PEP 621: the metadata
lives in [project], statically, so tools can read it without running anything.

This listing does not describe the contract; it IMPLEMENTS it. A complete
PEP 517 backend in ~30 lines builds a spec-valid wheel from a source tree
whose pyproject.toml names it, the [project] table translates mechanically
into Chapter 109's METADATA, and the result imports. Offline, deterministic,
and small enough to prove the point: the contract is an interface, and
setuptools, hatchling, and flit are implementations of it.
"""

import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ch190.l01_anatomy_of_an_installed_package import record_line  # noqa: E402

PYPROJECT = """\
[build-system]
requires = ["deepn_backend"]
build-backend = "deepn_backend"

[project]
name = "contractpkg"
version = "2.0.0"
description = "Built by the chapter's own backend"
requires-python = ">=3.11"
dependencies = ["tinypkg>=1.0"]

[project.scripts]
contract-tool = "contractpkg:main"
"""

MODULE = '''\
def main():
    return "built-by-contract"
'''


# ----- a complete PEP 517 build backend (the two mandatory hooks) -----

def project_table(source_dir: Path) -> dict:
    with open(source_dir / "pyproject.toml", "rb") as fh:
        return tomllib.load(fh)["project"]


def metadata_from_project(project: dict) -> str:
    lines = ["Metadata-Version: 2.4",
             f"Name: {project['name']}",
             f"Version: {project['version']}",
             f"Summary: {project['description']}",
             f"Requires-Python: {project['requires-python']}"]
    for dep in project.get("dependencies", []):
        lines.append(f"Requires-Dist: {dep}")
    return "\n".join(lines) + "\n"


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None,
                *, _source=None):
    source = Path(_source or ".")
    project = project_table(source)
    name, version = project["name"], project["version"]
    dist_info = f"{name}-{version}.dist-info"
    files = {
        f"{name}.py": (source / f"{name}.py").read_bytes(),
        f"{dist_info}/METADATA": metadata_from_project(project).encode(),
        f"{dist_info}/WHEEL": (b"Wheel-Version: 1.0\nGenerator: deepn_backend"
                               b"\nRoot-Is-Purelib: true\nTag: py3-none-any\n"),
        f"{dist_info}/entry_points.txt":
            ("[console_scripts]\n" + "\n".join(
                f"{k} = {v}" for k, v in
                project.get("scripts", {}).items()) + "\n").encode(),
    }
    record = "\n".join(record_line(n, d) for n, d in files.items())
    record += f"\n{dist_info}/RECORD,,\n"
    wheel_name = f"{name}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(Path(wheel_directory) / wheel_name, "w") as zf:
        for archive_name, data in files.items():
            # fixed 1980 date: reproducible bytes (Chapters 109, 114)
            zf.writestr(zipfile.ZipInfo(archive_name), data)
        zf.writestr(zipfile.ZipInfo(f"{dist_info}/RECORD"), record)
    return wheel_name


def build_sdist(sdist_directory, config_settings=None):
    raise NotImplementedError("left as the chapter's exercise 3")


# ----- a frontend driving it -----

def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "src"
        source.mkdir()
        (source / "pyproject.toml").write_text(PYPROJECT)
        (source / "contractpkg.py").write_text(MODULE)

        print("--- PEP 518: the project declares its builder ---")
        with open(source / "pyproject.toml", "rb") as fh:
            build_system = tomllib.load(fh)["build-system"]
        print(f"  requires      : {build_system['requires']}")
        print(f"  build-backend : {build_system['build-backend']}")
        print("  the frontend reads THIS before anything else, installs the")
        print("  requirements into an isolated environment (Chapter 113), and")
        print("  only then imports the named backend - so building never")
        print("  depends on what happens to be installed on the machine")

        print("--- PEP 517: the frontend calls the hook ---")
        dist = Path(tmp) / "dist"
        dist.mkdir()
        wheel_name = build_wheel(dist, _source=source)
        print(f"  build_wheel() returned : {wheel_name}")
        with zipfile.ZipFile(dist / wheel_name) as zf:
            for entry in sorted(zf.namelist()):
                print(f"    {entry}")

        print("--- PEP 621: [project] became METADATA, mechanically ---")
        with zipfile.ZipFile(dist / wheel_name) as zf:
            metadata = zf.read(
                "contractpkg-2.0.0.dist-info/METADATA").decode()
        for line in metadata.splitlines():
            print(f"  {line}")
        print("  static table in, static file out: resolvers (Chapter 112) can")
        print("  read dependencies WITHOUT running the build, which the old")
        print("  executable setup.py made impossible by construction")

        print("--- and the artifact is real: install and run it ---")
        site = Path(tmp) / "site"
        site.mkdir()
        with zipfile.ZipFile(dist / wheel_name) as zf:
            zf.extractall(site)
        sys.path.insert(0, str(site))
        try:
            import contractpkg
            print(f"  contractpkg.main() : {contractpkg.main()!r}")
        finally:
            sys.path.remove(str(site))
            sys.modules.pop("contractpkg", None)
    print("  thirty lines of backend, because the CONTRACT carries the")
    print("  complexity: real backends add source discovery, sdists, C")
    print("  compilation (Chapter 115), and editable hooks - same interface")


if __name__ == "__main__":
    main()
