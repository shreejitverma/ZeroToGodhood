"""Listing 200.1 - csv: the format that looks trivial and the module that isn't.

Chapter 118 ended where split(',') stops being safe: the moment a field can
CONTAIN the delimiter, delimited text needs a quoting grammar, and that
grammar is what the csv module implements. This listing shows the failure
that motivates the module (split corrupting a quoted field), the round-trip
contract (writer and reader inverse each other through quotes-in-quotes),
the dialect knobs that describe the wild files the world actually emits, and
DictReader/DictWriter as the schema-aware layer. All offline, all
deterministic, and every claim shaped as an equality check.
"""

import csv
import io


def main() -> None:
    print("--- why split(',') is a correctness bug, not a style choice ---")
    line = 'widget,"Acme, Inc.",1999'
    print(f"  the record : {line}")
    print(f"  split(',') : {line.split(',')}  <- 4 fields from 3")
    parsed = next(csv.reader([line]))
    print(f"  csv.reader : {parsed}")
    print("  a quoted field may contain the delimiter, the quote (doubled),")
    print("  and even newlines - the grammar cannot be regexed line-by-line,")
    print("  which is why the reader consumes an ITERABLE of lines, not a line")

    print("--- the round trip: writer and reader are inverses ---")
    rows = [["name", "quote", "note"],
            ["disk", 'the "fast" one', "usable, mostly"],
            ["tape", "multi\nline", "legacy"]]
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    wire = buffer.getvalue()
    print("  on the wire (escapes visible):")
    for raw_line in wire.splitlines():
        print(f"    {raw_line!r}")
    back = list(csv.reader(io.StringIO(wire)))
    print(f"  round-trip equality : {back == rows}")
    print("  quotes double inside quotes, embedded newlines survive inside a")
    print("  quoted field, and \\r\\n is the format's native line ending -")
    print("  which is why files open with newline='' (the module handles EOLs)")

    print("--- dialects: describing the files the world emits ---")
    tsv_wire = "a\tb 1\tc\n"
    print(f"  tab-separated : "
          f"{next(csv.reader([tsv_wire], delimiter=chr(9)))}")
    euro_wire = "3,14;2,71\n"
    print(f"  semicolon+comma-decimal : "
          f"{next(csv.reader([euro_wire], delimiter=';'))}")
    sniffed = csv.Sniffer().sniff("x;y;z\n1;2;3\n")
    print(f"  Sniffer guessed delimiter : {sniffed.delimiter!r}")
    print("  delimiter, quotechar, escapechar, quoting policy: a dialect is a")
    print("  parser configuration, and Sniffer is a HEURISTIC for unknown")
    print("  files - useful interactively, a gamble in pipelines (declare")
    print("  your dialect; sniff only what you must)")

    print("--- DictReader: rows with names, and the rules at the edges ---")
    data = "name,qty\nbolt,3\nnut,4,EXTRA\nwasher\n"
    for row in csv.DictReader(io.StringIO(data)):
        print(f"  {dict(row)}")
    print("  extra fields land in a None-keyed list (restkey), missing ones")
    print("  become None (restval): ragged rows are DESCRIBED, not dropped -")
    print("  detecting them is your validation's job, and the None key is")
    print("  the tell")

    print("--- the quoting policies, on one value ---")
    for policy, name in ((csv.QUOTE_MINIMAL, "QUOTE_MINIMAL"),
                         (csv.QUOTE_ALL, "QUOTE_ALL"),
                         (csv.QUOTE_NONNUMERIC, "QUOTE_NONNUMERIC")):
        out = io.StringIO()
        csv.writer(out, quoting=policy).writerow(["a,b", 7, "plain"])
        print(f"  {name:<16} : {out.getvalue().rstrip()}")
    print("  MINIMAL quotes only when forced (the default and the right one);")
    print("  NONNUMERIC additionally makes the READER parse unquoted fields")
    print("  as float - the only place csv does types; everything else is str")


if __name__ == "__main__":
    main()
