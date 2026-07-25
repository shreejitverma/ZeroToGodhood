"""Benchmark 41.1 - one transaction vs a transaction per row.

Inserting N rows two ways with the SAME insert loop, differing only in
transaction scope. In autocommit mode (isolation_level=None) each INSERT is its
own transaction, and committing a transaction fsyncs the database to disk, so
this is N disk syncs. Wrapping the same loop in ONE explicit transaction commits
(and fsyncs) once. A third case, executemany in one transaction, shows the
smaller further gain from reducing Python-side call overhead.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import sqlite3, tempfile, os
d = tempfile.mkdtemp()
N = 5000
rows = [(i, f"name{i}") for i in range(N)]
_c = [0]

def _new(autocommit):
    _c[0] += 1
    path = os.path.join(d, f"db{_c[0]}.sqlite")
    con = sqlite3.connect(path, isolation_level=(None if autocommit else ""))
    con.execute("CREATE TABLE t(id INTEGER, name TEXT)")
    return con

def autocommit_per_row():
    con = _new(True)
    for r in rows:
        con.execute("INSERT INTO t VALUES (?,?)", r)   # each its own txn -> fsync
    con.close()

def one_transaction():
    con = _new(False)
    for r in rows:
        con.execute("INSERT INTO t VALUES (?,?)", r)   # same loop
    con.commit()                                       # one fsync
    con.close()

def executemany_one_txn():
    con = _new(False)
    con.executemany("INSERT INTO t VALUES (?,?)", rows)
    con.commit()
    con.close()
"""


def main() -> None:
    results = [
        measure("autocommit per row", "autocommit_per_row()", SETUP, number=1),
        measure("one transaction (loop)", "one_transaction()", SETUP, number=1),
        measure("executemany, one txn", "executemany_one_txn()", SETUP, number=1),
    ]
    report("41.1  inserting 5000 rows: transaction scope dominates",
           results, baseline="one transaction (loop)")

    print()
    print("Reading this. In autocommit mode every INSERT is its own transaction,")
    print("and each commit fsyncs the database file to disk, so 5000 rows is 5000")
    print("disk syncs, the dominant cost by far. Wrapping the same loop in one")
    print("transaction fsyncs once and is hundreds of times faster. executemany in")
    print("one transaction is a little faster still, by cutting Python-side call")
    print("overhead, but the big win is the transaction scope, not executemany.")
    print("Batch writes into explicit transactions; never insert row-by-row in")
    print("autocommit mode.")


if __name__ == "__main__":
    main()
