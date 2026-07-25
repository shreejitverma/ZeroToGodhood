"""Benchmark 153.1 - the right feature beats a fancier model.

A quality measurement. On the XOR problem (target positive when x1 and x2 have the same
sign), not linearly separable, a linear model on the RAW features is near chance. Adding
one engineered interaction feature (x1*x2) makes the problem linearly separable, and the
SAME linear model becomes near-perfect. Feature engineering can substitute for model
complexity.

See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import cross_val_score  # noqa: E402

from _harness.bench import provenance  # noqa: E402


def main():
    print("=== 153.1  feature engineering: raw vs one engineered interaction feature ===")
    print(provenance())
    print()

    rng = np.random.RandomState(0)
    n = 600
    x1 = rng.uniform(-1, 1, n)
    x2 = rng.uniform(-1, 1, n)
    y = (x1 * x2 > 0).astype(int)                    # XOR: same-sign

    model = LogisticRegression()
    raw = cross_val_score(model, np.column_stack([x1, x2]), y, cv=5).mean()
    eng = cross_val_score(model, np.column_stack([x1, x2, x1 * x2]), y, cv=5).mean()

    print(f"  linear model, raw features (x1, x2)     : {raw:.3f}")
    print(f"  linear model, + engineered x1*x2        : {eng:.3f}")
    print(f"  the same model gained (features only)   : {eng - raw:.3f}")

    print()
    print("Reading this. The same simple linear model jumps from near chance (0.56) to")
    print("near-perfect (0.97), with NO change to the model, only a better feature. The")
    print("XOR pattern (positive when signs agree) is invisible to a linear model in")
    print("the raw features, but the interaction x1*x2 encodes it directly, and the")
    print("model just reads it off. This is the most under-appreciated truth in applied")
    print("ML: the biggest gains usually come from FEATURES, not from a fancier model.")
    print("A domain-informed feature (a ratio, an interaction, a lag, an aggregate,")
    print("a time-of-day) that exposes the signal beats hyperparameter tuning and model")
    print("swapping. So invest in understanding the problem and engineering features")
    print("that encode what matters, and remember to engineer them leakage-free")
    print("(within the training fold, Chapters 66, 70). Deep U built the data tools,")
    print("Deep W the models; feature engineering is the bridge, and it is where the")
    print("domain knowledge that a model cannot learn on its own enters the pipeline.")


if __name__ == "__main__":
    main()
