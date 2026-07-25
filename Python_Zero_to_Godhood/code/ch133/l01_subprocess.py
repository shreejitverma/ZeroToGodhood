"""Listing 133.1 - subprocess: running external programs safely.

multiprocessing (Chapter 47) runs Python functions in worker processes; subprocess
runs EXTERNAL PROGRAMS (any executable) and captures their output. The modern API is
subprocess.run(args, ...):
  - args as a LIST (["cmd", "arg1", ...]) execs the program directly, with NO shell,
    so arguments are passed literally and there is no shell-injection risk.
  - capture_output=True + text=True capture stdout/stderr as strings.
  - The result carries the RETURNCODE (0 = success); check=True raises
    CalledProcessError on a nonzero exit.
  - input= pipes data to the program's stdin.
This listing shows each with standard POSIX commands, deterministically.
"""

import subprocess


def main() -> None:
    print("--- run a command and capture its output ---")
    r = subprocess.run(["echo", "hello"], capture_output=True, text=True)
    print(f"  stdout     : {r.stdout!r}")
    print(f"  returncode : {r.returncode}   (0 = success)")

    print("--- the return code signals success or failure ---")
    r = subprocess.run(["false"], capture_output=True)   # 'false' always exits 1
    print(f"  'false' returncode : {r.returncode}")

    print("--- check=True raises on a nonzero exit (fail loudly) ---")
    try:
        subprocess.run(["false"], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"  check=True raised CalledProcessError, returncode : {e.returncode}")

    print("--- args as a LIST: no shell, so no injection (arguments are literal) ---")
    r = subprocess.run(["python3", "-c", "print(6 * 7)"], capture_output=True, text=True)
    print(f"  python3 -c 'print(6*7)' -> {r.stdout.strip()!r}")

    print("--- pipe data to the program's stdin with input= ---")
    r = subprocess.run(["wc", "-c"], input="12345", capture_output=True, text=True)
    print(f"  wc -c of '12345' (byte count) : {r.stdout.strip()}")

    print("--- the rule ---")
    print(f"  subprocess.run(list_args, capture_output=True, text=True); check the")
    print(f"  returncode (or check=True); pass args as a LIST, never shell=True on input")


if __name__ == "__main__":
    main()
