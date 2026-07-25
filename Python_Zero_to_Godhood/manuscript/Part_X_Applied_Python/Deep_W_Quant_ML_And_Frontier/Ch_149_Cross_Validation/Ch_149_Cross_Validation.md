# Chapter 68: Cross-Validation

Chapter 65 gave you the train/test split and immediately flagged a weakness: a *single* split is *noisy*.
The score you get depends on *which* samples happened to land in the test set, so the same model on the same data can score high or low depending only on the random seed.
The measurement makes it concrete: across 10 random seeds, a single split's accuracy swings from **0.875 to 0.975**, a **10-point** spread, so a single split could report almost anywhere in a wide range, and two people who split the same data differently could reach opposite conclusions.

**Cross-validation** fixes this by averaging.
**k-fold** cross-validation splits the data into k equal folds, then trains and evaluates *k times*, each fold held out as the test set once while the other k-1 folds train.
Every sample is thus tested *exactly once* and trained on *k-1 times*, and you average the k scores into a **stable estimate**, with a standard deviation that quantifies its uncertainty (**0.93 ± 0.029** here, tight, versus the single split's 10-point swing).
It also uses the data *efficiently*, every sample contributes to both training and testing, which matters when data is limited.

**This is Deep W's cross-validation chapter.**
It strengthens the evaluation methodology of Chapters 65-67 (held-out data, no leakage, right metric) with *robust estimation*, and it is the basis of model selection (`GridSearchCV`) and the standard way **Book III** reports and compares model performance.

## Section index

- **68.1** k-fold cross-validation
- **68.2** Using CV: robustness, selection, and variants
- **68.3** Measurement: single-split noise versus CV stability
- **68.4** Edges and failure modes
- **68.5** Connections
- **68.6** Exercises
- **68.7** Summary and cross-references

Listings live under `code/ch149/` and are re-executed by `make verify` on both verification interpreters.

---

## 68.1 k-fold cross-validation

```python
# code/ch149/l01_cross_val.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- 5-fold cross-validation: train and evaluate 5 times ---
  the 5 fold scores  : [0.925, 0.9, 0.95, 0.9, 0.975]
  CV mean (estimate) : 0.93
  CV std (uncertainty): 0.029
--- every sample is tested once, trained on k-1 times ---
  number of folds        : 5
  every sample tested once : True   (200 of 200)
--- report an estimate as mean +/- std, not a single number ---
  accuracy estimate : 0.93 +/- 0.03
  (a single split would report just one point in that range)
--- the rule ---
  use k-fold cross-validation for a stable generalization estimate: it
  averages over k splits so no single lucky/unlucky split misleads you
```

**k-fold cross-validation** trains and evaluates k times.
`cross_val_score(model, X, y, cv=5)` splits the data into 5 folds and, for each fold, trains on the other 4 and scores on that fold, giving 5 scores (`[0.925, 0.9, 0.95, 0.9, 0.975]`).
The **mean** (0.93) is the generalization estimate; the **standard deviation** (0.029) is its *uncertainty*, how much the score varies across folds.

**Every sample is used for both training and testing.**
Across the 5 folds, each of the 200 samples is in the test set *exactly once* (the output confirms all 200 are tested) and in the training set for the *other* 4 folds.
So cross-validation uses *all* the data for testing (no sample is wasted in a permanent test set) and *all* the data for training (each fold trains on 80% here), which is why it is more *data-efficient* than a single split, especially valuable when data is scarce.

**Report an estimate as mean ± std, not a single number.**
The proper way to report a model's performance is `0.93 ± 0.03`, the cross-validated mean and its standard deviation, which conveys both the estimate *and* its reliability.
A single split reports just *one point* in that range (and you do not know *where* in the range, because a single split gives no spread).
The ± is not decoration; it tells you whether a difference between two models (say 0.93 vs 0.94) is *real* or *within the noise* (if the stds overlap, the difference may be noise).

So cross-validation transforms evaluation from a single noisy point into a *distribution*: an estimate with a quantified uncertainty, computed by rotating the held-out fold through all the data.

---

## 68.2 Using CV: robustness, selection, and variants

Cross-validation is used in two ways, robust *estimation* and model *selection*, and it comes in variants for different data.

**Robust estimation.** §68.1, §68.3.
Report a model's performance as the cross-validated mean ± std, not a single split. This is the honest, reliable estimate, and it lets you compare models meaningfully (is model A's mean better than model B's by more than their stds?).

**Model selection.**
Choosing among models or *hyperparameters* (a model's settings: the k in KNN, the regularization strength, the tree depth) is done by cross-validation.
**`GridSearchCV`** tries each hyperparameter combination, cross-validates each, and picks the best by CV score, all *without* touching the final test set (Chapter 65: the test set is for the *final* estimate, not tuning).
Crucially, the *pipeline* (Chapter 66) goes *inside* the CV, so preprocessing is fit *per fold* on that fold's training data, leakage-free selection.

**k-fold variants for different data:**

- **Stratified k-fold:** for *classification*, preserves the class proportions in each fold (essential for imbalanced data, Chapter 67, so every fold has some of the rare class). `cross_val_score` uses it automatically for classifiers.
- **Time-series split (`TimeSeriesSplit`):** for *time-ordered* data, trains on the *past* and tests on the *future* (never the reverse), because standard k-fold would train on future data to predict the past, a leakage that invalidates any temporal model. This is *mandatory* for time series (Chapter 61) and quant models.
- **Group k-fold:** keeps *groups* (e.g. all rows from one entity) together, so the model is tested on *unseen groups*, preventing leakage when samples are not independent.
- **Leave-one-out (LOO):** k = n (each sample its own fold), maximally data-efficient but expensive; for very small data.

**Choosing k:** 5 or 10 are standard, more folds means more training (higher cost) but a lower-variance estimate and more training data per fold. 5-fold is the common default.

The rule: **estimate and select models with cross-validation, using the variant that matches your data (stratified for classification, time-series split for temporal data, group for grouped data), and put the pipeline inside the CV.**
The single train/test split has one honest use, the *final* held-out check (Chapter 65) after all selection is done via CV; for *estimation* and *comparison*, cross-validation is the tool.

---

## 68.3 Measurement: single-split noise versus CV stability

**Methodology.** `code/ch149/bench_cv.py`.
A quality measurement. The same model and data evaluated by a single 80/20 split across 10 random seeds (measuring the spread) versus 5-fold cross-validation.
CPython 3.13.5, scikit-learn 1.6.1.

| evaluation | result |
|---|---|
| single split, 10 seeds | min 0.875, max 0.975, **spread 0.100** |
| 5-fold cross-validation | **mean 0.930, std 0.029** |

A single split's score swings by **10 percentage points** (0.875 to 0.975) depending *only* on the random seed, on which samples happened to land in the test set (identical on both interpreters).
5-fold cross-validation gives a *stable* estimate (0.930) with a small standard deviation (0.029).

The implication is direct and important.
**A single split is an unreliable basis for a decision.**
If you evaluate a model with one split, your reported number could be anywhere in a 10-point range, and you would not know where, so you might report 0.975 (lucky split) or 0.875 (unlucky split) for the *same model*.
Worse, if you *compare* two models each with a single (different) split, the "better" one might just have had a luckier split, you would draw a wrong conclusion from noise.
Cross-validation removes this by averaging over folds: the mean is stable, and the std tells you the remaining uncertainty, so a comparison between models is *meaningful* (accounting for the noise) rather than a coin flip.

This completes Deep W's evaluation methodology (Chapters 65-68), and the through-line is one idea: **do not fool yourself about how good a model is.**
Chapter 65 said evaluate on data the model has not seen (not training). Chapter 66 said do not leak test information into training. Chapter 67 said use a metric that reflects what you care about (not accuracy on imbalanced data). This chapter says use *enough* splits that the estimate is stable (not one noisy split).
Each addresses a different way the *evaluation itself* can lie, and together they are the discipline that makes an ML result *trustworthy*.
The most sophisticated algorithm is worthless without this, and the simplest model is trustworthy with it.
**Book III**'s models are estimated and selected with cross-validation, stratified for imbalanced classification, time-respecting for temporal data, pipelines inside, so that a reported performance is a *reliable* estimate, not a lucky split, and a model comparison reflects *real* differences, not noise.
In a domain where a model's number drives a decision to deploy capital, the reliability of that number is the reliability of the decision, which is why cross-validation, not a single split, is the standard.

---

## 68.4 Edges and failure modes

**A single split is noisy; use CV for estimation.** §68.3.
One split can swing 10 points by seed. Report cross-validated mean ± std, not a single-split point.

**Use stratified k-fold for classification.** §68.2.
Preserves class proportions per fold, essential for imbalanced data (Chapter 67). `cross_val_score` does this automatically for classifiers; be explicit if constructing folds manually.

**Use time-series split for temporal data.** §68.2, Chapter 61.
Standard k-fold trains on future data to predict the past, a fatal leakage for time series and quant models. `TimeSeriesSplit` trains on past, tests on future. This is mandatory, not optional, for temporal data.

**Put the pipeline inside the CV.** §68.2, Chapter 66.
Preprocessing must be fit per fold on that fold's training data. Fitting it once outside CV leaks across folds. `cross_val_score(pipeline, ...)` does it correctly.

**Do not tune on the test set; CV is for selection, test for the final check.** Chapter 65.
Select hyperparameters by CV (or a validation set), then evaluate *once* on the held-out test set. Repeatedly checking the test set overfits to it.

**CV cost scales with k.**
k-fold trains k models. For expensive models or large data, this is k times the training cost. Balance k (5-10 typical) against cost; more folds lower variance but cost more.

**Grouped/dependent samples need group CV.** §68.2.
If samples are not independent (multiple rows per entity), standard CV leaks (the model sees an entity in both train and test). Use group k-fold to test on unseen groups.

**Nested CV for unbiased selection + estimation.**
Selecting hyperparameters by CV *and* estimating performance by the same CV is slightly optimistic. Nested CV (an inner CV for selection, an outer for estimation) gives an unbiased estimate, at higher cost, use it when the selection is extensive.

---

## 68.5 Connections

**Backward.**
CV strengthens the held-out evaluation of Chapter 65 (rotating the held-out fold), requires the leakage-free pipelines of Chapter 66 (fit per fold), uses the metrics of Chapter 67 (scored per fold), and, for temporal data, the time-order of Chapter 61. The mean ± std reporting is basic statistics (estimating with uncertainty).

**Forward.**
`GridSearchCV`/`RandomizedSearchCV` (CV-based hyperparameter selection), nested CV, learning curves, and the specific algorithms whose hyperparameters you tune are the rest of **Deep W**. Time-series-aware validation and backtesting (the quant form of CV, where the "folds" are walk-forward windows) are Deep W. Statistical significance of model comparisons builds on the CV distribution.

**Across books.**
Cross-validation is how **Book III** reports and compares model performance reliably: a quant signal model's edge is estimated by time-respecting cross-validation (walk-forward, never peeking at the future), not a single backtest split, because a single split's result could be luck, and deploying capital on a lucky split is a real risk. The order-book system evaluates and selects its models with cross-validation, stratified for imbalanced classification, `TimeSeriesSplit`/walk-forward for temporal signals, pipelines inside, and reports performance as a distribution (mean ± std) so that a model's edge is judged against its *noise*, a difference within the std is not an edge, it is chance. Deep W's evaluation methodology (Chapters 65-68) is complete, and its single principle, do not let the evaluation fool you, is the foundation on which every model's trustworthiness rests.

---

## 68.6 Exercises

**1. Run k-fold.** Reproduce §68.1: 5-fold cross-validate a model, inspect the per-fold scores, mean, and std, and confirm every sample is tested once. Explain how CV rotates the held-out fold.

**2. Measure the noise.** Reproduce §68.3. Confirm a single split swings ~10 points across seeds while CV is stable. Explain why a single split is an unreliable basis for reporting or comparing models.

**3. Stratify and time-split.** Use stratified k-fold on imbalanced data and confirm each fold has the rare class. Then use `TimeSeriesSplit` on temporal data and show it never trains on the future. Explain why each variant is needed.

**4. Select with CV.** Use `GridSearchCV` (with a pipeline inside) to select a hyperparameter, then evaluate once on a held-out test set. Explain why selection uses CV and the final estimate uses the untouched test set.

**5. The design question.** A single split is noisy; CV averages over folds for a stable estimate with quantified uncertainty. Argue why reporting mean ± std (not a single-split point) is essential for trustworthy comparison (§68.3), and how CV completes the evaluation methodology (Chapters 65-68). Why is time-series split mandatory for temporal data?

---

## 68.7 Summary and cross-references

- A **single train/test split is noisy:** the score depends on which samples land in test. **Measured:** across 10 seeds a single split swings **0.875 to 0.975** (a **10-point** spread).
- **k-fold cross-validation** trains and evaluates k times (each fold held out once), so every sample is tested once and trained on k-1 times. It gives a **stable estimate with quantified uncertainty** (measured **0.93 ± 0.029**) and uses data efficiently.
- **Report performance as a cross-validated mean ± std**, not a single-split point; use CV for **model selection** (`GridSearchCV`, pipeline inside, test set untouched).
- **Variants match the data:** **stratified** k-fold for classification (preserves class balance, Chapter 67), **`TimeSeriesSplit`** for temporal data (train on past, test on future, mandatory, Chapter 61), **group** k-fold for dependent samples.
- **This completes the evaluation methodology (Chapters 65-68):** held-out data, no leakage, right metric, **and enough splits for a stable estimate**, each preventing a different way the evaluation can lie.
- **Edges:** stratify for classification; time-split for temporal (else fatal leakage); pipeline inside CV; CV for selection, test set for the final check; cost scales with k; use group CV for dependent samples; nested CV for unbiased selection+estimation.

**Cross-references.** Held-out evaluation → Chapter 65. Leakage-free pipelines (inside CV) → Chapter 66. Metrics (scored per fold) → Chapter 67. Time-order for temporal data → Chapter 61. `GridSearchCV`, nested CV, walk-forward backtesting → the rest of Deep W. Book III reliable model estimation → Deep W / Book III.
