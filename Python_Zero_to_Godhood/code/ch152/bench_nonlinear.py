"""Benchmark 152.1 - neural networks learn non-linear boundaries a linear model cannot.

A quality measurement. On concentric-circle data (one class inside the other, not
linearly separable), a linear model (logistic regression) is compared with a small
neural network. The linear model is near chance; the neural net, via hidden layers with
non-linear activations, learns the circular boundary and classifies almost perfectly.

See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sklearn.datasets import make_circles  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.neural_network import MLPClassifier  # noqa: E402

from _harness.bench import provenance  # noqa: E402


def main():
    print("=== 152.1  non-linearly-separable data: linear model vs neural net ===")
    print(provenance())
    print()

    X, y = make_circles(n_samples=500, noise=0.1, factor=0.5, random_state=0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

    linear = LogisticRegression().fit(X_train, y_train)
    nn = MLPClassifier(hidden_layer_sizes=(16, 16), max_iter=2000, random_state=0).fit(X_train, y_train)

    print(f"  linear model (logistic reg) : test accuracy {linear.score(X_test, y_test):.3f}")
    print(f"  neural net (2x16 hidden)    : test accuracy {nn.score(X_test, y_test):.3f}")

    print()
    print("Reading this. The classes are concentric circles, no straight line")
    print("separates them, so the linear model is near chance (0.44). A neural network")
    print("with hidden layers and non-linear activations learns the CURVED boundary")
    print("and classifies almost perfectly (0.99). This is what neural nets add over")
    print("linear models and, for complex patterns, over trees: they approximate")
    print("ARBITRARY functions (the universal approximation theorem), composing simple")
    print("non-linear units into any shape. The cost is real: they need more data,")
    print("more compute, careful tuning (architecture, learning rate, regularization),")
    print("and they are opaque (no feature importances). So the guidance holds: for")
    print("TABULAR data, tree ensembles (Chapter 69) usually match or beat neural nets")
    print("with far less effort; neural networks earn their complexity on UNSTRUCTURED")
    print("data, images (CNNs), text and sequences (transformers), audio, where the")
    print("structure suits them and they are the state of the art. Deep learning is a")
    print("frontier tool for the right problem, not a default for every table.")


if __name__ == "__main__":
    main()
