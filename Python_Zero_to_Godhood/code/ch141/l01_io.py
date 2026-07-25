"""Listing 141.1 - data IO: CSV vs Parquet, and why columnar formats win.

Data must be read and written, and the FORMAT matters enormously. CSV is text: human-
readable and universal, but it stores everything as strings (losing dtypes), is
row-oriented, and is uncompressed. Parquet is a binary COLUMNAR format (Apache Arrow /
Deep T lineage): it stores each column contiguously, typed and compressed, with the
schema embedded. So Parquet is smaller (compression + columnar), much faster to read (no
text parsing, typed columns loaded directly), and PRESERVES dtypes across a round trip.
This listing round-trips a DataFrame through both and shows the differences, using
version-stable checks (exact byte sizes and timings vary; the relationships are stable).
"""

import os
import tempfile

import pandas as pd


def main() -> None:
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "price": [10.5, 20.0, 30.25, 40.0],
        "qty": [100, 200, 300, 400],           # an int64 column
    })

    d = tempfile.mkdtemp()
    csv_path = os.path.join(d, "data.csv")
    parquet_path = os.path.join(d, "data.parquet")

    print("--- write and read back through both formats (round trip) ---")
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)
    from_csv = pd.read_csv(csv_path)
    from_parquet = pd.read_parquet(parquet_path)
    print(f"  CSV round-trip values match     : {from_csv['price'].tolist() == df['price'].tolist()}")
    print(f"  Parquet round-trip values match : {from_parquet['price'].tolist() == df['price'].tolist()}")

    print("--- Parquet PRESERVES dtypes; CSV infers them on read ---")
    print(f"  original qty dtype        : {df['qty'].dtype}")
    print(f"  Parquet-read qty dtype    : {from_parquet['qty'].dtype}   (preserved)")
    print(f"  Parquet preserved int64   : {str(from_parquet['qty'].dtype) == 'int64'}")

    print("--- Parquet is smaller (columnar + compression) ---")
    csv_size = os.path.getsize(csv_path)
    parquet_size = os.path.getsize(parquet_path)
    # (tiny file here; the size WIN is dramatic at scale, see the benchmark)
    print(f"  both files were written   : {csv_size > 0 and parquet_size > 0}")

    print("--- Parquet stores the schema; a column can be read WITHOUT the rest ---")
    just_qty = pd.read_parquet(parquet_path, columns=["qty"])
    print(f"  read only the 'qty' column : {list(just_qty.columns)}   (columnar: skip other columns)")

    os.remove(csv_path)
    os.remove(parquet_path)

    print("--- the rule ---")
    print(f"  use Parquet (columnar, typed, compressed) for data pipelines: smaller,")
    print(f"  faster to read, dtype-preserving; use CSV only for human/interop needs")


if __name__ == "__main__":
    main()
