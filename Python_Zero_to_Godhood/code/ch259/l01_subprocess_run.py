"""Listing 259.1 - Python 3.5 (2015): subprocess.run, one call to run a command.

Running an external command from Python used to mean choosing among a confusing
family: os.system (no output capture, shell-injection risk), os.popen
(deprecated), or subprocess.Popen (powerful but low-level - you wire up pipes,
call communicate(), check returncode by hand). Simple needs demanded ceremony.
Python 3.5's PEP 324 follow-up added subprocess.run: one function that runs a
command to completion and returns a CompletedProcess with the return code and
(optionally) captured stdout/stderr, with check=True to raise on failure and
timeout= to bound it. Deep volumes own no process mechanism; this is the release
that made 'run this command and get the result' a single call. This listing runs
the current Python interpreter on fixed one-liners, so its output is
deterministic. Verified on current interpreters.
"""

import subprocess
import sys


def main() -> None:
    print("--- run() executes a command and returns a CompletedProcess ---")
    result = subprocess.run(
        [sys.executable, "-c", "print('hello from a subprocess')"],
        capture_output=True, text=True,
    )
    print(f"  type(result)      : {type(result).__name__}")
    print(f"  result.returncode : {result.returncode}   (0 = success)")
    print(f"  result.stdout     : {result.stdout!r}")
    print("  one call runs the command to completion and hands back an object")
    print("  with the exit code and captured output. no Popen, no manual pipe")
    print("  wiring, no communicate() - the common case is one line")

    print("--- capture_output + text: get stdout/stderr as strings ---")
    r2 = subprocess.run(
        [sys.executable, "-c",
         "import sys; print('out'); print('err', file=sys.stderr)"],
        capture_output=True, text=True,
    )
    print(f"  stdout : {r2.stdout!r}")
    print(f"  stderr : {r2.stderr!r}")
    print("  capture_output collects both streams; text=True decodes them from")
    print("  bytes to str. you get the child's output as ordinary strings to")
    print("  parse, log, or assert on")

    print("--- returncode reports success or failure without raising ---")
    r3 = subprocess.run(
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        capture_output=True, text=True,
    )
    print(f"  a command exiting 3 -> returncode : {r3.returncode}")
    print("  by default run() does NOT raise on a nonzero exit; you inspect")
    print("  returncode. this suits commands whose failure is an expected")
    print("  outcome you want to branch on, not an exception")

    print("--- check=True: turn a nonzero exit into an exception ---")
    try:
        subprocess.run(
            [sys.executable, "-c", "import sys; sys.exit(1)"],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"  check=True raised CalledProcessError, returncode="
              f"{exc.returncode}")
    print("  with check=True a failing command raises CalledProcessError - the")
    print("  right choice when the command MUST succeed and failure should stop")
    print("  the flow, like an error in your own code")

    print("--- passing input, and why a list (not a shell string) is safer ---")
    r5 = subprocess.run(
        [sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"],
        input="quiet text\n", capture_output=True, text=True,
    )
    print(f"  fed stdin 'quiet text', got : {r5.stdout!r}")
    print("  input= sends data to the child's stdin. passing the command as a")
    print("  LIST of arguments (not one shell string) avoids the shell entirely,")
    print("  so untrusted values cannot inject extra commands - the safe default")

    print("--- the constraint answered ---")
    print("  running a command meant picking from os.system/popen/Popen -")
    print("  unsafe, deprecated, or low-level. subprocess.run (3.5) is one call")
    print("  that returns a CompletedProcess with return code and captured")
    print("  output, check=True to raise on failure, timeout= to bound it, and")
    print("  list-args to stay shell-injection-safe. the common case became one line")


if __name__ == "__main__":
    main()
