# Chapter 71: Neural Networks

This chapter reaches the frontier of Deep W: **neural networks**, the model family behind the deep-learning revolution, and it places them correctly, powerful for the right problems, overkill for the wrong ones.
The core capability is one thing: a neural network can learn *arbitrary non-linear patterns* that a linear model cannot.
A linear model (logistic/linear regression) draws a *straight* decision boundary, so it fails on data that is not linearly separable; a neural network, by stacking layers of neurons with non-linear activations, learns *curved* boundaries of any shape.

The measurement makes the difference vivid.
On **concentric circles**, one class inside the other, no straight line separates the classes, so a linear model scores **0.44** (near chance).
A small neural network with two hidden layers learns the *circular* boundary and scores **0.99**.
This is the **universal approximation** property: a neural network with hidden layers can approximate essentially any function, composing simple non-linear units into arbitrary shapes.

But the chapter's discipline is *where* to use them.
Neural networks need more data, more compute, careful tuning, and are far less interpretable than tree ensembles (Chapter 69), so for *tabular* data, trees usually match or beat them with far less effort.
Neural networks earn their complexity on **unstructured** data, images, text, sequences, audio, where their structure suits the problem and they are the state of the art.
The rule: **neural networks for complex non-linear patterns and unstructured data; trees for tables.**

**This is Deep W's frontier chapter.**
It contrasts with linear models and tree ensembles (Chapter 69), builds on the evaluation methodology (Chapters 65-70), and gestures at the deep-learning domains of **Book III**'s frontier work.

## Section index

- **71.1** Linear limits and the neural network
- **71.2** What neural networks are for
- **71.3** Measurement: non-linear separation
- **71.4** Edges and failure modes
- **71.5** Connections
- **71.6** Exercises
- **71.7** Summary and cross-references

Listings live under `code/ch152/` and are re-executed by `make verify` on both verification interpreters.

---

## 71.1 Linear limits and the neural network

```python
# code/ch152/l01_neural_net.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a LINEAR model cannot separate non-linear (circular) classes ---
  logistic regression test accuracy : 0.44
  near chance: a straight line cannot enclose the inner circle
--- a NEURAL NET with hidden layers learns the non-linear boundary ---
  MLP (2 hidden layers of 16) test accuracy : 0.987
  it learned the circular decision boundary
--- the architecture: layers of neurons with non-linear activations ---
  hidden layers   : (16, 16)
  activation      : relu   (the non-linearity that enables curves)
  the net beats the linear model by : 0.547
--- the trade-off ---
  neural nets learn ANY function (universal approximation) but need more
  data, compute, and tuning, and are less interpretable than tree ensembles
--- the rule ---
  use neural nets for complex non-linear patterns and unstructured data
  (images, text, sequences); for tabular data, trees (Chapter 69) usually win
```

**The linear limit.**
Logistic regression draws a *straight* decision boundary (a line in 2D, a hyperplane in higher dimensions). On the concentric circles, one class *surrounds* the other, so *no* straight line separates them, and the linear model scores **0.44**, worse than a coin flip (it cannot enclose the inner circle with a line). This is the fundamental limitation of linear models: they can only separate *linearly separable* classes.

**The neural network.**
A neural network is layers of **neurons**, each computing a weighted sum of its inputs followed by a **non-linear activation** (here `relu`, `max(0, x)`). Stacking layers, an input layer, one or more **hidden layers**, an output layer, lets the network compose these non-linear units into *arbitrary* functions.
The MLP with two hidden layers of 16 neurons learns the *circular* boundary and scores **0.99**, beating the linear model by 0.55.
The **activation** is the key: without a non-linearity between layers, stacked linear layers collapse to a single linear function (no gain); the non-linear activation is what lets the network bend the boundary into curves.

**Universal approximation.**
The theoretical basis: a neural network with a hidden layer and enough neurons can approximate *any* continuous function to arbitrary accuracy. So neural networks are not limited to lines, or to any fixed shape; they learn whatever boundary the data requires. This flexibility is their power, and, unmanaged, their overfitting risk (Chapter 65).

So the neural network's contribution is **non-linearity via composition**: layers of simple non-linear units learning complex functions that linear models cannot express.

---

## 71.2 What neural networks are for

Neural networks are powerful *and* expensive, so knowing *when* to use them, and when not to, is the practical skill.

**The costs of neural networks:**

- **Data hungry:** they have many parameters, so they need *lots* of data to train without overfitting. On small data, simpler models (trees, linear) generalize better.
- **Compute intensive:** training is expensive (often needing GPUs for large networks), and inference can be too. Trees are far cheaper.
- **Tuning heavy:** architecture (layers, widths), learning rate, regularization, batch size, activations, many hyperparameters, each affecting results, requiring careful (cross-validated, Chapter 68) tuning. Trees work well with defaults.
- **Opaque:** no feature importances, understanding *why* a neural net predicts something is hard (an active research area: SHAP, attention, saliency). Trees are interpretable.
- **Preprocessing-sensitive:** they need scaled features (Chapter 66), unlike trees.

