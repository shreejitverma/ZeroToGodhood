"""Listing 276.1 - Python 3.11 (2022): Exception.add_note(), context added as an error propagates.

An exception raised deep in a library often lacks the CONTEXT the caller needs:
'invalid value' is true but useless without 'while parsing row 47 of orders.csv'.
The old fix was to catch and re-raise with a new message - which loses the
original type and traceback - or to wrap in a new exception. Python 3.11's PEP
678 added Exception.add_note(): attach one or more strings to an existing
exception WITHOUT changing its type or traceback. Each layer that catches it can
add what it knows and re-raise the SAME exception; the notes accumulate and print
in the traceback. Deep B owns the exception model; this is the release that let
an error gather context as it travels up the stack. Verified on current
interpreters.
"""


def parse_value(text):
    return int(text)                             # raises ValueError on bad input


def parse_row(row, line_number):
    try:
        return parse_value(row)
    except ValueError as exc:
        exc.add_note(f"while parsing row {line_number}")  # add context, re-raise SAME exc
        raise


def load_file(rows, filename):
    try:
        return [parse_row(r, i) for i, r in enumerate(rows, 1)]
    except ValueError as exc:
        exc.add_note(f"in file {filename!r}")    # another layer adds more context
        raise


def main() -> None:
    print("--- add_note attaches context without changing the exception ---")
    try:
        parse_row("notanumber", 47)
    except ValueError as exc:
        print(f"  exception type is still : {type(exc).__name__}")
        print(f"  original message intact : {exc.args[0]!r}")
        print(f"  exc.__notes__ : {exc.__notes__}")
    print("  add_note() did NOT wrap or replace the ValueError - it is the SAME")
    print("  exception, same type, same message, same traceback, now carrying an")
    print("  extra note. the note lives in exc.__notes__")

    print("--- notes ACCUMULATE as the exception travels up through layers ---")
    try:
        load_file(["10", "20", "bad", "40"], "orders.csv")
    except ValueError as exc:
        print(f"  final exception type : {type(exc).__name__}")
        print(f"  all accumulated notes :")
        for note in exc.__notes__:
            print(f"    - {note}")
    print("  parse_row added 'while parsing row 3', then load_file added 'in")
    print("  file orders.csv' to the SAME exception. each layer contributed what")
    print("  it knew; the notes stack up in order, low-level first")

    print("--- the notes appear in the printed traceback ---")
    import traceback
    try:
        load_file(["ok" if False else "x"], "data.csv")
    except ValueError as exc:
        tb = traceback.format_exc()
    note_lines = [ln for ln in tb.splitlines()
                  if ln.strip() in ("while parsing row 1", "in file 'data.csv'")]
    print(f"  traceback contains the note lines : {note_lines}")
    print("  the notes print beneath the exception in the traceback, so whoever")
    print("  reads the crash sees the gathered context - not just 'invalid")
    print("  literal for int()' with no idea where it came from")

    print("--- why this beats catch-and-re-raise-with-new-message ---")
    print("  re-raising `raise ValueError(f'row {n}: {exc}')` DISCARDS the")
    print("  original exception's type and its traceback, and nests messages")
    print("  awkwardly. add_note keeps the exact exception and its traceback")
    print("  and simply annotates it - context WITHOUT loss")

    print("--- the constraint answered ---")
    print("  an exception from deep code lacked the caller's context, and adding")
    print("  it meant re-raising a NEW exception that lost the original type and")
    print("  traceback. add_note() (3.11) attaches context strings to the SAME")
    print("  exception as it propagates, so each layer annotates what it knows")
    print("  and the traceback shows the full, accumulated story")


if __name__ == "__main__":
    main()
