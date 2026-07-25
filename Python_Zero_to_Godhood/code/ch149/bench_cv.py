"""Benchmark 149.1 - a single split is noisy; cross-validation is stable.

A quality measurement. A single train/test split's score depends on WHICH samples land
in the test set, so it swings with the random seed. Cross-validation averages over k
folds, giving a stable estimate. This compares the spread of single-split scores across
10 random seeds against the tight 5-fold CV estimate, for the same model and data.

See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from sklearn.datasets import make_classification  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import cross_val_score, train_test_split  # noqa: E402

from _harness.bench import provenance  # noqa: E402


def main():
    print("=== 149.1  single-split noise vs cross-validation stability ===")
    print(provenance())
    print()

    X, y = make_classification(n_samples=200, n_features=10, random_state=0)
    model = LogisticRegression(max_iter=1000)

    single = []
    for seed in range(10):
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=seed)
        single.append(model.fit(X_tr, y_tr).score(X_te, y_te))
    single = np.array(single)

    cv = cross_val_score(model, X, y, cv=5)

    print(f"  single split, 10 seeds : min {single.min():.3f}  max {single.max():.3f}  spread {single.max() - single.min():.3f}")
    print(f"  5-fold CV              : mean {cv.mean():.3f}  std {cv.std():.3f}")

    print()
    print("Reading this. A single train/test split gives one score, but that score")
    print("swings by 10 percentage points (0.875 to 0.975) depending only on the")
    print("random seed, on WHICH samples happened to land in the test set. So a single")
    print("split can report anywhere in a wide range, and two people splitting the same")
    print("data differently can reach opposite conclusions about a model. Cross-")
    print("validation averages over 5 folds into a stable estimate (0.93) with a small")
    print("standard deviation (0.03) that quantifies the remaining uncertainty, and it")
    print("uses every sample for both training and testing, more efficient with")
    print("limited data. So report a model's performance as a CROSS-VALIDATED mean")
    print("+/- std, not a single-split point, and use CV (with pipelines inside it,")
    print("Chapter 66) for model selection. A single split is for a final held-out")
    print("check; cross-validation is for reliable estimation and comparison.")


if __name__ == "__main__":
    main()
