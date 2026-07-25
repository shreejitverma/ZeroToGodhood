"""Listing 145.1 - out-of-core processing: aggregate data larger than RAM in chunks.

pandas loads a whole dataset into memory, so it is bounded by RAM. When data is too big,
the answer is CHUNKING: stream the file in pieces (pd.read_csv(..., chunksize=n)),
process each chunk, and COMBINE partial results, never holding the whole dataset. A sum
or count is trivially chunkable (add partial sums); a groupby aggregation combines the
per-chunk group results. Peak memory then scales with the CHUNK size, not the DATASET
size (the benchmark: ~10x less). This is the on-one-machine form of distributed
processing (Dask, Spark do the same, across machines). This listing shows a chunked
groupby matching the whole-file result, deterministically.
"""

import os
import tempfile

import pandas as pd


def main() -> None:
    d = tempfile.mkdtemp()
    path = os.path.join(d, "data.csv")
    # a fixed, deterministic dataset: keys 0/1/2 with known values
    pd.DataFrame({
        "key": [0, 1, 2, 0, 1, 2, 0, 1],
        "v": [10, 20, 30, 40, 50, 60, 70, 80],
    }).to_csv(path, index=False)

    print("--- whole-file: load everything, then aggregate ---")
    whole = pd.read_csv(path)
    whole_result = whole.groupby("key")["v"].sum()
    print(f"  whole-file sum per key : {whole_result.to_dict()}")

    print("--- chunked: process 3 rows at a time, combine partial sums ---")
    partial = None
    n_chunks = 0
    for chunk in pd.read_csv(path, chunksize=3):        # never more than 3 rows in memory
        n_chunks += 1
        chunk_sum = chunk.groupby("key")["v"].sum()
        partial = chunk_sum if partial is None else partial.add(chunk_sum, fill_value=0)
    chunked_result = partial.astype(int)
    print(f"  number of chunks read  : {n_chunks}")
    print(f"  chunked sum per key    : {chunked_result.to_dict()}")

    print("--- the chunked result MATCHES the whole-file result ---")
    print(f"  results identical : {whole_result.to_dict() == chunked_result.to_dict()}")

    print("--- why: a sum is associative, so partial sums combine correctly ---")
    print(f"  key 0: 10+40+70 = {10 + 40 + 70}   (across chunks, summed)")

    os.remove(path)

    print("--- the rule ---")
    print(f"  process data larger than RAM in chunks: stream, aggregate each chunk,")
    print(f"  combine partials; peak memory scales with chunk size, not dataset size")


if __name__ == "__main__":
    main()
