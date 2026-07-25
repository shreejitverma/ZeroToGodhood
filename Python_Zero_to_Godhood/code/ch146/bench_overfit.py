"""Benchmark 146.1 - why you must evaluate on held-out data: overfitting.

A CORRECTNESS/quality measurement, not timing. A k=1 nearest-neighbor regressor
MEMORIZES its training data: for each training point it predicts that exact point, so
its TRAINING score is a perfect 1.0. But on held-out TEST data it generalizes worse. A
k=5 model has a LOWER training score (it cannot memorize) yet a HIGHER test score (it
generalizes better). So the training score is a misleading, optimistic estimate, and the
perfect training score of the memorizing model is the danger sign of overfitting.

See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.neighbors import KNeighborsRegressor  # noqa: E402

from _harness.bench import provenance  # noqa: E402


def main():
    print("=== 146.1  overfitting: training score vs held-out test score ===")
    print(provenance())
    print()

    rng = np.random.RandomState(0)
    X = np.linspace(0, 10, 100).reshape(-1, 1)
    y = np.sin(X.ravel()) + rng.normal(0, 0.2, 100)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

    k1 = KNeighborsRegressor(n_neighbors=1).fit(X_train, y_train)
    k5 = KNeighborsRegressor(n_neighbors=5).fit(X_train, y_train)

    print(f"  k=1 (memorizes) : train R2 = {k1.score(X_train, y_train):.4f}   test R2 = {k1.score(X_test, y_test):.4f}")
    print(f"  k=5 (generalizes): train R2 = {k5.score(X_train, y_train):.4f}   test R2 = {k5.score(X_test, y_test):.4f}")

    print()
    print("Reading this. The k=1 model scores a PERFECT 1.0 on training data, it")
    print("predicts each training point as itself, but only 0.84 on held-out test")
    print("data: it memorized rather than learned. The k=5 model scores LOWER on")
    print("training (0.94, it cannot memorize) yet HIGHER on test (0.89): it")
    print("generalizes better. This is overfitting, and it is why the single most")
    print("important rule in machine learning is: NEVER judge a model by its training")
    print("score. A model that fits its training data perfectly has almost certainly")
    print("memorized noise and will fail on new data. Always evaluate on a held-out")
    print("test set (and, better, with cross-validation), and treat a suspiciously")
    print("high training score as a warning, not a success. The whole discipline of")
    print("ML evaluation exists to measure GENERALIZATION, not memorization.")


if __name__ == "__main__":
    main()
