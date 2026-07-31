"""Listing 239.1 - Python 2.7 (2010): argparse, declarative command-line parsing.

Parsing sys.argv by hand is deceptively awful: you loop over the list, track
which flags take values, coerce types, validate, generate --help text, and emit
usage errors - and everyone's hand-rolled version is subtly different and
incomplete. The stdlib had `optparse` (2.3) for options, but it did not handle
positional arguments and was declared done. Python 2.7 replaced it with
`argparse` (PEP 389): you DECLARE the arguments - names, types, defaults,
choices, help - and it does the parsing, coercion, validation, help generation,
and error reporting. Deep volumes own no CLI mechanism; this is the release that
made 'a real command-line interface' a declaration, not a parsing loop. To keep
output stable this listing sets prog= and feeds explicit argument lists rather
than reading sys.argv. Verified on current interpreters.
"""

import argparse
import contextlib
import io


def build_parser():
    p = argparse.ArgumentParser(
        prog="deploy",
        description="Deploy a service to an environment.",
    )
    p.add_argument("service", help="name of the service to deploy")
    p.add_argument("--env", choices=["dev", "staging", "prod"], default="dev",
                   help="target environment")
    p.add_argument("--replicas", type=int, default=1,
                   help="number of replicas")
    p.add_argument("--dry-run", action="store_true",
                   help="plan only, do not apply")
    return p


def main() -> None:
    parser = build_parser()

    print("--- you DECLARE arguments; argparse parses them into a Namespace ---")
    args = parser.parse_args(["billing", "--env", "prod", "--replicas", "3"])
    print(f"  parsed 'billing --env prod --replicas 3':")
    print(f"    service={args.service} env={args.env} "
          f"replicas={args.replicas} dry_run={args.dry_run}")
    print("  no parsing loop: each add_argument() declared a name, and argparse")
    print("  produced a Namespace with typed, defaulted attributes")

    print("--- types and defaults are applied for you ---")
    args2 = parser.parse_args(["billing", "--dry-run"])
    print(f"  parsed 'billing --dry-run':")
    print(f"    env={args2.env} (default), replicas={args2.replicas} "
          f"(default int), dry_run={args2.dry_run} (flag set True)")
    print(f"  --replicas is int : {type(args2.replicas).__name__} "
          f"(type=int coerced '3' -> 3 above)")
    print("  defaults fill unspecified options, type=int coerces the string,")
    print("  and store_true makes --dry-run a boolean flag. all declared, none")
    print("  hand-written")

    print("--- validation and choices are enforced automatically ---")
    # argparse prints a usage error to stderr and exits; redirect it so the
    # demo output is deterministic and we report the outcome ourselves.
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            parser.parse_args(["billing", "--env", "moon"])   # not in choices
        except SystemExit:
            print("  '--env moon' rejected: not in choices {dev, staging, prod}")
        try:
            parser.parse_args(["billing", "--replicas", "notanumber"])
        except SystemExit:
            print("  '--replicas notanumber' rejected: not a valid int")
    print("  argparse validates choices and types, prints a usage error, and")
    print("  exits - the error handling you would otherwise write by hand for")
    print("  every flag (it raises SystemExit, caught here for the demo)")

    print("--- generated --help: documentation from the declarations ---")
    help_text = parser.format_help()
    for line in help_text.rstrip().splitlines():
        print(f"  | {line}")
    print("  every argument's help= became a formatted --help screen, usage")
    print("  line included. you declared the interface once; the docs are free")

    print("--- the constraint answered ---")
    print("  hand-parsing sys.argv means re-implementing flags, types, defaults,")
    print("  validation, help, and errors - badly, every time. argparse (2.7)")
    print("  made the CLI a DECLARATION: state the arguments, get parsing,")
    print("  coercion, validation, help, and usage errors. that is why real")
    print("  Python command-line tools are built on it")


if __name__ == "__main__":
    main()
