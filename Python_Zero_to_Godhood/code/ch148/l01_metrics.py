"""Listing 148.1 - classification metrics: why accuracy lies on imbalanced data.

Accuracy (fraction correct) is the intuitive classification metric, and it is DANGEROUS
on IMBALANCED data. If 95% of examples are negative, a useless model that ALWAYS predicts
negative scores 95% accuracy while catching NONE of the positives, which are usually the
cases you care about (fraud, disease, a rare signal). The honest metrics come from the
CONFUSION MATRIX (true/false positives/negatives):
  - precision = TP / (TP + FP): of predicted positives, how many are right.
  - recall    = TP / (TP + FN): of actual positives, how many you caught.
  - F1        = harmonic mean of precision and recall (one balanced number).
This listing shows the accuracy trap and the honest metrics, deterministically.
"""

import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)


def main() -> None:
    # imbalanced: 95 negatives, 5 positives
    y_true = np.array([0] * 95 + [1] * 5)

    print("--- the trap: a useless always-negative model looks accurate ---")
    y_majority = np.zeros(100, dtype=int)        # always predicts the majority class
    print(f"  always-negative accuracy : {accuracy_score(y_true, y_majority)}   (looks great!)")
    print(f"  but recall of positives  : {recall_score(y_true, y_majority, zero_division=0)}   (catches NONE)")
    print(f"  -> 95% accuracy, 0% useful: accuracy hid a worthless model")

    print("--- the honest metrics from the confusion matrix ---")
    y_pred = y_true.copy()
    y_pred[0] = 1                                 # 1 false positive
    y_pred[96] = 0                                # 1 false negative
    cm = confusion_matrix(y_true, y_pred)
    print(f"  confusion matrix [[TN, FP], [FN, TP]] : {cm.tolist()}")
    print(f"  accuracy  : {accuracy_score(y_true, y_pred)}")
    print(f"  precision : {round(float(precision_score(y_true, y_pred)), 3)}   (of predicted +, how many right)")
    print(f"  recall    : {round(float(recall_score(y_true, y_pred)), 3)}   (of actual +, how many caught)")
    print(f"  F1        : {round(float(f1_score(y_true, y_pred)), 3)}   (balance of precision and recall)")

    print("--- precision vs recall is a TRADE-OFF you choose by the cost of errors ---")
    print(f"  fraud/disease: maximize RECALL (missing a positive is costly)")
    print(f"  spam filter  : maximize PRECISION (a false positive is costly)")

    print("--- the rule ---")
    print(f"  never judge a classifier by accuracy on imbalanced data; use precision,")
    print(f"  recall, F1 (and the confusion matrix), and choose by the cost of errors")


if __name__ == "__main__":
    main()
