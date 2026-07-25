# Chapter 65: The Machine Learning Workflow

Deep U ended at the seam where data engineering feeds a model.
This chapter opens **Deep W**, the volume on machine learning, quantitative finance, and frontier domains, the far end of the applied arc, where the numeric foundations (Deep T) and data engineering (Deep U) become predictive systems.
It starts with the two things every ML practitioner must internalize before any algorithm: the **estimator API** (`fit`/`predict`/`score`, the one interface every scikit-learn model shares) and the **train/test split** (the discipline of evaluating on data the model has never seen).

The estimator API is the ergonomic foundation: every model, linear regression, random forest, gradient boosting, a neural network wrapper, exposes the *same* `fit(X, y)` / `predict(X)` / `score(X, y)` interface, so you swap algorithms by changing one line and the surrounding pipeline is unchanged.
The train/test split is the *correctness* foundation, and it is the single most important discipline in ML, because of the failure the measurement demonstrates: a model can **memorize** its training data and score *perfectly* on it while generalizing *poorly*.
A k=1 nearest-neighbor model scores a perfect **1.0** on training data and only **0.84** on held-out test data; a k=5 model scores *lower* on training (0.94) but *higher* on test (0.89).
The training score is a misleading, optimistic estimate, and judging a model by it is the cardinal ML mistake.

**This opens Deep W, the ML and quant volume.**
It builds on the DataFrame/feature matrix (Deep U), NumPy (Deep T, the arrays models consume), and is the entry to the predictive systems of **Book III**.
(Verified against scikit-learn 1.6.1 on 3.13 and 1.9.0 on 3.14; the listing uses deterministic data and fixed `random_state`, and rounds, since some numerics vary across versions.)

## Section index

- **65.1** The estimator API and the train/test split
- **65.2** Overfitting, generalization, and evaluation discipline
- **65.3** Measurement: training score versus test score
- **65.4** Edges and failure modes
- **65.5** Connections
- **65.6** Exercises
- **65.7** Summary and cross-references

Listings live under `code/ch146/` and are re-executed by `make verify` on both verification interpreters.

---

## 65.1 The estimator API and the train/test split

```python
# code/ch146/l01_ml_workflow.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the estimator API: fit, predict, score ---
  learned slope     : 2.0   (true: 2)
  learned intercept : 1.0   (true: 1)
  predict(x=100)    : 201.0   (2*100+1)
  score (R^2)       : 1.0   (1.0 = perfect fit)
--- train/test split: reproducible with a fixed random_state ---
  train size : 15   test size : 5
  test samples (sorted x) : [0.0, 1.0, 8.0, 15.0, 17.0]
--- same random_state -> same split (reproducible experiments) ---
  identical split on re-run : True
--- one API, any model: fit on train, score on TEST ---
  test R^2 (evaluate on held-out data) : 1.0
--- the rule ---
  fit/predict/score is the universal estimator API; ALWAYS evaluate on a
  held-out test set (fixed random_state for reproducibility), never on train
```

**The estimator API** is scikit-learn's unifying interface, and it is the same for every model:

- **`fit(X, y)`** *learns* from training data. `X` is the **feature matrix** (a 2D array, samples x features, the wide format of Chapter 63); `y` is the **target** (what to predict). `LinearRegression().fit(X, y)` learns the relationship, and on the exact data `y = 2x + 1` it recovers slope `2.0` and intercept `1.0`.
- **`predict(X)`** *applies* the learned model to new features. `predict(x=100)` gives `201.0` (`2*100 + 1`).
- **`score(X, y)`** *evaluates* (here R^2 for regression, 1.0 is perfect; accuracy for classification).

Because *every* estimator, from `LinearRegression` to `RandomForestClassifier` to a neural network, exposes this identical interface, the ML *workflow* is model-independent: you build features, split data, `fit`, `predict`, `score`, and *swap the model* by changing the one line that constructs it. This uniformity is why scikit-learn pipelines and model-selection tools work across all algorithms.

**The train/test split** is the evaluation discipline.
`train_test_split(X, y, test_size=0.25, random_state=42)` randomly partitions the data into a training set (to `fit`) and a held-out test set (to `score`), here 15 train, 5 test.
The **`random_state`** makes the split *reproducible*: the same seed gives the *identical* split on every run (the test samples are the same `[0, 1, 8, 15, 17]`, confirmed identical on re-run), which is essential for reproducible experiments, you and a colleague running the same code get the same split, the same result.
The workflow is then: `fit` on the *training* set, `score` on the *test* set, so the reported performance reflects how the model does on data it did *not* learn from.

---

## 65.2 Overfitting, generalization, and evaluation discipline

The train/test split exists because of **overfitting**, the defining hazard of machine learning, and understanding it is more important than any algorithm.

**A model can memorize instead of learn.**
The *goal* of ML is **generalization**: performing well on *new*, unseen data. The *risk* is that a model, especially a flexible one, fits the *training* data's idiosyncrasies (its noise, its specific points) rather than the underlying pattern, so it does great on training data and poorly on new data. This is **overfitting**.
The extreme case is *memorization*: a k=1 nearest-neighbor model predicts each training point as *itself*, so its training score is a *perfect* 1.0, it has memorized every training example. But it has learned nothing generalizable, so on new data it does worse (§65.3).

