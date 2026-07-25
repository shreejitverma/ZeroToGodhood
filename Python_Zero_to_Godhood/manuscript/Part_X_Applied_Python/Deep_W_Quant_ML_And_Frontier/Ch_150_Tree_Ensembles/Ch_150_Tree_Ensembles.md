# Chapter 69: Tree Ensembles

Chapters 65-68 built the *methodology*, how to evaluate a model honestly.
This chapter turns to *algorithms*, and to the family that dominates the problem most data engineers actually face: prediction from **tabular data** (rows of features, the DataFrames of Deep U).
For images, text, and sequences, neural networks win; for *tables*, the champions are **tree ensembles**, random forests and gradient-boosted trees, and they are almost always the right first model for a table of features.

The idea builds on a single **decision tree**: splitting the data on feature thresholds until each leaf is pure.
A single tree, grown fully, *memorizes* its training data (train accuracy 1.0) and *overfits*, the Chapter 65 hazard, with a large train-test gap (train 1.0, test 0.77).
The fix is an **ensemble**: train *many* trees, each on a random bootstrap sample of the data and a random subset of features, and average their votes.
The individual trees still overfit, but their errors are *diverse* and *average out*, so the forest keeps the signal and cancels the noise.
Measured, a 100-tree random forest lifts test accuracy from the single tree's **0.77** to **0.85**, same perfect training score, far better generalization.

**This is Deep W's core-algorithm chapter.**
It applies the overfitting lesson (Chapter 65), needs no scaling (Chapter 66, trees split per feature), operates on the feature matrix (Deep U), and is the workhorse for **Book III**'s tabular prediction.

## Section index

- **69.1** Trees, forests, and feature importance
- **69.2** Why ensembles work, and which to use
- **69.3** Measurement: single tree versus forest
- **69.4** Edges and failure modes
- **69.5** Connections
- **69.6** Exercises
- **69.7** Summary and cross-references

Listings live under `code/ch150/` and are re-executed by `make verify` on both verification interpreters.

---

## 69.1 Trees, forests, and feature importance

```python
# code/ch150/l01_ensembles.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a single deep decision tree MEMORIZES and overfits ---
  tree  train accuracy : 1.0   (memorized)
  tree  test accuracy  : 0.773   (overfit: big gap)
--- a random forest (100 trees) averages out the overfitting ---
  forest train accuracy : 1.0
  forest test accuracy  : 0.85   (better generalization)
  forest beats the single tree on test : True
--- ensembles give FEATURE IMPORTANCES (which features matter) ---
  top-3 most important feature indices : [3, 4, 19]
  importances sum to ~1.0 : True
--- trees need NO scaling (they split per feature, Chapter 66) ---
  forest is scale-invariant : unlike KNN/SVM, no StandardScaler needed
--- the rule ---
  ensembles (random forest, gradient boosting) turn many overfitting trees
  into a strong, generalizing model; they need no scaling and rank features
```

**A single decision tree overfits.**
A `DecisionTreeClassifier` grown to purity fits the training data *perfectly* (train accuracy 1.0), it has carved the feature space into regions that each memorize their training points, but it *overfits*: test accuracy is only 0.77, a 0.23 gap between train and test that is the signature of memorization (Chapter 65). A single deep tree is *high-variance*: small changes in the training data produce wildly different trees, because it fits the noise.

**A random forest averages the overfitting away.**
A `RandomForestClassifier` trains *many* trees (100 here), each on a different **bootstrap** sample (a random resample with replacement) of the data and considering a **random subset of features** at each split. Each tree still overfits, but they overfit *differently* (diverse errors), so averaging their votes *cancels* the idiosyncratic errors while *reinforcing* the shared signal. The forest's test accuracy is **0.85**, meaningfully better than the single tree's 0.77, with the same perfect training score. This is variance reduction through diversity: many weak, overfitting learners combine into a strong, generalizing one.

**Feature importances** come for free.
The forest exposes `feature_importances_`, how much each feature contributed to reducing impurity across all the trees (summing to ~1.0), so you can see *which* features drive predictions (top-3 here: indices 3, 4, 19). This *interpretability*, knowing which features matter, is a major practical advantage of tree ensembles over black-box models.

**No scaling needed.**
Unlike KNN/SVM (Chapter 66), trees split on *thresholds per feature* (`is feature 3 > 0.5?`), so they are *invariant* to feature scale, no `StandardScaler` required. This makes them low-effort: feed the raw feature matrix (handling only missing values and categoricals) and they work.

---

## 69.2 Why ensembles work, and which to use

Ensembles are the dominant tabular-ML approach, and understanding *why* and *which* guides their use.

**Why ensembles work: bias-variance and diversity.**
A single deep tree has *low bias* (it can fit anything) but *high variance* (it fits noise, overfits).
An ensemble *reduces variance* by averaging diverse models: if each tree's error has a random component, averaging many trees cancels the random part (like averaging noisy measurements reduces noise).
The key is **diversity**, the trees must make *different* errors, which the random forest ensures via bootstrap sampling (different data per tree) and random feature subsets (different splits).
The result: the ensemble keeps the low bias (it can still fit complex patterns) while cutting the variance (it does not overfit like one tree). This is the bias-variance trade-off resolved in the ensemble's favor.

