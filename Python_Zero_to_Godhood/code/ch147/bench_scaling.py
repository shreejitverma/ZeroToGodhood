"""Benchmark 147.1 - feature scaling matters for scale-sensitive models.

A quality measurement. When features are on very different scales, a distance-based
model (KNN) lets the large-magnitude feature dominate the distance metric, degrading
accuracy. StandardScaler puts features on equal footing. This fits a KNN classifier on
data whose second feature is 1000x larger than the first, unscaled versus scaled (via a
leakage-free Pipeline), and compares held-out test accuracy.

See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from sklearn.datasets import make_classification  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.neighbors import KNeighborsClassifier  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from _harness.bench import provenance  # noqa: E402


def main():
    print("=== 147.1  KNN with features on a 1000x scale mismatch: unscaled vs scaled ===")
    print(provenance())
    print()

    X, y = make_classification(
        n_samples=400, n_features=2, n_redundant=0, n_informative=2,
        n_clusters_per_class=1, random_state=0,
    )
    X[:, 1] *= 1000                       # feature 1 is 1000x larger

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

    unscaled = KNeighborsClassifier().fit(X_train, y_train)
    scaled = make_pipeline(StandardScaler(), KNeighborsClassifier()).fit(X_train, y_train)

    print(f"  unscaled KNN test accuracy : {unscaled.score(X_test, y_test):.3f}")
    print(f"  scaled   KNN test accuracy : {scaled.score(X_test, y_test):.3f}")

    print()
    print("Reading this. Scaling improves the KNN's accuracy, because KNN classifies by")
    print("distance, and when one feature is 1000x larger it dominates the distance")
    print("entirely, the small feature contributes almost nothing, so the model is")
    print("effectively one-dimensional. StandardScaler rescales each feature to mean 0,")
    print("std 1, so all features contribute comparably. Scale-sensitive models (KNN,")
    print("SVM, k-means, anything distance- or gradient-based) REQUIRE scaling; tree")
    print("models (which split on thresholds per feature) do not. And the scaling is")
    print("done inside a Pipeline, so the scaler is fit on the TRAINING data only and")
    print("applied to test, never letting test statistics leak into training (Chapter")
    print("65). Preprocess with a Pipeline: it makes preprocessing part of the model")
    print("AND enforces the train/test boundary automatically.")


if __name__ == "__main__":
    main()