**The training score is optimistically biased.**
A model *always* does at least as well on its training data as on new data (it was optimized for exactly that data). So the training score *overestimates* true performance, sometimes wildly. Judging a model by its training score is measuring memorization, not learning, and it is the single most common and most dangerous ML mistake.

**The evaluation discipline:**

- **Always evaluate on held-out test data.** §65.1, §65.3. `fit` on train, `score` on test. The test score estimates generalization.
- **Cross-validation** for robust estimates. A single train/test split is noisy (the estimate depends on which points landed in test). **k-fold cross-validation** splits the data k ways, trains and evaluates k times (each fold held out once), and averages, a far more reliable generalization estimate. Use it, especially with limited data.
- **Never touch the test set during development.** The test set is a *final* estimate. If you tune your model against the test score (trying many models, keeping the best test score), you have *leaked* the test set into training and overfit to it. Use a separate *validation* set (or cross-validation) for tuning, and the test set *once*, at the end.
- **A perfect (or suspiciously high) training score is a warning, not a success.** It usually means memorization/overfitting. Real generalization shows as a *good test score*, with the train and test scores *close*.

**Controlling overfitting** is the other side: simpler models (fewer parameters, k=5 not k=1), regularization (penalizing complexity), more data, and cross-validated model selection all trade a little training fit for better generalization.
The k=5 model (§65.3) exemplifies it: it *cannot* memorize (lower train score) and therefore generalizes better (higher test score).

The rule: **machine learning measures generalization, not fit.** Evaluate on held-out data, use cross-validation, keep the test set pristine, and treat a high training score as a red flag. This discipline is more foundational than any algorithm, a wrong evaluation makes even a good model useless (you cannot tell if it works), and a right evaluation makes model choice tractable.

---

## 65.3 Measurement: training score versus test score

**Methodology.** `code/ch146/bench_overfit.py`.
A quality measurement, not timing. A noisy dataset (`y = sin(x) + noise`), split 70/30, fit with a k=1 nearest-neighbor regressor (memorizes) and a k=5 regressor (generalizes), comparing training R^2 and test R^2.
CPython 3.13.5, scikit-learn 1.6.1.

| model | train R^2 | test R^2 |
|---|---|---|
| k=1 (memorizes) | **1.0000** | 0.8391 |
| k=5 (generalizes) | 0.9407 | **0.8913** |

The result is the overfitting lesson in four numbers (identical on both interpreters).
The **k=1** model scores a **perfect 1.0** on training data, it predicts each training point as itself, memorizing, but only **0.84** on held-out test data.
The **k=5** model scores *lower* on training (**0.94**, it *cannot* memorize, each prediction averages 5 neighbors) yet *higher* on test (**0.89**), it *generalizes* better.

Two conclusions, both foundational.

**The training score is misleading.**
k=1's perfect training score (1.0) is *worse* news than k=5's imperfect one (0.94), because k=1's perfection is *memorization* that does not transfer (test 0.84 < 0.89). If you had chosen the model by training score, you would have picked the *worse* model. The training score does not measure what you care about (generalization); the test score does.

**Simpler can generalize better.**
k=5 is a *simpler* model (more smoothing, less flexibility) and it *wins* on the metric that matters (test score). This is the bias-variance trade-off in miniature: too flexible (k=1) overfits (memorizes noise), too simple underfits (misses the pattern), and the right complexity (k=5 here) generalizes best. Model selection is the search for that right complexity, guided by *test/validation* scores, not training scores.

This is Deep W's opening lesson, and it precedes all algorithms because it is what makes them *usable*.
The most sophisticated model is worthless if you evaluate it wrong (by training score), and the simplest model is trustworthy if you evaluate it right (held-out test, cross-validation).
So before *any* modeling, the discipline: split the data, fit on train, evaluate on test, cross-validate for robustness, keep the test set pristine, and never trust a training score.
This is the correctness foundation of ML, the counterpart to Deep U's "vectorize" and Deep M's "amortize the boundary", a single discipline that, gotten right, makes everything downstream sound, and gotten wrong, silently invalidates it.
**Book III**'s predictive systems, quant models, classifiers, forecasters, all rest on this evaluation discipline, because in a domain where a model's prediction drives a decision (a trade, a risk limit), knowing whether it *actually generalizes* is not academic, it is the difference between a model that makes money and one that memorized the past and fails on the future.

---

## 65.4 Edges and failure modes

**Never judge a model by its training score.** §65.2, §65.3.
It overestimates performance (memorization). Always evaluate on held-out test data.

**A perfect training score signals overfitting.** §65.3.
It usually means the model memorized rather than learned. Good generalization shows as a good *test* score with train and test *close*.

**Do not tune against the test set (leakage).** §65.2.
Selecting the model with the best *test* score leaks the test set into training. Use a validation set or cross-validation for tuning; touch the test set once, at the end.

