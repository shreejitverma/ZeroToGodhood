"""Listing 98.1 - dtype is a memory/precision/speed choice: float32 vs float64.

A NumPy array's dtype fixes each element's WIDTH. float64 (the default) uses 8
bytes and ~15 significant digits; float32 uses 4 bytes and ~7. So float32 halves
the memory AND runs faster (half the memory bandwidth, more elements per SIMD
register, better cache use, the benchmark measures ~2x), at the cost of precision:
it loses digits, and cannot even represent every integer above 2^24. The choice is
a real engineering trade: float32 for large approximate data (ML embeddings,
weights, images) where memory/speed dominate; float64 for precision-sensitive
science. This listing shows the memory and precision facts (deterministic).
"""

import numpy as np


def main() -> None:
    print("--- width: float32 is half the memory of float64 ---")
    print(f"  float64 itemsize : {np.dtype(np.float64).itemsize} bytes")
    print(f"  float32 itemsize : {np.dtype(np.float32).itemsize} bytes")
    a64 = np.zeros(1_000_000, dtype=np.float64)
    a32 = np.zeros(1_000_000, dtype=np.float32)
    print(f"  1,000,000 float64 : {a64.nbytes:>9,} bytes")
    print(f"  1,000,000 float32 : {a32.nbytes:>9,} bytes  (half)")

    print("--- precision: float32 has ~7 significant digits, float64 ~15 ---")
    print(f"  float32 precision (digits) : {np.finfo(np.float32).precision}")
    print(f"  float64 precision (digits) : {np.finfo(np.float64).precision}")
    print(f"  float32(0.1)+float32(0.2) : {float(np.float32(0.1) + np.float32(0.2))!r}")
    print(f"  float64(0.1)+float64(0.2) : {float(np.float64(0.1) + np.float64(0.2))!r}")

    print("--- float32 cannot represent every integer above 2^24 ---")
    print(f"  float32(16_777_216) : {np.float32(16_777_216)}   (2^24, exact)")
    print(f"  float32(16_777_217) : {np.float32(16_777_217)}   (2^24+1, rounded down!)")
    print(f"  float64(16_777_217) : {np.float64(16_777_217)}   (exact)")

    print("--- the rule ---")
    print(f"  float32: large approximate data (ML, images) - half memory, ~2x speed")
    print(f"  float64: precision-sensitive science (accumulation, ill-conditioning)")


if __name__ == "__main__":
    main()
