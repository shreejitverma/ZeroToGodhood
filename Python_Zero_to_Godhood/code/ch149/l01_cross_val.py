"""Listing 149.1 - cross-validation: a robust generalization estimate.

A single train/test split (Chapter 65) gives ONE estimate, and it is NOISY: which
samples happen to land in the test set swings the score (the benchmark shows a 10-point
spread across random seeds). CROSS-VALIDATION fixes this. k-fold CV splits the data into
k equal folds, then trains and evaluates k times, each fold held out as the test set once
while the other k-1 train. Every sample is thus used for testing exactly once and for
training k-1 times, and you average the k scores for a stable estimate (with a standard
deviation that quantifies its uncertainty). This listing shows 5-fold CV, deterministically.
"""

from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold, cross_val_score


def main() -> None:
    X, y = make_classification(n_samples=200, n_features=10, random_state=0)
    model = LogisticRegression(max_iter=1000)

    print("--- 5-fold cross-validation: train and evaluate 5 times ---")
    scores = cross_val_score(model, X, y, cv=5)
    print(f"  the 5 fold scores  : {[round(float(s), 3) for s in scores]}")
    print(f"  CV mean (estimate) : {round(float(scores.mean()), 3)}")
    print(f"  CV std (uncertainty): {round(float(scores.std()), 3)}")

    print("--- every sample is tested once, trained on k-1 times ---")
    kf = KFold(n_splits=5)
    tested = set()
    n_folds = 0
    for train_idx, test_idx in kf.split(X):
        n_folds += 1
        tested.update(test_idx.tolist())
    print(f"  number of folds        : {n_folds}")
    print(f"  every sample tested once : {len(tested) == len(X)}   ({len(tested)} of {len(X)})")

    print("--- report an estimate as mean +/- std, not a single number ---")
    print(f"  accuracy estimate : {round(float(scores.mean()), 2)} +/- {round(float(scores.std()), 2)}")
    print(f"  (a single split would report just one point in that range)")

    print("--- the rule ---")
    print(f"  use k-fold cross-validation for a stable generalization estimate: it")
    print(f"  averages over k splits so no single lucky/unlucky split misleads you")


if __name__ == "__main__":
    main()
