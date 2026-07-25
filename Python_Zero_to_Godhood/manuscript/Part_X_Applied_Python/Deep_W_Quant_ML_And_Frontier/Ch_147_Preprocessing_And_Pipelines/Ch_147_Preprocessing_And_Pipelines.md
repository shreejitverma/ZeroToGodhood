# Chapter 66: Preprocessing and Pipelines

Chapter 65 established the ML workflow and its cardinal rule, evaluate on held-out data, and named a hazard it deferred: **data leakage**, where information from the test set sneaks into training and inflates the estimate.
This chapter addresses leakage head-on, through the two tools that make preprocessing correct: **feature scaling** (putting features on comparable scales, which many models require) and the **`Pipeline`** (chaining preprocessing and the model into one estimator that automatically respects the train/test boundary).

Raw features are rarely model-ready.
A dataset might have one feature in dollars (thousands) and another as a ratio (0 to 1), and a distance- or gradient-based model, KNN, SVM, k-means, anything measuring feature magnitude, will let the large-scale feature *dominate* and effectively ignore the rest.
The measurement shows it: a KNN classifier on features with a 1000x scale mismatch scores **0.78**, and **0.84** after scaling.
And the way you scale matters as much as that you scale: the scaler must be fit on **training data only**, or you leak test information, which is exactly what a `Pipeline` enforces.

**This is Deep W's preprocessing chapter.**
It makes concrete the leakage warning of Chapter 65, builds on the feature matrix (Deep U), and is essential infrastructure for every model in **Book III**.

## Section index

- **66.1** Scaling, and the Pipeline
- **66.2** Preprocessing correctly: leakage and what to scale
- **66.3** Measurement: scaling a scale-sensitive model
- **66.4** Edges and failure modes
- **66.5** Connections
- **66.6** Exercises
- **66.7** Summary and cross-references

Listings live under `code/ch147/` and are re-executed by `make verify` on both verification interpreters.

---

## 66.1 Scaling, and the Pipeline

```python
# code/ch147/l01_pipeline.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- StandardScaler: each feature to mean 0, std 1 ---
  original feature-1 range : 1000.0 .. 4000.0
  scaled means (per feature, ~0)   : [0.0, 0.0]
  scaled stds  (per feature, ~1)   : [1.0, 1.0]
  both features now comparable scale : True
--- a Pipeline chains preprocessing + model as ONE estimator ---
  pipeline steps : ['standardscaler', 'logisticregression']
--- fitting the pipeline fits every step; predict runs the whole chain ---
  pipeline predicts : [0, 0, 1, 1]
  it scaled then classified in one call : True
--- why a pipeline: it fits preprocessing on TRAIN only (no leakage) ---
  a pipeline fit on the training split scales using TRAIN statistics,
  then applies them to test, test data never influences the scaler
--- the rule ---
  scale features for scale-sensitive models; wrap preprocessing + model in
  a Pipeline so fitting respects the train/test split (no data leakage)
```

**`StandardScaler`** standardizes each feature to **mean 0, standard deviation 1**.
The features (`feature-1` ranges 1000 to 4000, `feature-0` is 1 to 4) become comparable: after scaling, each has mean ~0 and std ~1, so no feature dominates by magnitude.
This matters because many models measure feature magnitude directly: a KNN computes *distances* (a 1000x-larger feature dominates the distance), an SVM and gradient descent are sensitive to scale, k-means clusters by distance. Standardizing puts all features on equal footing so each contributes according to its *information*, not its *units*.
(Other scalers exist: `MinMaxScaler` to [0, 1], `RobustScaler` for outlier-resistant scaling; `StandardScaler` is the common default.)

**A `Pipeline`** chains preprocessing steps and a final model into a *single estimator*.
`make_pipeline(StandardScaler(), LogisticRegression())` is one object with `fit`/`predict`/`score` (the estimator API, Chapter 65), whose `fit` runs *each step in order* (scaler `fit`+`transform`, then model `fit` on the scaled data), and whose `predict` runs the *whole chain* (scale, then classify) in one call.
So the pipeline *is* a model that includes its preprocessing, you treat it exactly like any estimator.

