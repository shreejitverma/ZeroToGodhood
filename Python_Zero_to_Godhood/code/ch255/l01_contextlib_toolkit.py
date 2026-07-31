"""Listing 255.1 - Python 3.4 (2014): the contextlib toolkit - suppress, redirect_stdout, ExitStack.

The `with` statement (Chapter 5) automates cleanup, but writing context managers
and common with-block patterns still took boilerplate. Python 3.4 filled out
contextlib with ready-made tools: suppress(Exc) is a with-block that swallows a
specific exception (replacing an empty-except try), redirect_stdout captures or
silences print output cleanly, and ExitStack (3.3) manages a DYNAMIC number of
context managers - closing them all even if the count is unknown until runtime.
These turn recurring try/finally and try/except shapes into named,
self-documenting with-blocks. Deep B owns exception unwinding, Chapter 5 owns
the context-manager protocol; this is the release that stocked the toolbox built
on them. Verified on current interpreters.
"""

import contextlib
import io


def main() -> None:
    print("--- suppress(): a with-block that swallows a chosen exception ---")
    with contextlib.suppress(FileNotFoundError):
        raise FileNotFoundError("config.ini")     # swallowed by suppress
    print("  reached the line after the with-block (the error was suppressed)")
    print("  suppress(FileNotFoundError) replaces `try: ... except")
    print("  FileNotFoundError: pass` - the intent ('ignore this specific")
    print("  error') is now the NAME of the block, not a silent empty except")

    print("--- suppress only swallows the named type; others propagate ---")
    try:
        with contextlib.suppress(KeyError):
            raise ValueError("different error")   # NOT a KeyError
    except ValueError as exc:
        print(f"  a ValueError inside suppress(KeyError) propagated : {exc}")
    print("  suppress is precise: it catches only the type(s) you name. an")
    print("  unrelated exception passes through, so you do not accidentally")
    print("  hide bugs the way a bare `except:` would")

    print("--- redirect_stdout(): capture print output cleanly ---")
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        print("this goes into the buffer, not the terminal")
        print("second captured line")
    captured = buffer.getvalue()
    print(f"  captured {len(captured.splitlines())} lines from stdout")
    print(f"  first captured line : {captured.splitlines()[0]!r}")
    print("  redirect_stdout temporarily points sys.stdout at our buffer, so")
    print("  code that prints can be captured or silenced without editing it -")
    print("  ideal for testing output or quieting a chatty library")

    print("--- ExitStack(): manage a DYNAMIC number of context managers ---")
    class Resource:
        def __init__(self, name, log):
            self.name, self.log = name, log
        def __enter__(self):
            self.log.append(f"open {self.name}")
            return self
        def __exit__(self, *exc):
            self.log.append(f"close {self.name}")

    log = []
    names = ["a", "b", "c"]                        # count known only at runtime
    with contextlib.ExitStack() as stack:
        resources = [stack.enter_context(Resource(n, log)) for n in names]
        log.append(f"using {len(resources)} resources")
    print(f"  event log : {log}")
    print("  a plain `with A, B, C:` needs the managers known at write time.")
    print("  ExitStack enters an arbitrary NUMBER of them and guarantees each")
    print("  is closed (in REVERSE order) - note close c, b, a on exit")

    print("--- the payoff: recurring try shapes become named with-blocks ---")
    print("  try/except Exc: pass          -> with suppress(Exc):")
    print("  save/restore sys.stdout       -> with redirect_stdout(buf):")
    print("  N nested with-statements       -> with ExitStack() as stack:")
    print("  each pattern now has a self-documenting name instead of hand-")
    print("  written try/finally or deep nesting")

    print("--- the constraint answered ---")
    print("  `with` automated cleanup, but common patterns around it were still")
    print("  boilerplate. contextlib (3.4) stocked the toolbox: suppress for")
    print("  ignoring a specific error, redirect_stdout for capturing output,")
    print("  ExitStack for a runtime-sized set of managers. recurring try/finally")
    print("  shapes became named, precise, self-documenting with-blocks")


if __name__ == "__main__":
    main()