**The two ensemble strategies:**

- **Bagging (Random Forests):** train trees *independently* on bootstrap samples, average them. Reduces variance. Robust, parallel, hard to overfit by adding trees, a strong, low-tuning default.
- **Boosting (Gradient Boosting: XGBoost, LightGBM, CatBoost):** train trees *sequentially*, each correcting the previous ones' errors. Reduces bias *and* variance, and typically achieves *higher* accuracy than random forests, but needs more tuning (learning rate, tree count) and can overfit if over-trained. The usual *winner* on tabular ML competitions.

**Which to use:**

- **Random Forest** as a strong, low-effort baseline: minimal tuning, robust, gives feature importances. Start here.
- **Gradient Boosting** (XGBoost/LightGBM) for maximum tabular accuracy, with hyperparameter tuning (via cross-validation, Chapter 68).
- Both need **no scaling**, handle mixed feature types well, are **robust to irrelevant features** (they just do not split on them), and provide **feature importances**.

**Why trees, not neural nets, for tables.**
On *tabular* data, tree ensembles consistently *match or beat* neural networks, with far less tuning, no scaling, and built-in interpretability. Neural networks dominate on *unstructured* data (images, text, audio, sequences) where the structure (spatial, sequential) suits them. So the practical rule: **for a table of features, reach for a tree ensemble first; reserve neural networks for unstructured data.** This surprises people expecting deep learning to win everywhere, but on tables, gradient-boosted trees are the state of the art.

The rule: **for tabular prediction, use tree ensembles (random forest as a baseline, gradient boosting for peak accuracy), which are strong, low-effort, scale-free, robust, and interpretable.** They are the workhorse, and the first model to try on any table.

---

## 69.3 Measurement: single tree versus forest

**Methodology.** `code/ch150/bench_ensemble.py`.
A quality measurement. A single decision tree versus a 100-tree random forest on the same 20-feature, 1000-sample classification data, comparing train and test accuracy (and the train-test gap).
CPython 3.13.5, scikit-learn 1.6.1.

| model | train | test | gap |
|---|---|---|---|
| single tree | 1.000 | 0.773 | 0.227 |
| random forest (100) | 1.000 | 0.850 | 0.150 |

Both models achieve a *perfect* training score (1.0), they can both memorize, but on held-out test data the single tree scores **0.77** and the forest **0.85**, and the train-test *gap* shrinks from **0.23** to **0.15** (identical on both interpreters).
The forest generalizes better *from the same overfitting trees*, purely by averaging their diverse errors.

This is variance reduction quantified, and it is the central idea of ensemble learning.
The single tree's large gap (0.23) is high variance, it fit the training noise, and the noise does not transfer.
The forest's smaller gap (0.15) and higher test score come from *diversity*: 100 trees, each overfitting *differently* (different bootstrap samples, different feature subsets), whose errors partly *cancel* when averaged.
The perfect training score is retained (the ensemble can still fit the data), but the *test* performance, the thing that matters, is markedly better.

The practical lesson closes the loop with the methodology (Chapters 65-68).
The single tree *looked* as good as the forest by training score (both 1.0), only *held-out* evaluation (Chapter 65) reveals the forest's superiority, and only *cross-validation* (Chapter 68) would tell you the difference is real, not noise.
So algorithm and methodology work together: the ensemble is a *better* model, and the honest evaluation is what *proves* it.
For tabular data, this is the default workflow: build a feature matrix (Deep U), reach for a tree ensemble (this chapter), evaluate with held-out, leakage-free, right-metric cross-validation (Chapters 65-68), and tune the gradient-booster's hyperparameters by CV.
**Book III**'s tabular models, quant signals from engineered features, risk classifiers, are overwhelmingly gradient-boosted trees, chosen because on tables they win, evaluated with the strict methodology because that is what makes their edge trustworthy. The order-book system's feature-based predictive models are tree ensembles (gradient-boosted for accuracy, random forests for a robust baseline and feature importance), fed engineered features, evaluated with time-respecting cross-validation, the §69.2 rule (trees for tables) and the Chapters 65-68 methodology combined into the standard tabular-ML workflow.

---

## 69.4 Edges and failure modes

**A single tree overfits; use an ensemble.** §69.1, §69.3.
One deep tree is high-variance. Random forests (bagging) and gradient boosting reduce variance by averaging diverse trees.

**Boosting can overfit if over-trained.** §69.2.
Unlike random forests (hard to overfit by adding trees), gradient boosting overfits if you add too many trees or set the learning rate too high. Tune (via CV) and use early stopping.

**Trees need no scaling but do need encoded categoricals and handled missing values.** §69.1.
Scale-invariant, but most implementations need numeric features (encode categoricals, Chapter 63) and handled `NaN`s (Chapter 62), though some (LightGBM, HistGradientBoosting) handle missing natively.

