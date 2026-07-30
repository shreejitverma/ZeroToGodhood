"""Listing 194.1 - a virtual environment is three files and a prefix rule.

Every mystery about venvs dissolves into one mechanism: at startup, the
interpreter looks for pyvenv.cfg next to its executable; finding one, it sets
sys.prefix to that directory (the venv) while sys.base_prefix keeps pointing
at the real installation - and site-packages under sys.prefix is what goes on
sys.path. That is the whole trick. No copies of the stdlib, no magic in
`activate` (which only edits PATH for your shell's convenience), and nothing
an installer needs to know beyond "extract under THIS prefix instead."

This listing creates a real venv offline (with_pip=False), proves the prefix
split from inside it, installs Chapter 109's hand-built wheel into it by
extraction, and shows the isolation working both ways - printing only
booleans and relative names, so the output is deterministic across the matrix.
"""

import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ch190.l01_anatomy_of_an_installed_package import build_wheel  # noqa: E402


def run_python(executable, code):
    return subprocess.run([str(executable), "-c", code],
                          capture_output=True, text=True).stdout.strip()


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp) / "env"

        print("--- creation: what venv.create actually writes ---")
        venv.create(env_dir, with_pip=False)
        cfg = (env_dir / "pyvenv.cfg").read_text()
        keys = sorted(line.split("=")[0].strip()
                      for line in cfg.splitlines() if "=" in line)
        print(f"  pyvenv.cfg keys : {keys}")
        vpython = env_dir / "bin" / "python"
        print(f"  bin/python exists (symlink on most platforms, a small COPY")
        print(f"  on macOS framework builds - never a second stdlib) : "
              f"{vpython.exists()}")
        site_dirs = list((env_dir / "lib").glob("python*/site-packages"))
        print(f"  site-packages exists and is empty : "
              f"{bool(site_dirs) and not any(site_dirs[0].iterdir())}")
        print("  a config file, a launcher, an empty directory: the environment")
        print("  is METADATA, and the interpreter does the rest at startup")

        print("--- the prefix split, proven from inside ---")
        code = ("import sys; "
                "print(sys.prefix != sys.base_prefix, "
                "any(p.endswith('site-packages') and 'env' in p "
                "for p in sys.path))")
        split, on_path = run_python(vpython, code).split()
        print(f"  sys.prefix != sys.base_prefix : {split}")
        print(f"  venv site-packages on sys.path: {on_path}")
        print("  the stdlib still comes from base_prefix (never copied);")
        print("  site-packages comes from the venv; two prefixes, one rule")

        print("--- isolation, both ways ---")
        wheel = build_wheel(Path(tmp))
        with zipfile.ZipFile(wheel) as zf:
            zf.extractall(site_dirs[0])
        probe = ("try:\n import tinypkg; print(tinypkg.answer())\n"
                 "except ImportError:\n print('ImportError')")
        print(f"  import tinypkg in the venv : {run_python(vpython, probe)}")
        print(f"  import tinypkg in base     : "
              f"{run_python(sys.executable, probe)}")
        print("  installing was extraction under the venv's prefix (Chapter")
        print("  109), and the base interpreter cannot see it - isolation is")
        print("  nothing but sys.path arithmetic")

        print("--- .pth files: site's extension point ---")
        extra = Path(tmp) / "extra_libs"
        extra.mkdir()
        (extra / "extramod.py").write_text("MARK = 'via-pth'\n")
        (site_dirs[0] / "add_extra.pth").write_text(f"{extra}\n")
        code = "import extramod; print(extramod.MARK)"
        print(f"  module reachable only via .pth : {run_python(vpython, code)}")
        print("  each line of a .pth in site-packages is appended to sys.path")
        print("  by the site module at startup - the mechanism under editable")
        print("  installs (Chapter 109's shims) and path-manipulating tools")

        print("--- what activation is ---")
        print("  activate edits PATH so 'python' finds bin/python first, and")
        print("  sets VIRTUAL_ENV for prompts; the ISOLATION never needed it -")
        print("  running the venv's python by path, as this listing just did")
        print("  four times, is the entire mechanism with no shell involved")


if __name__ == "__main__":
    main()