**The critical benefit is leakage prevention.**
When you fit a pipeline on the *training* split, it fits the scaler on the *training data's* statistics (mean, std), and then, at test time, *applies those training statistics* to the test data.
The test data *never influences* the scaler.
This is the correct way to preprocess, and it is easy to get wrong *without* a pipeline (fit the scaler on all the data before splitting, and the test set's mean/std leak into the training scaling, an optimistically biased estimate, §66.2).
The pipeline makes the correct behaviour *automatic*: preprocessing becomes part of the model, and the model respects the train/test boundary by construction.

---

## 66.2 Preprocessing correctly: leakage and what to scale

Preprocessing is where leakage most often creeps in, and where the pipeline earns its place.

**Data leakage: the subtle, invalidating bug.**
Leakage is when information the model should not have at prediction time influences training, and it silently *inflates* your evaluation, so a leaky model looks great in testing and fails in production.
The classic preprocessing leakage:

- **Scaling/imputing on the whole dataset before splitting.** If you `StandardScaler().fit(X)` on *all* the data and *then* split, the scaler's mean/std were computed using the *test* rows, so test information leaked into the training scaling. Fit the scaler on the *training split only*.
- **Feature selection or target encoding on the whole dataset.** Choosing features by their correlation with the target *using all the data*, or encoding a categorical by its target mean *over all rows*, leaks the target into features. Do it within the training fold.
- **Any statistic computed over data the model would not have at prediction time.**

The fix, and the discipline, is: **fit every preprocessing step on training data only, and a `Pipeline` enforces this automatically.**
When the pipeline is inside cross-validation (Chapter 65), *each fold* fits the preprocessing on *that fold's* training data, correct leakage-free evaluation, for free. Preprocessing outside a pipeline is where careful people still leak.

**What to scale (and what not to):**

- **Scale for scale-sensitive models:** KNN, SVM, k-means, PCA, neural networks, logistic/linear regression with regularization, anything using distances, dot products, or gradient descent. §66.3.
- **Do not need to scale for tree models:** decision trees, random forests, gradient-boosted trees split on *thresholds per feature*, so they are invariant to monotonic feature scaling. Scaling does not hurt but does not help.

**Other preprocessing steps** (all belonging in the pipeline, all fit on train only):

- **Imputation** (filling missing values, Chapter 62): `SimpleImputer`, fit the fill statistic (mean/median) on train.
- **Encoding categoricals:** `OneHotEncoder`, `OrdinalEncoder` (the get-dummies of Chapter 63, for models needing numeric input).
- **Feature engineering:** `PolynomialFeatures`, custom transformers.

The rule: **preprocess with a `Pipeline` (or `ColumnTransformer` for per-column steps), which makes preprocessing part of the model and fits it on training data only, preventing leakage.**
Scale for scale-sensitive models; skip it for trees.
This is not fussiness: leakage is the most common way an ML result is *silently wrong* (a great test score that does not hold up), and the pipeline is the tool that makes the correct, leakage-free preprocessing the *default* rather than a thing you must remember.

---

## 66.3 Measurement: scaling a scale-sensitive model

**Methodology.** `code/ch147/bench_scaling.py`.
A quality measurement. A KNN classifier on 2-feature data where the second feature is scaled up 1000x, fit unscaled versus scaled (via a leakage-free `Pipeline`), comparing held-out test accuracy.
CPython 3.13.5, scikit-learn 1.6.1.

| KNN, features on a 1000x scale mismatch | test accuracy |
|---|---|
| unscaled | 0.783 |
| scaled (`StandardScaler` in a Pipeline) | **0.842** |

Scaling improves accuracy from **0.78** to **0.84** (identical on both interpreters).
The reason is KNN's mechanism: it classifies a point by the labels of its *nearest neighbors* in feature space, using **distance**.
When one feature is 1000x larger, it *dominates* the distance, the small feature contributes almost nothing, so the model is effectively *one-dimensional*, ignoring the information in the small feature.
`StandardScaler` rescales both to mean 0, std 1, so both contribute comparably to the distance, and the model uses *all* the information.

The measurement teaches two things.

**Scale-sensitive models require scaling.**
KNN, SVM, k-means, and gradient-based models measure feature magnitude, so unscaled features on different scales degrade them (sometimes severely, more than the modest 0.06 here for a starker mismatch). Scaling is not optional for these; it is part of making them work. Tree models, which split per-feature, do not need it.

**The pipeline makes it correct.**
The scaling here is inside a `Pipeline`, so the scaler was fit on the *training* split and applied to test, the honest, leakage-free way (§66.2). Had the scaler been fit on all the data, the test accuracy would be optimistically biased, a *higher* number that does not reflect real performance. The pipeline gives the correct number *and* bundles preprocessing into the model.

This is Deep W's second foundational lesson (after Chapter 65's evaluation discipline): **preprocessing is part of the model, and it must respect the train/test boundary.**
Together, the two chapters establish the *methodology* that precedes all algorithms: split the data, preprocess within a pipeline (on train only), fit, and evaluate on held-out test with cross-validation, no leakage, honest estimates, real generalization.
**Book III**'s models are built exactly this way, features scaled and preprocessed inside pipelines, fit and evaluated with strict train/test discipline, because a model whose preprocessing leaked, or whose features are unscaled for a scale-sensitive algorithm, is a model that either fails silently or fails to work, and in a domain where predictions drive decisions, the methodology *is* the model's trustworthiness.

