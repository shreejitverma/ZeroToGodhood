# Chapter 41: SQLite and Transactions

A data-import script inserts 5,000 rows into a SQLite database and takes almost two seconds, and the
developer concludes SQLite is slow. It is not; the script is committing 5,000 times. In SQLite's default
autocommit mode each `INSERT` is its own transaction, and committing a transaction *fsyncs the database
file to disk*, so 5,000 rows is 5,000 disk syncs. Wrap the identical insert loop in a single explicit
transaction, one commit, one sync, and the same 5,000 rows land in a few milliseconds, **hundreds of times
faster** (measured ~300x under load, ~600x on a quiet disk; the exact figure is disk-dependent, the order
of magnitude is not). The database was never the bottleneck. The transaction *scope* was.

That is the dominant performance fact about SQLite, and it sits beside the dominant *correctness* fact:
always pass values as `?` parameters, never format them into the SQL string, because string-formatted SQL
is the SQL-injection hole. This chapter continues **Deep R** with SQLite, the full SQL database that ships
in the standard library, and the two disciplines, parameterized queries and batched transactions, that make
it safe and fast. It builds directly on Chapter 40's buffering-and-fsync model: a transaction commit is the
`fsync` of the database world.

## Section index

- **41.1** Parameterized queries and transactions
- **41.2** Why autocommit-per-row is slow
- **41.3** Measurement: transaction scope dominates
- **41.4** Edges and failure modes
- **41.5** Connections
- **41.6** Exercises
- **41.7** Summary and cross-references

Listings live under `code/ch041/` and are re-executed by `make verify` on both interpreters.

---

## 41.1 Parameterized queries and transactions

```python
# code/ch041/l01_sqlite.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- parameterized insert: values as ? params, never string-formatted ---
--- query with a parameter (safe even with hostile input) ---
  lookup of injection string : None
  table still exists         : 4 rows
--- ordered query ---
  Ada      36
  Guido    69
  Bjarne   70
  Grace    85
--- a transaction is atomic: rollback undoes the whole block ---
  caught: simulated failure mid-transaction
  rows after rollback        : 4 (Temp not saved)
```

**Parameterized queries** are the security spine. Values go in as `?` placeholders with a separate tuple of
arguments; SQLite treats them as *data*, never as SQL. The listing looks up the hostile string
`"Ada'; DROP TABLE users; --"`, and the result is `None` and the table survives with all 4 rows, because
the string is matched as a literal name, not executed as a statement. Had the code built the query with an
f-string, that input would have run the `DROP TABLE`. **Never** interpolate values into SQL; always pass
them as parameters. This is not a style preference, it is the difference between a safe query and a
remote-code-execution hole.

**Transactions** are the correctness-and-performance spine. `con.commit()` ends a transaction; the `with
con:` block commits on success and *rolls back on any exception*, so the failed insert of `"Temp"` leaves
no trace, the count stays 4. A transaction is atomic (all-or-nothing) and durable (committed data survives a
crash), and it is exactly that durability, the disk sync at commit, that makes the *number* of commits the
performance story of §41.3.

---

## 41.2 Why autocommit-per-row is slow

SQLite's default connection is in autocommit mode until a statement opens a transaction, and in the naive
row-by-row pattern each `INSERT` runs and commits on its own. Committing is not free: to keep its atomicity
and durability guarantees, SQLite must ensure the write reaches stable storage, an `fsync` (the same disk
sync Chapter 40 named). One `fsync` takes on the order of hundreds of microseconds to milliseconds,
dominated by the storage device, and doing it per row means the insert loop's time is essentially
`N x (one disk sync)`, regardless of how trivial each row is.

Wrapping the loop in one transaction changes the arithmetic to `1 x (one disk sync)` plus the actual work
of buffering N rows. The rows accumulate in SQLite's page cache and are written and synced once at commit.
This is the database-layer version of Chapter 40's rule, batch the expensive boundary crossing, and here
the boundary is the durability sync, which is even more expensive than the plain `write()` syscall. The
`executemany` form adds a further, smaller gain by cutting Python-side per-statement overhead, but the
first-order win, the hundreds-fold one, is the transaction scope.

---

## 41.3 Measurement: transaction scope dominates

**Methodology.** `code/ch041/bench_transaction.py`. Inserting 5,000 rows with the *same* insert loop, in
autocommit mode (each row its own transaction) versus one explicit transaction; plus `executemany` in one
transaction. `min` over runs. This is fsync-bound and therefore highly disk-dependent and noisy, the
autocommit case's variance is large and the harness flags it machine-busy, so the finding is the order of
magnitude, not a precise multiple. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 5,000 inserts | min per run | per row | vs one-txn |
|---|---|---|---|
| autocommit, per-row transaction | **~1000 ms** (varies widely) | **~200-400 us** | **hundreds of x slower** |
| one transaction (same loop) | **~3.5 ms** | **~0.7 us** | 1.00x |
| `executemany`, one transaction | **~2.3 ms** | **~0.5 us** | ~0.65x (a bit faster) |

The autocommit case spends **~200-400 microseconds per row**, essentially the cost of one disk sync per
row, and its wall-clock varies by an order of magnitude with disk state (measured ~300x slower than
one-transaction under load, ~600x on a quiet disk). The one-transaction loop spends **~0.7 us per row**,
because the rows batch and sync once. `executemany` shaves that to **~0.5 us** by reducing Python-side call
overhead. The precise multiple is not the point and cannot be, it is a disk-timing figure; the point is
that transaction scope changes the cost by *orders of magnitude*, and no amount of query tuning matters
until the commits are batched.

