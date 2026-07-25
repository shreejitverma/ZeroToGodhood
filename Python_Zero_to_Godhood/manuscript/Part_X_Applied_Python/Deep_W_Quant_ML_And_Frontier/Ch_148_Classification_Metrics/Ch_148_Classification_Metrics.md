# Chapter 67: Classification Metrics

Chapter 65 taught *that* you must evaluate on held-out data; this chapter teaches *what to measure*, and it turns out the intuitive choice, **accuracy**, is often the wrong one.
Accuracy (the fraction of predictions that are correct) is fine for *balanced* problems, but on **imbalanced** data, where one class is rare, it is dangerously misleading, and imbalanced data is the norm for the problems that matter: fraud (most transactions are legitimate), disease (most patients are healthy), rare trading signals (most bars are noise).

The failure is stark and the measurement makes it undeniable.
On a dataset that is 95% negative, a **useless** model that *always predicts the majority class* scores **95% accuracy**, and catches **none** of the positives (recall 0).
Accuracy ranks this worthless model nearly as high as a real one (98%), because accuracy is dominated by the 95% majority class.
The honest metrics, **precision**, **recall**, and **F1**, computed from the **confusion matrix**, expose the difference: the useless model has recall 0, the real model recall 0.80.
The lesson, and the chapter's rule, is: **on imbalanced data, ignore accuracy; use precision/recall/F1 and choose the metric by the cost of each error.**

**This is Deep W's metrics chapter.**
It completes the evaluation methodology of Chapters 65-66 (evaluate on held-out data, without leakage, *with the right metric*), and is essential to **Book III**, where the classification problems (fraud, signal detection, risk) are overwhelmingly imbalanced.

## Section index

- **67.1** The accuracy trap and the honest metrics
- **67.2** Precision, recall, and the cost of errors
- **67.3** Measurement: accuracy versus recall on imbalanced data
- **67.4** Edges and failure modes
- **67.5** Connections
- **67.6** Exercises
- **67.7** Summary and cross-references

Listings live under `code/ch148/` and are re-executed by `make verify` on both verification interpreters.

---

## 67.1 The accuracy trap and the honest metrics

```python
# code/ch148/l01_metrics.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the trap: a useless always-negative model looks accurate ---
  always-negative accuracy : 0.95   (looks great!)
  but recall of positives  : 0.0   (catches NONE)
  -> 95% accuracy, 0% useful: accuracy hid a worthless model
--- the honest metrics from the confusion matrix ---
  confusion matrix [[TN, FP], [FN, TP]] : [[94, 1], [1, 4]]
  accuracy  : 0.98
  precision : 0.8   (of predicted +, how many right)
  recall    : 0.8   (of actual +, how many caught)
  F1        : 0.8   (balance of precision and recall)
--- precision vs recall is a TRADE-OFF you choose by the cost of errors ---
  fraud/disease: maximize RECALL (missing a positive is costly)
  spam filter  : maximize PRECISION (a false positive is costly)
--- the rule ---
  never judge a classifier by accuracy on imbalanced data; use precision,
  recall, F1 (and the confusion matrix), and choose by the cost of errors
```

**The accuracy trap.**
The data is 95% negative, so a model that *always predicts negative* is right 95% of the time, **95% accuracy**, which *sounds* excellent.
But it catches **zero** of the 5 positives (**recall 0**), so it is completely useless for the task (finding the positives).
Accuracy hid a worthless model, because accuracy counts the easy majority-class correctness that swamps the hard, important minority class.

**The confusion matrix** is the honest foundation.
It counts the four outcomes: **TN** (true negatives, correctly predicted negative), **FP** (false positives, predicted positive but actually negative), **FN** (false negatives, predicted negative but actually positive), **TP** (true positives, correctly predicted positive), here `[[94, 1], [1, 4]]` (94 TN, 1 FP, 1 FN, 4 TP).
Every classification metric derives from these four numbers.

**The honest metrics:**

- **Precision** = `TP / (TP + FP)` = "of the examples I *predicted* positive, how many *are* positive". Here `4 / (4 + 1) = 0.8`. High precision means few false alarms.
- **Recall** (sensitivity) = `TP / (TP + FN)` = "of the *actual* positives, how many did I *catch*". Here `4 / (4 + 1) = 0.8`. High recall means few misses.
- **F1** = the *harmonic* mean of precision and recall = one balanced number (0.8 here). The harmonic mean punishes imbalance: F1 is high only when *both* precision and recall are high (the always-negative model has F1 0, because recall is 0).

These metrics *cannot* be fooled by imbalance the way accuracy is, because they focus on the *positive* class (the rare, important one), so a model that ignores positives scores 0 on recall and F1 regardless of how many negatives it gets right.

---

## 67.2 Precision, recall, and the cost of errors

Precision and recall are in **tension**, and choosing between them is a *domain* decision, driven by the *cost of each error type*.

