"""Benchmark 45.1 - shell=True spawns an extra process.

Running the trivial command `true` two ways. With a list of args, subprocess
execs the program directly: one child process. With shell=True, subprocess first
starts a shell (/bin/sh) and the shell then runs the command: two child
processes, one of them a whole shell startup. So shell=True is both a security
hole (Chapter listing) AND slower. This measures the process-spawn overhead of
the extra shell.

Process spawning is OS-bound and noisy; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import subprocess
DN = subprocess.DEVNULL
"""


def main() -> None:
    results = [
        measure("list args (exec direct)", "subprocess.run(['true'], stdout=DN, stderr=DN)", SETUP, number=1),
        measure("shell=True (via /bin/sh)", "subprocess.run('true', shell=True, stdout=DN, stderr=DN)", SETUP, number=1),
    ]
    report("45.1  running 'true': direct exec vs via a shell",
           results, baseline="list args (exec direct)")

    print()
    print("Reading this. The list form execs the program directly: one child")
    print("process. shell=True starts /bin/sh first and has IT run the command:")
    print("two processes, including a full shell startup, so it is slower. The")
    print("security case against shell=True (command injection) is decisive on its")
    print("own; the extra process is a second, smaller reason. Use a list of args")
    print("by default; reach for shell=True only for trusted, fixed commands that")
    print("genuinely need shell features (pipes, globs, redirection), and never")
    print("with interpolated untrusted input.")


if __name__ == "__main__":
    main()
