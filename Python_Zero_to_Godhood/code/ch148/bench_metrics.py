"""Benchmark 148.1 - accuracy hides a worthless model on imbalanced data.

A quality measurement. On a 95%-negative dataset, a useless model that always predicts
the majority class is compared with a real model that catches most positives. Accuracy
ranks them almost the same (95% vs 98%), hiding that the majority model catches ZERO
positives (recall 0). Recall and F1 expose the difference. This is why accuracy is the
wrong metric for imbalanced classification.

See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score, recall_score  # noqa: E402

from _harness.bench import provenance  # noqa: E402


def main():
    print("=== 148.1  imbalanced classification: accuracy vs recall/F1 ===")
    print(provenance())
    print()

    y_true = np.array([0] * 95 + [1] * 5)             # 95 negative, 5 positive

    majority = np.zeros(100, dtype=int)               # always predicts negative
    real = y_true.copy()
    real[0] = 1                                       # 1 false positive
    real[96] = 0                                      # 1 false negative (catches 4 of 5)

    print("  model                | accuracy | recall | F1")
    print(f"  always-negative      |   {accuracy_score(y_true, majority):.2f}   |  {recall_score(y_true, majority, zero_division=0):.2f}  | {f1_score(y_true, majority, zero_division=0):.2f}")
    print(f"  real (catches 4 of 5)|   {accuracy_score(y_true, real):.2f}   |  {recall_score(y_true, real):.2f}  | {f1_score(y_true, real):.2f}")

    print()
    print("Reading this. By ACCURACY, the two models look close (0.95 vs 0.98), so")
    print("accuracy says the useless always-negative model is nearly as good as the")
    print("real one. But its RECALL is 0.00: it catches none of the 5 positives, and")
    print("its F1 is 0.00. The real model catches 4 of 5 (recall 0.80, F1 0.80).")
    print("Accuracy is dominated by the 95% majority class, so a model can score high")
    print("while being worthless on the minority class, which is usually the class")
    print("you care about (fraud, disease, a rare trading signal). The lesson: on")
    print("imbalanced data, IGNORE accuracy; use precision, recall, F1, the confusion")
    print("matrix, and (for ranking) ROC-AUC or precision-recall-AUC, and choose the")
    print("metric by the cost of each error type. Optimizing the wrong metric ships a")
    print("model that scores well and does nothing useful.")


if __name__ == "__main__":
    main()