---

## 66.4 Edges and failure modes

**Fit preprocessing on training data only; use a `Pipeline`.** §66.1, §66.2.
Fitting a scaler/imputer on the whole dataset before splitting leaks test information. A `Pipeline` fits every step on the training fold automatically.

**Scale-sensitive models need scaling; trees do not.** §66.2, §66.3.
KNN/SVM/k-means/gradient-based models require it; decision trees/forests/boosting are scale-invariant. Know which your model is.

**`StandardScaler` assumes roughly Gaussian, is outlier-sensitive.**
An outlier skews the mean/std. For heavy-tailed or outlier-prone features, `RobustScaler` (median/IQR) is better. Match the scaler to the data.

**Scaling the target is usually wrong (for classification) and sometimes needed (regression).**
Scale *features*, not the class label. For regression, scaling the target is occasionally useful but changes the interpretation of the score; usually leave `y` unscaled.

**`ColumnTransformer` for heterogeneous columns.**
Real data has numeric columns (scale) and categorical columns (encode) together. `ColumnTransformer` applies different preprocessing to different columns within a pipeline. A single scaler on mixed data is wrong.

**Leakage is subtler than scaling.** §66.2.
Feature selection, target encoding, and any target-derived feature computed over all data leak. Time-series leakage (future data predicting the past) is especially dangerous. Do all data-dependent preprocessing within the training fold.

**Pipelines and cross-validation compose.**
Putting a pipeline inside `cross_val_score`/`GridSearchCV` fits the preprocessing separately per fold, correct. Fitting preprocessing *once* outside CV leaks across folds. Always put preprocessing inside the pipeline inside the CV.

**Fitted scaler must be saved with the model.**
At deployment, new data must be scaled with the *training* statistics (the fitted scaler), not re-fit. A pipeline (persisted whole) handles this; a separately-managed scaler is a chance to get it wrong.

---

## 66.5 Connections

**Backward.**
The leakage this prevents is Chapter 65's deferred hazard. The feature matrix being preprocessed is Deep U (Chapters 57, 63) and NumPy (Deep T). Imputation is Chapter 62 (missing data). Encoding categoricals relates to Chapter 63 (get-dummies). The estimator API a pipeline exposes is Chapter 65.

