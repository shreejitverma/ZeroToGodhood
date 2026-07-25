"""Benchmark 150.1 - a random forest generalizes far better than a single tree.

A quality measurement. A single fully-grown decision tree memorizes its training data
(train accuracy 1.0) and overfits. A random forest of 100 such trees, each trained on a
bootstrap sample and a random feature subset, averages their diverse errors and
generalizes much better. This compares their test accuracy on the same data.

See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sklearn.datasets import make_classification  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402

from _harness.bench import provenance  # noqa: E402


def main():
    print("=== 150.1  single decision tree vs 100-tree random forest ===")
    print(provenance())
    print()

    X, y = make_classification(n_samples=1000, n_features=20, n_informative=10, random_state=0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

    tree = DecisionTreeClassifier(random_state=0).fit(X_train, y_train)
    forest = RandomForestClassifier(n_estimators=100, random_state=0).fit(X_train, y_train)

    print(f"  single tree   : train {tree.score(X_train, y_train):.3f}   test {tree.score(X_test, y_test):.3f}   gap {tree.score(X_train, y_train) - tree.score(X_test, y_test):.3f}")
    print(f"  forest (100)  : train {forest.score(X_train, y_train):.3f}   test {forest.score(X_test, y_test):.3f}   gap {forest.score(X_train, y_train) - forest.score(X_test, y_test):.3f}")

    print()
    print("Reading this. Both models memorize the training data (train accuracy 1.0),")
    print("but on held-out test data the single tree scores 0.77 and the forest 0.85,")
    print("the forest generalizes much better. The reason is variance reduction: a")
    print("single deep tree is high-variance (small data changes swing it wildly, it")
    print("fits noise), but a forest of 100 trees, each trained on a different")
    print("bootstrap sample and a random feature subset, makes DIVERSE errors that")
    print("average out, keeping the signal and cancelling the noise. This is why")
    print("random forests and gradient-boosted trees (XGBoost, LightGBM) are the")
    print("dominant algorithms for TABULAR data: strong out of the box, no feature")
    print("scaling needed (trees split per feature), robust to irrelevant features,")
    print("and they rank feature importance. For a table of features, an ensemble of")
    print("trees is the sensible first model, not a single tree, and rarely a neural")
    print("net (which wins on images/text/sequences, not tabular).")


if __name__ == "__main__":
    main()
