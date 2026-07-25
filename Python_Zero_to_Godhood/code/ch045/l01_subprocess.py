"""Listing 45.1 - subprocess: list args are safe; shell=True is an injection hole.

subprocess.run launches an external program. Pass the command as a LIST of
arguments and the OS executes that program directly, with each list element a
single literal argument, shell metacharacters (; | > $ ...) have no special
meaning. Pass a STRING with shell=True and a shell interprets it, so any
metacharacter in interpolated input is executed: that is command injection, the
shell-level twin of the SQL injection of Chapter 41. This listing demonstrates
the difference with a benign injected command (echo), so the output is safe and
deterministic.
"""

import subprocess


def main() -> None:
    # A benign stand-in for hostile input: it contains a shell command separator.
    user_input = "report.txt; echo INJECTED-COMMAND-RAN"

    print("--- UNSAFE: shell=True interprets the whole string ---")
    unsafe = subprocess.run(
        f"echo Processing {user_input}",
        shell=True, capture_output=True, text=True,
    )
    for line in unsafe.stdout.splitlines():
        print(f"    {line}")               # the injected echo RAN: two lines

    print("--- SAFE: a list of args; metacharacters are literal ---")
    safe = subprocess.run(
        ["echo", "Processing", user_input],
        capture_output=True, text=True,
    )
    for line in safe.stdout.splitlines():
        print(f"    {line}")               # one line: the ; is just text

    print("--- capturing output and checking the exit status ---")
    r = subprocess.run(["echo", "done"], capture_output=True, text=True)
    print(f"    stdout     : {r.stdout.strip()!r}")
    print(f"    returncode : {r.returncode}")
    # check=True raises CalledProcessError on a non-zero exit
    try:
        subprocess.run(["false"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"    check=True raised on exit {e.returncode}")


if __name__ == "__main__":
    main()
