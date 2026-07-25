"""Listing 153.1 - feature engineering: the right feature beats a fancier model.

The single highest-leverage ML skill is not choosing a model, it is engineering FEATURES:
transforming raw data into inputs that expose the pattern. A model can only learn from
what the features encode. The XOR problem, target positive when x1 and x2 have the SAME
sign, is NOT linearly separable, so a linear model on the raw (x1, x2) features is near
chance. But adding ONE engineered feature, the interaction x1*x2 (which is positive
exactly when the signs agree), makes the problem trivially linear, and the SAME simple
model jumps to near-perfect. So feature engineering can substitute for model complexity:
often the biggest wins come from better features, not a bigger model. This listing shows
it, deterministically (cross-validated so the scores are stable).
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score


def main() -> None:
    rng = np.random.RandomState(0)
    n = 600
    x1 = rng.uniform(-1, 1, n)
    x2 = rng.uniform(-1, 1, n)
    # XOR-like target: 1 when x1 and x2 have the SAME sign (their product > 0)
    y = (x1 * x2 > 0).astype(int)

    model = LogisticRegression()

    print("--- raw features (x1, x2): the pattern is NOT linearly separable ---")
    X_raw = np.column_stack([x1, x2])
    raw = cross_val_score(model, X_raw, y, cv=5).mean()
    print(f"  linear model CV accuracy : {round(float(raw), 3)}   (near chance: XOR needs a curve)")

    print("--- add ONE engineered feature: the interaction x1 * x2 ---")
    X_eng = np.column_stack([x1, x2, x1 * x2])
    eng = cross_val_score(model, X_eng, y, cv=5).mean()
    print(f"  linear model CV accuracy : {round(float(eng), 3)}   (near-perfect: now linear!)")
    print(f"  the SAME model, better features, gained : {round(float(eng - raw), 3)}")

    print("--- why: the interaction directly encodes the pattern (same sign) ---")
    print(f"  x1*x2 > 0 exactly when the signs agree, so the target is now a")
    print(f"  linear function of the features; the model had the answer handed to it")

    print("--- common engineered features ---")
    print(f"  interactions (a*b), ratios (a/b), differences, aggregates, time features")
    print(f"  (Chapter 61), domain transforms, encodings (Chapter 63), binning")

    print("--- the rule ---")
    print(f"  invest in FEATURES, not just models: the right feature can let a simple")
    print(f"  model solve what looked like it needed a complex one (features > models)")


if __name__ == "__main__":
    main()