**The precision-recall trade-off.**
A classifier outputs a *score*, and you set a *threshold* to decide positive versus negative.
Lower the threshold (predict positive more readily): you catch more actual positives (higher **recall**) but also raise more false alarms (lower **precision**).
Raise the threshold (predict positive cautiously): fewer false alarms (higher **precision**) but you miss more positives (lower **recall**).
You cannot maximize both; you *trade* them, by moving the threshold, according to which error is more costly.

**Choose the metric by the cost of errors:**

- **Maximize recall when a *miss* (false negative) is costly.** Fraud detection (missing a fraud costs money), disease screening (missing a case is dangerous), a critical trading signal (missing an opportunity). You accept more false alarms (lower precision) to catch nearly all positives.
- **Maximize precision when a *false alarm* (false positive) is costly.** A spam filter (a false positive hides a real email), an automated action with a cost (a false trade), a high-stakes alert (crying wolf erodes trust). You accept missing some positives (lower recall) to be sure the positives you flag are real.
- **Use F1 when you want a balance** of both, and there is no strong asymmetry.
- **Use ROC-AUC or precision-recall-AUC** to evaluate a model *across all thresholds* (ranking quality), independent of a specific threshold, useful for comparing models and for imbalanced data (PR-AUC especially).

The broader metrics landscape:

- **Confusion matrix:** the full breakdown, always inspect it.
- **Classification report** (`classification_report`): precision/recall/F1 per class.
- **ROC-AUC:** area under the true-positive-rate versus false-positive-rate curve, threshold-independent ranking quality (but can be optimistic on heavy imbalance).
- **Precision-Recall AUC:** better than ROC-AUC for rare positives.
- **Class weighting / resampling:** for training on imbalanced data, weight the minority class or resample, but *evaluate* with the honest metrics regardless.

The rule: **there is no single right metric; choose it by the problem's error costs, and never default to accuracy on imbalanced data.**
The metric you optimize *defines* what "good" means for your model, so choosing it wrong (accuracy on imbalanced data) produces a model that is "good" by a meaningless standard, high accuracy, no useful predictions.

---

## 67.3 Measurement: accuracy versus recall on imbalanced data

**Methodology.** `code/ch148/bench_metrics.py`.
A quality measurement. On 95%-negative data, an always-predict-negative model versus a real model (catching 4 of 5 positives), compared by accuracy, recall, and F1.
CPython 3.13.5, scikit-learn 1.6.1.

| model | accuracy | recall | F1 |
|---|---|---|---|
| always-negative (useless) | 0.95 | **0.00** | **0.00** |
| real (catches 4 of 5) | 0.98 | 0.80 | 0.80 |

By **accuracy**, the two models look close, **0.95** versus **0.98**, so accuracy declares the useless model *nearly as good* as the real one.
By **recall** and **F1**, they are worlds apart: the always-negative model scores **0.00** (it catches none of the 5 positives), the real model **0.80**.

This is the accuracy trap quantified (identical on both interpreters).
Accuracy is a *weighted average* over classes, dominated by whichever class is larger, so on 95%-negative data, getting the 95% negatives right *already* yields 95% accuracy, and the 5% positives, the ones you built the model to find, barely move the number.
A model can therefore score high accuracy while being *completely useless* on the minority class.

The consequences are severe and specific.
**If you select or tune a model by accuracy on imbalanced data, you will pick the wrong model**, potentially one that ignores the positive class entirely, and it will score well in evaluation and *do nothing useful* in production (catch no fraud, detect no disease, find no signal).
This is a close cousin of the overfitting trap (Chapter 65): both are cases where the *wrong metric* makes a bad model look good, and both silently invalidate the result.
The defense completes the evaluation methodology: **evaluate on held-out data (Chapter 65), without leakage (Chapter 66), with the *right metric* (this chapter)**, all three, or the evaluation lies.

The metric choice is not a detail; it is a *definition* of the goal.
**Book III**'s classification problems are almost all imbalanced, fraud, anomalies, rare signals, risk events, and they are evaluated with precision/recall/F1/AUC chosen by error cost, never accuracy.
The order-book system's signal and risk classifiers are judged by recall (catch the rare event) or precision (avoid the costly false action) as the domain demands, with the confusion matrix always inspected, because a classifier optimized for accuracy on 99%-negative market data would be a model that predicts "nothing happens" and is right 99% of the time while being worthless, the §67.3 trap, avoided by choosing the metric that matches what the model is *for*. Deep W's evaluation methodology, held-out, leakage-free, right-metric, is the foundation that makes every algorithm's results *mean* something.

---

## 67.4 Edges and failure modes

**Never use accuracy on imbalanced data.** §67.1, §67.3.
It is dominated by the majority class; a useless model scores high. Use precision/recall/F1/AUC.

**Choose the metric by error cost.** §67.2.
Recall when misses are costly (fraud, disease); precision when false alarms are costly (spam, costly actions); F1 for balance. The metric defines the goal.

**Precision and recall trade off via the threshold.** §67.2.
You cannot maximize both. Set the threshold (or optimize the chosen metric) by the cost of each error, not by default.

**ROC-AUC can be optimistic on heavy imbalance.**
On very rare positives, ROC-AUC looks good even for weak models; precision-recall AUC is more informative. Prefer PR-AUC for rare-positive problems.

