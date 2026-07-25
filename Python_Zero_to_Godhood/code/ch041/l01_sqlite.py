"""Listing 41.1 - sqlite3: parameterized queries, transactions, executemany.

sqlite3 is a full SQL database in the standard library, backed by a single file
(or :memory:). Two disciplines dominate correct, fast use: ALWAYS pass values as
parameters (? placeholders), never string-format them into SQL (that is the SQL-
injection hole); and wrap many writes in ONE transaction, because each committed
transaction fsyncs to disk. This listing shows both; the benchmark shows what
the transaction discipline is worth.
"""

import sqlite3


def main() -> None:
    con = sqlite3.connect(":memory:")     # an in-process database, no file
    con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")

    print("--- parameterized insert: values as ? params, never string-formatted ---")
    con.execute("INSERT INTO users(name, age) VALUES (?, ?)", ("Ada", 36))
    con.executemany(
        "INSERT INTO users(name, age) VALUES (?, ?)",
        [("Bjarne", 70), ("Grace", 85), ("Guido", 69)],
    )
    con.commit()                          # one commit for all the writes above

    print("--- query with a parameter (safe even with hostile input) ---")
    hostile = "Ada'; DROP TABLE users; --"
    row = con.execute("SELECT id, name, age FROM users WHERE name = ?", (hostile,)).fetchone()
    print(f"  lookup of injection string : {row}")   # None: treated as a literal, not SQL
    print(f"  table still exists         : {con.execute('SELECT count(*) FROM users').fetchone()[0]} rows")

    print("--- ordered query ---")
    for r in con.execute("SELECT name, age FROM users ORDER BY age"):
        print(f"  {r[0]:8} {r[1]}")

    print("--- a transaction is atomic: rollback undoes the whole block ---")
    try:
        with con:                          # commits on success, rolls back on exception
            con.execute("INSERT INTO users(name, age) VALUES (?, ?)", ("Temp", 1))
            raise ValueError("simulated failure mid-transaction")
    except ValueError as e:
        print(f"  caught: {e}")
    print(f"  rows after rollback        : {con.execute('SELECT count(*) FROM users').fetchone()[0]} (Temp not saved)")

    con.close()


if __name__ == "__main__":
    main()
