# Chapter 72: Feature Engineering

Deep W has surveyed the methodology (Chapters 65-68, 70) and the models (Chapters 69, 71), and it closes on the skill that matters *most* and gets discussed *least*: **feature engineering**, transforming raw data into inputs that expose the pattern.
The under-appreciated truth of applied machine learning is that **a model can only learn from what the features encode**, so the biggest gains usually come from *better features*, not a fancier model or more hyperparameter tuning.
This chapter demonstrates it and, in doing so, ties the whole applied arc together: Deep U builds the data tools, Deep W the models, and feature engineering is the bridge, the place where *domain knowledge* enters the pipeline.

The demonstration is stark.
The **XOR** problem, target positive when two features have the *same sign*, is *not* linearly separable, so a linear model on the raw features scores **0.56**, near chance.
Add *one* engineered feature, the interaction `x1 * x2` (positive exactly when the signs agree), and the *same* linear model jumps to **0.97**.
No change to the model, only a better feature that *encodes the pattern directly*, and a problem that seemed to need a non-linear model (Chapter 71's neural net) is solved by a simple linear one.
Feature engineering can *substitute for model complexity*: the right feature hands the model the answer.

**This closes Deep W, and the applied volumes.**
It is the bridge from Deep U (data engineering) to Deep W (models), draws on time features (Chapter 61), encodings (Chapter 63), and leakage discipline (Chapters 66, 70), and is where the human understanding of the problem, which no model learns on its own, shapes what the model can achieve.

## Section index

- **72.1** The right feature beats a fancier model
- **72.2** Engineering features: kinds, and the discipline
- **72.3** Measurement: features versus model complexity
- **72.4** Edges and failure modes
- **72.5** Connections
- **72.6** Exercises
- **72.7** Summary and cross-references

Listings live under `code/ch153/` and are re-executed by `make verify` on both verification interpreters.

---

## 72.1 The right feature beats a fancier model

```python
# code/ch153/l01_features.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- raw features (x1, x2): the pattern is NOT linearly separable ---
  linear model CV accuracy : 0.558   (near chance: XOR needs a curve)
--- add ONE engineered feature: the interaction x1 * x2 ---
  linear model CV accuracy : 0.965   (near-perfect: now linear!)
  the SAME model, better features, gained : 0.407
--- why: the interaction directly encodes the pattern (same sign) ---
  x1*x2 > 0 exactly when the signs agree, so the target is now a
  linear function of the features; the model had the answer handed to it
--- common engineered features ---
  interactions (a*b), ratios (a/b), differences, aggregates, time features
  (Chapter 61), domain transforms, encodings (Chapter 63), binning
--- the rule ---
  invest in FEATURES, not just models: the right feature can let a simple
  model solve what looked like it needed a complex one (features > models)
```

**The XOR problem defeats a linear model in the raw features.**
The target is 1 when `x1` and `x2` have the *same sign*, a checkerboard pattern that *no line* separates. So logistic regression on `(x1, x2)` scores **0.56** (cross-validated, Chapter 68), barely above chance: the pattern is *invisible* to a linear model in these features.

**One engineered feature makes it trivial.**
Add `x1 * x2`, the *interaction*. This product is positive *exactly* when the signs agree (the target), so the target is now a *linear* function of the features (thresholding one feature), and the *same* linear model scores **0.97**, a **0.41** gain from a single feature, no model change.

**Why:** the engineered feature *encodes the pattern directly*.
The model does not have to *discover* the interaction (which a linear model *cannot*, and a neural net *can* but needs capacity and data, Chapter 71); the feature *hands* it the relevant quantity, and the problem becomes linear.
This is the essence of feature engineering: **transform the data so the pattern is exposed**, and even a simple model succeeds.

The listing's last block previews the vocabulary, interactions, ratios, differences, aggregates, time features, domain transforms, encodings, binning, and the rule states the principle: **invest in features, not just models.**
The XOR example is a toy, but the lesson is real and pervasive: across applied ML, the largest, cheapest gains come from features that expose the signal, more than from swapping models or tuning hyperparameters.

---

## 72.2 Engineering features: kinds, and the discipline

Feature engineering is where *domain knowledge*, the human understanding of what drives the target, becomes model input, and it is both a craft and a discipline.

**Kinds of engineered features:**

- **Interactions and combinations:** products (`a * b`), ratios (`a / b`), differences (`a - b`), that capture relationships between features (as XOR showed). A ratio like price-to-earnings, a difference like bid-ask spread, an interaction like price times volume, each encodes a relationship the model would otherwise have to discover.
- **Aggregates:** per-group summaries (Chapter 58) as features, "average purchase per customer", "count of events per session", "rolling mean of a signal".
- **Time features** (Chapter 61): from a timestamp, day-of-week, hour, is-holiday, time-since-last-event; from a series, lags, differences, rolling statistics. These encode temporal structure.
- **Domain transforms:** log for skewed/multiplicative quantities, returns (percent change) for prices, normalization by a relevant baseline, transforms the domain says are meaningful.
- **Encodings** (Chapter 63): categoricals to numbers (one-hot, ordinal, target encoding done leakage-free), text to features (bag-of-words, embeddings), that make non-numeric data model-ready.
- **Binning/discretization:** grouping a continuous feature into ranges, sometimes exposing non-linear thresholds.

**The discipline:**

- **Encode domain knowledge.** The most valuable features come from *understanding the problem*: what quantities the domain expert knows matter. A model cannot invent a feature that requires knowledge outside the data (that a certain ratio is meaningful, that a certain event predicts another); *you* supply it. This is why feature engineering is the highest-leverage skill, it injects information the model cannot derive alone.
- **Engineer leakage-free.** Chapters 66 and 70. Every feature must be computable *at prediction time* using *only past/available* data. A feature using future information (a centered average, a whole-series statistic, a target-derived value) leaks (Chapter 70) and invalidates the model. Compute features within the training fold (pipelines).
- **More features is not always better.** Irrelevant features add noise and overfitting risk; redundant features add nothing. Feature *selection* (keeping the useful ones, using importances from Chapter 69, or statistical tests) complements engineering. Quality over quantity.
- **Iterate with the model.** Engineer features, evaluate (Chapters 65-70), inspect feature importances (Chapter 69) to see what works, and refine. Feature engineering is an iterative loop guided by honest evaluation.

The rule: **invest in features that encode domain knowledge and expose the signal, engineer them leakage-free, and iterate guided by honest evaluation.**
Feature engineering is where the applied ML pipeline's *intelligence* often lives, more than in the model choice, because it is where *human understanding of the problem* shapes what is learnable.

---

## 72.3 Measurement: features versus model complexity

**Methodology.** `code/ch153/bench_features.py`.
A quality measurement. On the XOR problem, a linear model on the raw features versus the same model plus one engineered interaction feature (`x1 * x2`), 5-fold cross-validated.
CPython 3.13.5, scikit-learn 1.6.1.

| linear model | CV accuracy |
|---|---|
| raw features (`x1`, `x2`) | 0.558 |
| + engineered `x1 * x2` | **0.965** |
| gain (features only) | **+0.407** |

The same simple model jumps from near chance (**0.56**) to near-perfect (**0.97**), with **no model change**, only a better feature (identical on both interpreters).

The lesson is the central, under-appreciated truth of applied ML.
Faced with the raw XOR data, you might reach for a *more powerful model*, a neural network (Chapter 71, which *would* solve it, at the cost of data, compute, tuning, and opacity).
But *one engineered feature* solves it with a *linear* model, simpler, faster, interpretable.
The feature *substitutes* for the model complexity, because it *encodes the non-linear pattern* the linear model could not express, turning a hard problem into an easy one.

This reframes where effort should go.
Practitioners often over-invest in *model selection and hyperparameter tuning* (swapping algorithms, grid-searching), and under-invest in *features*, yet features usually offer the larger, cheaper gains, because they inject *information* (domain knowledge, exposed structure) that no amount of model tuning can recover if the features do not encode it.
"Better features beat better models" is the applied-ML adage, and the XOR measurement is its clearest illustration: `+0.41` from *one feature*, more than any model swap would give on the raw features.

This closes Deep W, and the applied volumes (Deep T, U, W), on their unifying theme.
Deep T made *computation* fast (vectorized, typed arrays). Deep U made *data* manageable (columnar DataFrames, groupby, merge, honest handling of scale and missingness). Deep W made *prediction* trustworthy (honest evaluation) and *capable* (the right model), and feature engineering is the bridge where *the human understanding of the problem* enters, transforming Deep U's data into the inputs Deep W's models learn from.
The applied arc is: build the data (Deep U), engineer features that encode what matters (this chapter), choose a model matched to the data (Deep W algorithms), and evaluate honestly (Deep W methodology), and the intelligence of the result depends as much on the *features* (domain knowledge) as on the model.
**Book III**'s predictive systems are built exactly this way, and their edge comes disproportionately from *feature engineering*: the market microstructure features, the engineered signals, the domain-informed transforms that expose the pattern a raw price series hides. The order-book system's models succeed largely on the strength of features engineered from deep market-structure knowledge, computed leakage-free and validated walk-forward, because in quant, as in all applied ML, the feature that encodes a real edge, informed by understanding the domain, is worth more than any model, and it is the place where human insight, which the model cannot supply, makes the system intelligent. Deep W ends here, at the skill that most determines whether an applied ML system works.

---

## 72.4 Edges and failure modes

**Features can substitute for model complexity.** §72.1, §72.3.
The right feature lets a simple model solve a hard problem. Invest in features before reaching for a more complex model.

**Engineer features leakage-free.** §72.2, Chapters 66, 70.
Every feature must use only data available at prediction time (no future, no whole-dataset statistics, no target-derived values). A leaky feature invalidates the model. Compute within the training fold (pipelines).

**More features is not always better.** §72.2.
Irrelevant features add noise and overfitting; redundant features add nothing. Select features (importances, tests); quality over quantity.

**Domain knowledge is irreplaceable.** §72.2.
The best features come from understanding the problem, information the model cannot derive from the data alone. Feature engineering is where domain expertise enters; a black-box model does not substitute for it.

**Feature engineering is iterative and evaluation-guided.** §72.2.
Engineer, evaluate (honestly, Chapters 65-70), inspect importances, refine. Do not engineer blindly; let honest evaluation and importances guide which features help.

**Automated feature engineering has limits.**
Tools that generate features automatically (polynomial features, featuretools) can help but produce many irrelevant features and can leak if not careful. They complement, not replace, domain-informed manual engineering.

**Deep learning learns features, but not for tables.** Chapter 71.
Neural networks *learn* representations (features) from raw unstructured data (images, text), reducing manual engineering there. But for *tabular* data, hand-engineered features plus a tree ensemble usually beat a neural net; feature engineering remains essential for tables.

**Scaling and encoding are feature engineering too.** Chapters 66, 63.
Scaling (for scale-sensitive models) and encoding categoricals are preprocessing that is part of feature engineering, and part of the leakage-free pipeline.

---

## 72.5 Connections

**Backward.**
Feature engineering bridges Deep U (the data tools: DataFrames, groupby aggregates as features, Chapter 58; time features, Chapter 61; encodings, Chapter 63) and Deep W (the models). Leakage-free engineering is Chapters 66 and 70. Evaluating whether a feature helps is Chapters 65-68. The XOR non-linearity is Chapter 71 (what features can substitute for). Feature importances (which features matter) are Chapter 69.

**Forward.**
Automated feature engineering, feature selection methods, representation learning (deep learning learning features), embeddings (text/categorical), and domain-specific feature libraries are the frontier of **Deep W** / Book III. Feature stores (managing engineered features at scale) are a Deep U / MLOps topic.

**Across books.**
Feature engineering is where **Book III**'s domain knowledge, deep understanding of market microstructure, becomes model input, and it is the largest source of edge. A quant model's performance depends far more on the *features* (engineered signals, microstructure metrics, cross-asset relationships, informed by understanding *why* they predict) than on the model choice, because the feature is where a *real, understood edge* is encoded, and no model can invent an edge the features do not contain. The order-book system's predictive edge comes disproportionately from features engineered from deep domain knowledge, computed leakage-free, validated walk-forward, the model is almost a commodity (a tree ensemble), the *features* are the intellectual property. This is the culminating lesson of the applied arc: the tools (Deep T, U, W) are learnable and shared, but the *features that encode a real, domain-informed edge* are where human understanding makes an applied ML system genuinely intelligent, and that is the skill Deep W, and the applied volumes, close on.

---

## 72.6 Exercises

**1. Engineer a feature.** Reproduce §72.1: show a linear model failing on XOR raw features and succeeding with the interaction feature. Explain how the feature encodes the pattern and why it substitutes for model complexity.

**2. Measure the gain.** Reproduce §72.3. Confirm the same model gains ~0.41 from one feature. Then compare to switching to a neural net (Chapter 71) on the raw features, and discuss which is simpler.

**3. Leakage-free features.** Engineer a time feature two ways: using future data (leaky) and using only past data (correct, Chapter 70). Show the leaky one inflates a backtest. Explain the discipline.

**4. Domain features.** For a dataset you understand, engineer three domain-informed features (a ratio, an aggregate, a time feature) and show they improve a model. Explain what domain knowledge each encodes.

**5. The design question.** "Better features beat better models" is applied ML's adage. Argue why, using §72.3 (a feature substituting for complexity) and the fact that features inject domain knowledge a model cannot derive. Where should effort go, features or model selection, and why? How does this close the applied arc (Deep T -> U -> W)?

---

## 72.7 Summary and cross-references

- **Feature engineering** transforms raw data into inputs that expose the pattern, and it is the highest-leverage ML skill: **a model can only learn from what the features encode**, so the biggest gains usually come from **better features, not a fancier model**.
- **Measured:** on XOR (not linearly separable), a linear model scores **0.56** on raw features and **0.97** with one engineered interaction feature (`x1*x2`), a **+0.41** gain from a *single feature*, no model change. The feature **substitutes for model complexity**.
- **Kinds:** interactions/ratios/differences, aggregates (Chapter 58), time features (Chapter 61), domain transforms (log, returns), encodings (Chapter 63), binning.
- **The discipline:** encode **domain knowledge** (information the model cannot derive), engineer **leakage-free** (only past/available data, within the training fold, Chapters 66, 70), prefer **quality over quantity** (irrelevant features hurt; select), and **iterate** guided by honest evaluation and feature importances (Chapter 69).
- **This closes the applied arc (Deep T -> U -> W):** build data, engineer features (domain knowledge), choose a matched model, evaluate honestly. Feature engineering is the bridge where human understanding makes the system intelligent, often the largest source of a model's edge.

**Cross-references.** Aggregates / time features / encodings → Chapters 58, 61, 63 (Deep U). Leakage-free engineering → Chapters 66, 70. Evaluation (does a feature help) → Chapters 65-68. Non-linearity features substitute for → Chapter 71. Feature importances → Chapter 69. Automated feature engineering, embeddings, feature stores → the frontier of Deep W / Book III. This closes Deep W (Quant, ML, Frontier) and the applied volumes.