The rule: **batch writes into explicit transactions; never insert row-by-row in autocommit mode.** Group
related writes (an import, a batch of events, a unit of work) into one transaction and commit once. Use
`executemany` for the further Python-side savings when inserting many uniform rows. And when read
concurrency matters, enable WAL mode (`PRAGMA journal_mode=WAL`), which lets readers proceed during a
writer, a separate lever on the same durability machinery.

---

## 41.4 Edges and failure modes

**String-formatted SQL.** §41.1. Building a query with an f-string or `%` from user input is the SQL-
injection vulnerability. Always use `?` parameters (or named `:name` parameters). There is no exception for
"trusted" input, parameterize everything.

**Autocommit per row.** §41.3. The hundreds-fold slowdown. Wrap bulk writes in one transaction.

**Forgetting to commit.** In the default (non-autocommit) mode, uncommitted writes are lost when the
connection closes without `commit()`. Use `with con:` so the commit (or rollback) is guaranteed.

**A giant single transaction.** The opposite extreme: one transaction over millions of rows holds a write
lock and accumulates a large rollback journal, blocking other writers for its whole duration. Batch into
transactions of thousands to tens of thousands of rows, not one transaction for everything and not one per
row.

**Sharing a connection across threads.** By default a SQLite connection object may not be used from a thread
other than the one that created it (`check_same_thread`). Give each thread its own connection, or use a
connection pool; do not share one across threads casually.

**Type affinity surprises.** SQLite has dynamic typing (type *affinity*, not strict types): a column can
hold values of the "wrong" type. Validate types in Python if you need strictness; do not assume the schema
enforces them the way a stricter database would.

**`fsync` and `PRAGMA synchronous`.** The durability cost §41.3 measures can be traded away with `PRAGMA
synchronous=OFF`, which makes commits fast but *unsafe* (a crash can corrupt the database). Do not reach for
it to "fix" the autocommit slowdown; batch transactions instead, which is fast *and* safe.

---

## 41.5 Connections

**Backward.** The `fsync`/durability model a commit rests on is Chapter 40, a transaction commit is the
database's `fsync`. The `with`-block that makes commit/rollback automatic is the context-manager protocol of
Chapter 5. The parameter-passing that prevents injection is the same string-versus-data boundary as
Chapter 7's text handling, here with security stakes.

**Forward.** Serializing richer Python objects than SQLite's columns hold (`json`, `pickle`) is the next
Deep R material. Concurrency across connections and processes touches the GIL and multiprocessing themes
(Chapter 8 and Deep L). The on-disk B-tree and page cache SQLite uses are a storage-engine topic flagged in
**Deep R**.

**Across books.** SQLite is how Book II persists structured state at the edges before it reaches
**Book III**: a job queue, a cache of computed results, a small metadata store. A **Book III** pipeline that
checkpoints progress or memoizes expensive results to SQLite batches its writes into transactions, so
checkpointing costs one sync per batch, not one per record. The §41.3 discipline is what keeps persistence
from dominating the pipeline's time. **Deep U** owns the persistence seam.

---

## 41.6 Exercises

**1. Reproduce the transaction gap.** Insert several thousand rows in autocommit mode and in one
transaction, and confirm the order-of-magnitude difference. Explain, in terms of `fsync`, why the gap is so
large and why the exact multiple varies with the disk.

**2. Prove the injection safety.** Query for a name containing `'; DROP TABLE ...; --` passed as a `?`
parameter and confirm the table survives. Then (in a *throwaway* database) build the same query with an
f-string and show the injection would execute. Explain what the parameter binding does differently.

**3. Roll back on failure.** Use `with con:` to run a block of inserts that raises partway through, and
confirm none of the block's rows persist. Explain the atomicity guarantee and why `with con:` is safer than
a manual `commit()`.

**4. Find the sweet spot.** Insert a million rows in one giant transaction, then in batches of 10,000, and
compare wall-clock and peak journal size. Explain why neither one-per-row nor one-giant-transaction is
ideal.

**5. The design question.** SQLite makes every commit durable by default (`fsync`), which is what makes
autocommit-per-row slow. Argue why that default is correct even though it creates the performance trap. Your
answer must address the atomicity/durability guarantees a transaction provides, why `PRAGMA synchronous=OFF`
is the wrong fix, and why batching transactions gives both safety and speed.

---

## 41.7 Summary and cross-references

- **SQLite** is a full SQL database in the standard library, backed by one file (or `:memory:`).
- **Always parameterize:** pass values as `?` placeholders, never format them into the SQL string. String-
  formatted SQL is the injection vulnerability; parameters treat input as data.
- **Transactions are atomic and durable;** `with con:` commits on success and rolls back on exception. A
  commit `fsync`s the database.
- **Measured:** inserting 5,000 rows autocommit-per-row is **hundreds of times slower** (~200-400 us/row, a
  disk sync each) than one transaction (~0.7 us/row); `executemany` adds a smaller further gain. The exact
  multiple is disk-dependent; the order of magnitude is the point. **Batch writes into explicit
  transactions.**

**Cross-references.** `fsync` and durability → Chapter 40. Context managers → Chapter 5. String-vs-data and
injection → Chapter 7. Serialization (`json`/`pickle`) → the next Deep R chapters. The persistence seam →
Deep U.