**Forward.**
`ColumnTransformer`, `GridSearchCV` (model + hyperparameter selection, with pipelines inside CV), custom transformers, and specific algorithms (which need scaling, which do not) are the rest of **Deep W**. Feature engineering and selection (done leakage-free) are Deep W. Model persistence (saving the fitted pipeline) is a deployment topic.

**Across books.**
Leakage-free preprocessing pipelines are non-negotiable in **Book III**'s modeling: a quant signal model whose features leaked future information backtests beautifully and loses money live, so the discipline, preprocess within a pipeline, fit on train (or per CV fold) only, respect time order, is a correctness requirement, not a convenience. The order-book system builds every model as a pipeline (scaling and encoding inside), evaluates with time-respecting cross-validation, and treats any preprocessing that touches data outside the training fold as a bug, the §66.2 discipline as a hard rule, because leakage produces exactly the false confidence that is most dangerous when a model's output drives a trade. Deep W's methodology (Chapters 65-66) is the foundation every algorithm rests on.

---

## 66.6 Exercises

**1. Scale and pipeline.** Reproduce §66.1: use `StandardScaler` to standardize features, build a `Pipeline` with a model, and confirm fitting/predicting runs the whole chain. Explain what the pipeline does at fit versus predict.

**2. Measure scaling.** Reproduce §66.3. Confirm scaling helps the KNN. Then make the scale mismatch larger (1,000,000x) and show the unscaled accuracy collapse. Explain KNN's distance sensitivity, and confirm a tree model is unaffected.

**3. Cause and prevent leakage.** Fit a scaler on the whole dataset before splitting (leakage) versus inside a pipeline (correct), evaluate both, and show the leaky version gives an optimistic (higher) test score. Explain the leakage and why the pipeline prevents it.

**4. Heterogeneous columns.** Use `ColumnTransformer` to scale numeric columns and one-hot-encode categorical columns within one pipeline. Explain why a single scaler on mixed data is wrong.

**5. The design question.** Preprocessing must be fit on training data only, and a `Pipeline` enforces this. Argue why leakage is the most dangerous ML bug (silent, invalidating), using §66.2, and why making leakage-free preprocessing the default (via pipelines) matters more than remembering to do it manually. How do pipelines and cross-validation compose to prevent leakage across folds?

---

## 66.7 Summary and cross-references

- Raw features often need **preprocessing**. **`StandardScaler`** standardizes each feature to **mean 0, std 1**, required by **scale-sensitive models** (KNN, SVM, k-means, gradient-based) that measure feature magnitude; **tree models** do not need it.
- A **`Pipeline`** chains preprocessing + model into one estimator (`fit`/`predict`/`score` runs the whole chain), and, crucially, **fits preprocessing on training data only**, preventing **data leakage** automatically (and correctly per-fold inside cross-validation).
- **Measured:** a KNN on features with a 1000x scale mismatch scores **0.78** unscaled and **0.84** scaled, because the large feature dominates the distance until scaling equalizes them.
- **Leakage** (fitting preprocessing on the whole dataset, target-derived features over all data, time-series future-peeking) is the most dangerous ML bug, silent and invalidating. **The discipline:** preprocess within a `Pipeline`, fit on train (or per CV fold) only.
- **Edges:** `StandardScaler` is outlier-sensitive (use `RobustScaler` for heavy tails); use `ColumnTransformer` for mixed column types; scale features not labels; persist the fitted pipeline for deployment; put preprocessing inside CV.

**Cross-references.** Leakage / evaluation discipline → Chapter 65. Feature matrix / encoding → Chapters 57, 63. Missing-data imputation → Chapter 62. NumPy arrays → Deep T. `ColumnTransformer`, `GridSearchCV`, feature engineering, algorithms → the rest of Deep W. Book III model correctness → Deep W / Book III.
