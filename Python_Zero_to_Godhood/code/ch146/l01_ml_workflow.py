"""Listing 146.1 - the machine-learning workflow: fit, predict, score, and train/test split.

scikit-learn is the standard ML library, and it has ONE consistent API (the estimator
interface) across every model:
  - model.fit(X, y)      learn from training data (X = features matrix, y = target)
  - model.predict(X)     predict targets for new data
  - model.score(X, y)    evaluate (R^2 for regression, accuracy for classification)
Every algorithm, linear regression, random forest, neural net, uses this same interface,
so you swap models by changing one line. The CARDINAL rule: evaluate on a HELD-OUT TEST
set, never on training data, because a model can memorize its training data and look
perfect while generalizing poorly (the benchmark). train_test_split (with a fixed
random_state) makes the split reproducible. This listing shows the API deterministically.
"""

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split


def main() -> None:
    print("--- the estimator API: fit, predict, score ---")
    X = np.arange(20).reshape(-1, 1).astype(float)     # feature matrix (20 samples, 1 feature)
    y = 2 * X.ravel() + 1                               # target: y = 2x + 1 exactly

    model = LinearRegression().fit(X, y)               # LEARN
    print(f"  learned slope     : {round(float(model.coef_[0]), 4)}   (true: 2)")
    print(f"  learned intercept : {round(float(model.intercept_), 4)}   (true: 1)")
    print(f"  predict(x=100)    : {round(float(model.predict([[100.0]])[0]), 4)}   (2*100+1)")
    print(f"  score (R^2)       : {round(float(model.score(X, y)), 4)}   (1.0 = perfect fit)")

    print("--- train/test split: reproducible with a fixed random_state ---")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )
    print(f"  train size : {len(X_train)}   test size : {len(X_test)}")
    print(f"  test samples (sorted x) : {sorted(X_test.ravel().tolist())}")

    print("--- same random_state -> same split (reproducible experiments) ---")
    _, X_test2, _, _ = train_test_split(X, y, test_size=0.25, random_state=42)
    print(f"  identical split on re-run : {sorted(X_test.ravel().tolist()) == sorted(X_test2.ravel().tolist())}")

    print("--- one API, any model: fit on train, score on TEST ---")
    m = LinearRegression().fit(X_train, y_train)
    print(f"  test R^2 (evaluate on held-out data) : {round(float(m.score(X_test, y_test)), 4)}")

    print("--- the rule ---")
    print(f"  fit/predict/score is the universal estimator API; ALWAYS evaluate on a")
    print(f"  held-out test set (fixed random_state for reproducibility), never on train")


if __name__ == "__main__":
    main()