**Where neural networks win: unstructured data.**
The costs are worth it when the data has *structure* that neural architectures exploit:

- **Images:** convolutional neural networks (CNNs) exploit spatial locality, state of the art for vision.
- **Text and sequences:** transformers (and RNNs) exploit sequential/attention structure, the basis of large language models and modern NLP.
- **Audio, video, graphs:** specialized architectures for each.

On these, neural networks vastly outperform trees and linear models, because their architecture *matches* the data's structure (a CNN's convolutions mirror an image's spatial regularity), and they *learn the features* (representations) rather than needing hand-engineered ones.

**Where trees win: tabular data.** §71.1, Chapter 69.
On *tables* (rows of features, the DataFrames of Deep U), tree ensembles (gradient boosting) consistently *match or beat* neural networks, with far less data, compute, tuning, and with interpretability. So for tabular prediction, trees are the default (Chapter 69), not neural nets, a fact that surprises those who expect deep learning everywhere.

The rule: **reach for neural networks when the data is unstructured (images, text, sequences, audio) or the pattern is genuinely complex and you have enough data and compute; for tabular data, use tree ensembles.**
Neural networks are a *frontier tool for the right problem*, not a universal default.
Choosing them for a small tabular dataset is usually the wrong call (more effort, worse or equal results, no interpretability); choosing trees for image classification is equally wrong.
Match the model family to the data's structure.

---

## 71.3 Measurement: non-linear separation

**Methodology.** `code/ch152/bench_nonlinear.py`.
A quality measurement. On concentric-circle data (not linearly separable), a linear model (logistic regression) versus a small neural network (two hidden layers of 16).
CPython 3.13.5, scikit-learn 1.6.1.

| model | test accuracy |
|---|---|
| linear (logistic regression) | 0.440 |
| neural net (2x16 hidden) | **0.987** |

The linear model scores **0.44** (near chance), the neural net **0.99** (identical on both interpreters).
The gap is the value of *non-linearity*: the classes form circles, a shape no line can separate, so the linear model *cannot* express the boundary (any line it draws misclassifies about half), while the neural network *learns* the circular boundary through its hidden layers and non-linear activations.

The lesson is about *model capacity matching the problem*.
The linear model *underfits* here, not because it was trained badly, but because it *cannot represent* the required boundary (a fundamental limit, not a tuning issue). The neural network *can* represent it (universal approximation), so it succeeds.
This is the *opposite* end of the bias-variance spectrum from Chapter 69's single tree (which *overfit*): a linear model on non-linear data is *high bias* (too simple to fit the pattern), a deep tree is *high variance* (too flexible, fits noise), and the right model has *appropriate* capacity for the problem.

The measurement also cautions against over-reading it.
The neural net won *here* because the data is genuinely non-linear *and* there is enough of it (500 points) for the net to learn the smooth boundary.
On *tabular* data with hand-engineered features, a tree ensemble would likely match this with less effort (Chapter 69), and on *small* data, the neural net's flexibility could overfit.
So the finding is not "neural nets are better", it is "neural nets can express non-linear patterns linear models cannot", which matters *when the problem needs it and the data supports it*.
This completes Deep W's model-family survey: **linear models** (simple, interpretable, linear boundaries), **tree ensembles** (the tabular workhorse, non-linear, robust, interpretable), and **neural networks** (maximally flexible, for unstructured data and complex patterns, data/compute-hungry, opaque), each with a place, chosen by the data's structure and the problem's complexity.
**Book III**'s frontier work uses neural networks where they belong, order-flow *sequences* (transformers), *text* (news, filings) via language models, *image*-like market representations (CNNs), while its *tabular* signal models remain tree ensembles, the §71.2 rule applied by data type. The order-book system reserves deep learning for its unstructured inputs and complex sequence modeling, keeps trees for engineered-feature tables, and, critically, evaluates *all* of them with the same rigorous, look-ahead-free methodology (Chapters 65-70), because a neural network is no more exempt from overfitting and leakage than any other model, more prone, if anything, given its flexibility. Deep W's arc, methodology then algorithms then frontier, ends here, at the most powerful and most misapplied model family, placed in its proper role.

---

## 71.4 Edges and failure modes

**Neural nets need scaled features.** §71.2, Chapter 66.
Unlike trees, they are scale-sensitive (gradient descent). Scale features (via a pipeline). Unscaled features train poorly or not at all.

**They are data- and compute-hungry.** §71.2.
Many parameters need much data to avoid overfitting, and training is expensive. On small data, simpler models generalize better; on large data with GPUs, neural nets scale.

**Tuning is extensive.** §71.2.
Architecture, learning rate, regularization, and more, all matter and interact. Tune with cross-validation (Chapter 68). Defaults rarely suffice.

