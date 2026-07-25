"""Listing 152.1 - neural networks: learning non-linear patterns a line cannot.

A LINEAR model (logistic/linear regression) draws a straight decision boundary, so it
fails on data that is not linearly separable. A NEURAL NETWORK stacks layers of neurons
(each a weighted sum followed by a non-linear activation), and with a HIDDEN LAYER it can
learn ARBITRARY non-linear boundaries, this is the universal approximation property. On
concentric circles (one class inside the other), no line separates the classes, but a
small neural net learns the circular boundary. The cost: neural nets need more data,
compute, and tuning, and are less interpretable than trees (Chapter 69). This listing
shows a linear model failing and a neural net succeeding on non-linear data.
"""

from sklearn.datasets import make_circles
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier


def main() -> None:
    # concentric circles: one class inside the other, NOT linearly separable
    X, y = make_circles(n_samples=500, noise=0.1, factor=0.5, random_state=0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

    print("--- a LINEAR model cannot separate non-linear (circular) classes ---")
    linear = LogisticRegression().fit(X_train, y_train)
    print(f"  logistic regression test accuracy : {round(linear.score(X_test, y_test), 3)}")
    print(f"  near chance: a straight line cannot enclose the inner circle")

    print("--- a NEURAL NET with hidden layers learns the non-linear boundary ---")
    nn = MLPClassifier(hidden_layer_sizes=(16, 16), max_iter=2000, random_state=0)
    nn.fit(X_train, y_train)
    print(f"  MLP (2 hidden layers of 16) test accuracy : {round(nn.score(X_test, y_test), 3)}")
    print(f"  it learned the circular decision boundary")

    print("--- the architecture: layers of neurons with non-linear activations ---")
    print(f"  hidden layers   : {nn.hidden_layer_sizes}")
    print(f"  activation      : {nn.activation}   (the non-linearity that enables curves)")
    print(f"  the net beats the linear model by : {round(nn.score(X_test, y_test) - linear.score(X_test, y_test), 3)}")

    print("--- the trade-off ---")
    print(f"  neural nets learn ANY function (universal approximation) but need more")
    print(f"  data, compute, and tuning, and are less interpretable than tree ensembles")

    print("--- the rule ---")
    print(f"  use neural nets for complex non-linear patterns and unstructured data")
    print(f"  (images, text, sequences); for tabular data, trees (Chapter 69) usually win")


if __name__ == "__main__":
    main()