**A single split is noisy.** §65.2.
The test score depends on which points landed in test. Use k-fold cross-validation for a robust estimate, especially with limited data.

**Data leakage is subtler than the test set.**
Fitting a preprocessing step (scaling, imputation) on the *whole* dataset before splitting leaks test information into training. Fit preprocessing on *train only* (use a `Pipeline` so the split is respected). Time-series leakage (using future data to predict the past) is especially insidious.

**`random_state` for reproducibility, but do not over-rely on one seed.** §65.1.
Fix `random_state` for reproducible experiments, but a result that only holds for one seed is fragile; cross-validation averages over splits.

**Class imbalance breaks accuracy.**
For classification, `score` (accuracy) is misleading on imbalanced data (99% of one class -> 99% accuracy by always predicting it). Use precision/recall/F1/AUC for imbalanced problems.

**The feature matrix shape and dtype matter.**
`X` must be 2D (samples x features); a 1D array needs reshaping. NaNs (Chapter 62) must be handled before most models. Categorical features need encoding. Garbage features in produce garbage predictions out.

---

## 65.5 Connections

**Backward.**
The feature matrix `X` is the wide DataFrame/2D array of Chapters 63, 57, and Deep T. Reproducible `random_state` builds on deterministic PRNGs. Handling NaNs before modeling is Chapter 62. The evaluation discipline is the book's "measure the right thing, do not fool yourself" stance applied to prediction.

**Forward.**
Cross-validation, pipelines (preprocessing + model as one estimator, respecting the split), model selection (`GridSearchCV`), specific algorithms (trees, ensembles, linear models, neural nets), metrics beyond R^2/accuracy, and feature engineering are the rest of **Deep W**. Quant-specific modeling (time-series-aware validation, backtesting) is Deep W. Deep learning frameworks (PyTorch) are frontier Deep W.

**Across books.**
The ML workflow and evaluation discipline are the foundation of **Book III**'s predictive systems: a quant model, a classifier, a forecaster is only as trustworthy as its evaluation, and the train/test/cross-validation discipline (with time-aware splits and no leakage) is what separates a model that generalizes from one that memorized history. The order-book system's predictive components (signal models, risk classifiers) are evaluated with strict held-out, time-respecting validation, never by training score, and treat data leakage as a first-order bug, because a model chosen by the wrong metric is worse than no model, it gives false confidence to a real decision. Deep W begins here, at the discipline that makes every algorithm that follows sound.

---

## 65.6 Exercises

**1. The estimator API.** Reproduce §65.1: fit a `LinearRegression` on exact data and confirm it recovers the parameters, predicts, and scores 1.0. Then swap in a different regressor (changing one line) and confirm the same API works. Explain the uniform interface.

**2. Reproducible splits.** Use `train_test_split` with a fixed `random_state` and confirm the split is identical on re-run; change the seed and show it differs. Explain why reproducibility matters for experiments.

**3. Watch overfitting.** Reproduce §65.3: fit k=1 and k=5 nearest-neighbor regressors and compare train and test scores. Confirm k=1's perfect train score and worse test score. Explain why simpler k=5 generalizes better.

**4. Leakage.** Fit a scaler on the whole dataset before splitting (leakage) versus on the training set only (correct, via a `Pipeline`), and show the difference in the honest test estimate. Explain why preprocessing must respect the split.

**5. The design question.** ML measures generalization, not fit, and the train/test discipline exists to prevent judging a model by memorization. Argue why this discipline precedes all algorithms, using §65.3, and why a high training score is a warning. How does cross-validation improve on a single split, and why keep the test set pristine?

---

## 65.7 Summary and cross-references

- scikit-learn's **estimator API** is uniform across every model: **`fit(X, y)`** (learn), **`predict(X)`** (apply), **`score(X, y)`** (evaluate). `X` is the feature matrix (samples x features), `y` the target. Swap models by changing one line.
- **The train/test split** (`train_test_split`, reproducible with `random_state`) is the evaluation discipline: **`fit` on train, `score` on held-out test**. The test score estimates **generalization**.
- **Overfitting** is the defining hazard: a model can **memorize** training data (perfect training score) while generalizing poorly. **Measured:** a k=1 (memorizing) model scores **1.0** on train but **0.84** on test; a k=5 (generalizing) model scores **0.94** on train but **0.89** on test, simpler generalizes better, and training score is misleading.
- **The rule: ML measures generalization, not fit.** Always evaluate on held-out test data, use **cross-validation** for robustness, keep the test set **pristine** (no tuning against it), and treat a high training score as a **red flag**.
- **Edges:** avoid data leakage (fit preprocessing on train only, via `Pipeline`; beware time-series leakage); a single split is noisy (cross-validate); accuracy misleads on imbalanced classes (use precision/recall/F1/AUC); handle NaNs and encode categoricals first.

**Cross-references.** Feature matrix / wide format → Chapters 63, 57. NumPy arrays → Deep T. Handling missing data → Chapter 62. Cross-validation, pipelines, model selection, algorithms, metrics, quant modeling, deep learning → the rest of Deep W. Book III predictive systems → Deep W / Book III.