**For tabular data, trees usually win.** §71.2, Chapter 69.
Do not default to neural networks for tables; gradient-boosted trees match or beat them with less effort and interpretability. Reserve neural nets for unstructured data.

**They overfit easily (high capacity).** §71.3, Chapter 65.
Universal approximation means they can memorize; regularization (dropout, weight decay, early stopping) and enough data are essential. Evaluate rigorously (held-out, CV).

**Opacity limits trust and debugging.** §71.2.
No feature importances; understanding predictions needs special tools (SHAP, attention). For high-stakes or regulated decisions, interpretability may favor trees/linear models.

**sklearn's MLP is for learning, not production deep learning.**
`MLPClassifier` illustrates neural networks but is CPU-bound and basic. Real deep learning uses PyTorch/TensorFlow (GPU, autograd, modern architectures). This chapter's MLP is pedagogical.

**Reproducibility is harder.**
Neural net training involves more randomness (initialization, data order, GPU non-determinism); exact reproducibility is harder than for trees. Fix seeds where possible and report with CV.

---

## 71.5 Connections

**Backward.**
Neural nets contrast with linear models (this chapter) and tree ensembles (Chapter 69), completing the model-family survey. They need scaling (Chapter 66) and rigorous evaluation (Chapters 65-70). The non-linear activation composing into arbitrary functions is the universal approximation property. High bias (linear) versus appropriate capacity is the bias-variance framing of Chapter 69.

**Forward.**
Deep learning proper, CNNs (images), transformers (text/sequences, LLMs), training with backpropagation and GPUs, regularization (dropout), and the PyTorch/TensorFlow ecosystems are the frontier of **Deep W** / Book III. Representation learning (learning features rather than engineering them) is the deep-learning paradigm. Autograd connects to the numeric foundations (Deep T).

**Across books.**
Neural networks are **Book III**'s tool for unstructured and complex-sequence data: language models over financial text and filings, transformers over order-flow sequences, CNNs over image-like market representations, while tabular signals stay with tree ensembles. The order-book system applies deep learning where the data structure warrants it (sequences, text), keeps trees for engineered-feature tables (§71.2), and subjects every model, neural or not, to the same look-ahead-free, cross-validated evaluation (Chapters 65-70), because a flexible model is *more* prone to overfitting and leakage, not exempt. Placing neural networks correctly, powerful for the right problem, wrong as a default, is the frontier judgment Deep W closes on, and it is the same discipline throughout: match the tool to the problem, and evaluate honestly.

---

## 71.6 Exercises

**1. Linear versus neural.** Reproduce §71.1: show a linear model fails on concentric circles and a neural net succeeds. Inspect the architecture. Explain why the non-linear activation is essential.

**2. Measure the gap.** Reproduce §71.3. Confirm the neural net's advantage on non-linear data. Then try linearly-separable data and show the linear model matches the net. Explain when non-linearity helps.

**3. Trees versus neural on tables.** Compare a tree ensemble (Chapter 69) and a neural net on a *tabular* dataset. Show the tree matches or beats the net with less effort. Explain why trees win on tables.

**4. Overfitting a neural net.** Train a large neural net on small data and show it overfits (high train, low test). Add regularization/early stopping and show improvement. Explain the high-capacity overfitting risk.

**5. The design question.** Neural networks are universal approximators but data/compute/tuning-hungry and opaque. Argue when to use them (unstructured data, §71.2) versus trees (tables), using §71.3, and why "match the model family to the data's structure" is the right principle. Why is deep learning not a universal default?

---

## 71.7 Summary and cross-references

- **Linear models** draw straight boundaries and fail on non-linearly-separable data. **Neural networks** stack layers of neurons with **non-linear activations**, learning **arbitrary non-linear boundaries** (universal approximation). The activation is essential (without it, stacked linear layers collapse to linear).
- **Measured:** on concentric circles (not linearly separable), a linear model scores **0.44** (near chance) and a 2-hidden-layer neural net scores **0.99**, the value of non-linearity.
- **Neural networks are powerful but costly:** data-hungry, compute-intensive, tuning-heavy, opaque, and scale-sensitive. **Trees usually win on tabular data** (Chapter 69); **neural networks win on unstructured data** (images via CNNs, text/sequences via transformers, audio).
- **The rule:** match the model family to the data's structure, neural networks for unstructured/complex-non-linear data with enough data and compute; tree ensembles for tables. Neural networks are a frontier tool for the right problem, not a universal default.
- **Edges:** scale features; regularize against overfitting (high capacity); tune extensively (CV); interpretability is limited; sklearn's MLP is pedagogical (real DL uses PyTorch/TensorFlow); evaluate as rigorously as any model (Chapters 65-70).

**Cross-references.** Linear models / tree ensembles → Chapter 69. Feature scaling → Chapter 66. Overfitting / evaluation methodology → Chapters 65-70. Bias-variance → Chapter 69. CNNs, transformers, deep learning, PyTorch, representation learning → the frontier of Deep W / Book III. Autograd / numeric foundations → Deep T.
