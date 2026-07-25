"""Listing 150.1 - tree ensembles: many weak trees beat one, and give feature importance.

A single DECISION TREE splits the data on feature thresholds until each leaf is pure. Grown
fully, it MEMORIZES the training data (train accuracy 1.0) and overfits (Chapter 65). The
fix is an ENSEMBLE: a RANDOM FOREST trains many trees, each on a bootstrap sample of the
data and a random subset of features, and averages their votes. The individual trees still
overfit, but their errors are DIVERSE and average out, so the forest generalizes far
better. Ensembles (random forests, gradient boosting) are the workhorse of tabular ML, and
they need NO feature scaling (trees split per feature, Chapter 66). Trees also expose
FEATURE IMPORTANCES (which features drive predictions). This listing shows all three.
"""

import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier


def main() -> None:
    X, y = make_classification(n_samples=1000, n_features=20, n_informative=10, random_state=0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

    print("--- a single deep decision tree MEMORIZES and overfits ---")
    tree = DecisionTreeClassifier(random_state=0).fit(X_train, y_train)
    print(f"  tree  train accuracy : {round(tree.score(X_train, y_train), 3)}   (memorized)")
    print(f"  tree  test accuracy  : {round(tree.score(X_test, y_test), 3)}   (overfit: big gap)")

    print("--- a random forest (100 trees) averages out the overfitting ---")
    forest = RandomForestClassifier(n_estimators=100, random_state=0).fit(X_train, y_train)
    print(f"  forest train accuracy : {round(forest.score(X_train, y_train), 3)}")
    print(f"  forest test accuracy  : {round(forest.score(X_test, y_test), 3)}   (better generalization)")
    print(f"  forest beats the single tree on test : {forest.score(X_test, y_test) > tree.score(X_test, y_test)}")

    print("--- ensembles give FEATURE IMPORTANCES (which features matter) ---")
    importances = forest.feature_importances_
    top3 = sorted(np.argsort(importances)[-3:].tolist())
    print(f"  top-3 most important feature indices : {top3}")
    print(f"  importances sum to ~1.0 : {round(float(importances.sum()), 6) == 1.0}")

    print("--- trees need NO scaling (they split per feature, Chapter 66) ---")
    print(f"  forest is scale-invariant : unlike KNN/SVM, no StandardScaler needed")

    print("--- the rule ---")
    print(f"  ensembles (random forest, gradient boosting) turn many overfitting trees")
    print(f"  into a strong, generalizing model; they need no scaling and rank features")


if __name__ == "__main__":
    main()
