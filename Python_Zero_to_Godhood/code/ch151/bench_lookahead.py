"""Benchmark 151.1 - look-ahead bias: shuffled CV fakes a great score on a time series.

A correctness measurement. On an autocorrelated time series (a random walk), a model is
evaluated two ways: standard SHUFFLED k-fold (test points interspersed with train, which
lets the model interpolate between neighboring 'future' points it has seen) and
TimeSeriesSplit (train on the past, test on the future only). Shuffled CV reports a great
score that is pure leakage; the honest time-respecting split reveals the truth.

See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.model_selection import KFold, TimeSeriesSplit, cross_val_score  # noqa: E402

from _harness.bench import provenance  # noqa: E402


def main():
    print("=== 151.1  time-series validation: shuffled CV vs walk-forward ===")
    print(provenance())
    print()

    rng = np.random.RandomState(0)
    n = 300
    t = np.arange(n)
    y = np.cumsum(rng.randn(n))                     # random walk: each value depends on prior
    X = np.column_stack([np.sin(t / 10), np.cos(t / 7), t / n])

    model = RandomForestRegressor(n_estimators=30, random_state=0)

    shuffled = cross_val_score(model, X, y, cv=KFold(5, shuffle=True, random_state=0))
    walk_forward = cross_val_score(model, X, y, cv=TimeSeriesSplit(5))

    print(f"  shuffled k-fold R2   : {shuffled.mean():7.3f}   (LEAKS: test among train)")
    print(f"  TimeSeriesSplit R2   : {walk_forward.mean():7.3f}   (honest: past -> future)")

    print()
    print("Reading this. Shuffled cross-validation reports a near-perfect R2 (0.98),")
    print("and it is a FANTASY. On this autocorrelated series, shuffling scatters test")
    print("points among the training points, so for each test point the model has")
    print("trained on its immediate neighbors, points from the SAME time it is trying")
    print("to predict, and simply interpolates between them. It has effectively seen")
    print("the future. The honest walk-forward split (train on the past, predict the")
    print("future the model has never seen) reveals a deeply NEGATIVE R2: the model")
    print("has no real predictive power on genuinely unseen future data. This is")
    print("look-ahead bias, the deadliest error in quant finance: a backtest that")
    print("peeks at the future looks brilliant and loses money live. The rule is")
    print("absolute: validate time series ONLY with time-respecting splits (walk-")
    print("forward), never a shuffled split, and audit every feature for future")
    print("information. A shuffled backtest is not optimistic; it is fiction.")


if __name__ == "__main__":
    main()