**Feature importances can mislead.**
Impurity-based importances are biased toward high-cardinality features and can be unreliable with correlated features. Use permutation importance or SHAP values for more trustworthy interpretation.

**Random forests are memory- and compute-heavy.**
100+ full trees use significant memory and prediction time. For large-scale or latency-sensitive deployment, gradient boosting (smaller trees) or model compression may be needed.

**Extrapolation fails.**
Trees predict a constant outside the training data's range (they cannot extrapolate a trend), so for data far outside the training distribution, tree predictions are unreliable. Linear models extrapolate; trees do not.

**For unstructured data, use neural networks.** §69.2.
Tree ensembles are for *tabular* data. Images, text, audio, and sequences need neural networks (CNNs, transformers). Do not force trees onto unstructured data.

**Set `random_state` for reproducibility.**
Random forests and boosting use randomness (bootstrap, feature subsets); fix `random_state` for reproducible results, and remember a single seed's result has variance (cross-validate, Chapter 68).

---

## 69.5 Connections

**Backward.**
The overfitting a single tree exhibits is Chapter 65. Trees needing no scaling is Chapter 66 (contrast KNN/SVM). They operate on the feature matrix (Deep U) with encoded categoricals (Chapter 63) and handled missing values (Chapter 62). Evaluating tree-vs-forest honestly is Chapters 65-68. Variance reduction by averaging is the statistics of the mean (noise reduction).

**Forward.**
Gradient boosting (XGBoost, LightGBM), hyperparameter tuning by CV (`GridSearchCV`, Chapter 68), permutation/SHAP feature importance, and the tree-versus-neural-net choice are the rest of **Deep W**. Neural networks and deep learning (for unstructured data) are frontier Deep W. Quant-specific modeling (features -> tree ensemble -> backtest) is Deep W.

**Across books.**
Tree ensembles are **Book III**'s default for tabular prediction: quant signals built from engineered features, credit/risk classifiers, and forecasters from structured data are gradient-boosted trees, because on tables they are state of the art, low-effort, and interpretable (feature importances show *which* signals drive the model). The order-book system's feature-based models are tree ensembles fed engineered market features, evaluated with time-respecting CV, and the feature importances guide feature engineering (which signals matter). It reserves neural networks for its unstructured inputs (order-flow sequences, text), the §69.2 rule (trees for tables, nets for sequences/images) applied by data type. Deep W's algorithm chapters build on its methodology chapters: the ensemble is the model, the honest evaluation is what makes its edge real.

---

## 69.6 Exercises

**1. Tree versus forest.** Reproduce §69.1: fit a single tree and a random forest, compare train and test accuracy, and confirm the forest generalizes better. Inspect feature importances. Explain the overfitting and how the ensemble reduces it.

**2. Measure variance reduction.** Reproduce §69.3. Confirm the forest's smaller train-test gap and higher test accuracy. Then vary the number of trees (10, 100, 500) and show test accuracy improving then plateauing. Explain diminishing returns.

**3. Bagging versus boosting.** Compare a random forest with a gradient-boosting model on the same data (tune the booster with CV). Show boosting's higher accuracy and discuss its tuning cost. Explain the independent-versus-sequential difference.

**4. No scaling needed.** Show a tree ensemble gives identical results with and without feature scaling (unlike KNN, Chapter 66). Explain why trees are scale-invariant.

**5. The design question.** Tree ensembles dominate tabular ML while neural networks dominate unstructured data. Argue why (variance reduction via diversity, no scaling, interpretability, robustness), using §69.3, and why "reach for a tree ensemble first on a table" is the right default. When is a neural network the right choice instead?

---

## 69.7 Summary and cross-references

- A **single decision tree** splits on feature thresholds until pure; grown fully it **memorizes and overfits** (train 1.0, big train-test gap). It is high-variance (fits noise).
- A **random forest** trains many trees on **bootstrap samples** with **random feature subsets** and averages them; the trees overfit *diversely*, so their errors **cancel**, reducing variance and generalizing far better. Ensembles need **no scaling** (trees split per feature) and give **feature importances**.
- **Measured:** a single tree scores test **0.77** (gap 0.23); a 100-tree forest scores test **0.85** (gap 0.15), same perfect training score, better generalization via variance reduction.
- **Two strategies:** **bagging** (random forests, independent trees, robust low-tuning baseline) and **boosting** (gradient boosting: XGBoost/LightGBM, sequential error-correction, higher accuracy, more tuning). **For tabular data, tree ensembles are state of the art**; reserve neural networks for unstructured data (images, text, sequences).
- **Edges:** boosting overfits if over-trained (tune, early-stop); encode categoricals and handle `NaN`s; impurity importances can mislead (use permutation/SHAP); trees cannot extrapolate; set `random_state` (and cross-validate).

**Cross-references.** Overfitting → Chapter 65. No scaling needed (vs KNN/SVM) → Chapter 66. Metrics/CV for honest comparison → Chapters 67-68. Feature matrix / encoding / missing data → Chapters 57, 63, 62 (Deep U). Gradient boosting, tuning, SHAP, neural networks → the rest of Deep W. Book III tabular models → Deep W / Book III.