**Class imbalance in *training* is separate from in *evaluation*.**
Resampling or class-weighting helps a model *learn* from imbalanced data, but you still *evaluate* with the honest metrics on the *original* distribution. Do not evaluate on resampled data.

**Multi-class needs averaging choices.**
For more than two classes, precision/recall/F1 are per-class; combining them needs an averaging strategy (`macro` treats classes equally, `weighted` by frequency, `micro` pools). The choice matters for imbalanced multi-class; pick deliberately.

**The confusion matrix is the ground truth; always look at it.**
Summary metrics compress the four counts; the confusion matrix shows *which* errors the model makes (all false negatives? all false positives?), which is often more actionable than any single number.

**Metrics on the wrong data mislead.**
Compute metrics on the *test* set (Chapter 65), not training. A great training F1 is as meaningless as a great training accuracy.

---

## 67.5 Connections

**Backward.**
This completes the evaluation methodology of Chapters 65 (held-out data) and 66 (no leakage). The confusion-matrix counts are the raw material; F1's harmonic mean is the mean that punishes imbalance (contrast the arithmetic mean). The metric-defines-the-goal idea is the book's "measure the right thing" stance.

**Forward.**
ROC/PR curves, threshold tuning, `classification_report`, multi-class averaging, class weighting/resampling for imbalanced training, and probability calibration are the rest of **Deep W**. Regression metrics (beyond R^2: MAE, RMSE, and their trade-offs) parallel this. Cost-sensitive learning formalizes the error-cost choice.

**Across books.**
Choosing the right classification metric is a domain-and-correctness requirement in **Book III**: its classification problems (fraud, anomaly, signal, risk) are imbalanced, and evaluating them by accuracy would systematically favor do-nothing models. The order-book system evaluates each classifier by the metric its use demands, recall for catching rare adverse events, precision for triggering costly automated actions, and always inspects the confusion matrix, so a model is judged by whether it does the *job*, not by an accuracy inflated by the easy majority class. In a domain where a missed fraud or a false trade is a real loss, the metric *is* the specification, and choosing it correctly is as important as the model. Deep W's methodology (Chapters 65-67) is complete: evaluate held-out, leakage-free, with the metric that matches the cost of being wrong.

---

## 67.6 Exercises

**1. Spring the trap.** Reproduce §67.1: on imbalanced data, show an always-majority model's high accuracy and zero recall. Inspect the confusion matrix. Explain why accuracy hid the worthless model.

**2. The honest metrics.** Compute precision, recall, and F1 from a confusion matrix by hand and verify against sklearn. Explain what each answers and why F1 (harmonic mean) is 0 when either is 0.

**3. Choose by cost.** For fraud detection and for a spam filter, decide whether to prioritize precision or recall, and adjust a threshold to trade them. Justify each choice by the error cost.

**4. Measure the trap.** Reproduce §67.3. Confirm accuracy ranks the useless and real models close while recall/F1 separate them. Explain why accuracy is a majority-dominated average.

**5. The design question.** The metric you optimize defines what "good" means for a model. Argue why accuracy is the wrong default for imbalanced data (§67.3), how to choose the right metric by error cost (§67.2), and how this completes the evaluation methodology (with Chapters 65-66). What goes wrong if you select a model by the wrong metric?

---

## 67.7 Summary and cross-references

- **Accuracy is misleading on imbalanced data.** A useless always-majority model scores high accuracy (95% on 95%-negative data) while catching **no** positives. Accuracy is dominated by the majority class.
- **Honest metrics come from the confusion matrix** (TN/FP/FN/TP): **precision** = `TP/(TP+FP)` (of predicted positives, how many right), **recall** = `TP/(TP+FN)` (of actual positives, how many caught), **F1** = their harmonic mean (0 if either is 0).
- **Precision and recall trade off** via the threshold; **choose the metric by the cost of errors**: recall when misses are costly (fraud, disease), precision when false alarms are costly (spam, costly actions), F1 for balance, ROC/PR-AUC for threshold-independent ranking.
- **Measured:** on 95%-negative data, an always-negative model scores **0.95 accuracy but 0.00 recall/F1**; a real model **0.98 / 0.80 / 0.80**. Accuracy ranks them close; recall/F1 expose the difference.
- **This completes the evaluation methodology:** held-out data (Chapter 65), no leakage (Chapter 66), **and the right metric** (this chapter). Selecting a model by the wrong metric silently invalidates the result.
- **Edges:** ROC-AUC can be optimistic on heavy imbalance (use PR-AUC); training imbalance handling (resampling/weighting) is separate from evaluation; multi-class needs an averaging choice; always inspect the confusion matrix; compute metrics on test data.

**Cross-references.** Held-out evaluation → Chapter 65. Leakage-free preprocessing → Chapter 66. Harmonic vs arithmetic mean → Deep Q/statistics. ROC/PR curves, thresholds, imbalanced training, calibration, regression metrics → the rest of Deep W. Book III classifier evaluation → Deep W / Book III.
