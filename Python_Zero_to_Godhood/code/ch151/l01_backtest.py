"""Listing 151.1 - backtesting and look-ahead bias: validate time series on the FUTURE.

The deadliest error in quantitative finance (and any time-series ML) is LOOK-AHEAD BIAS:
using information from the future to predict the past. Standard k-fold cross-validation
(Chapter 68) SHUFFLES the data, so test points end up interspersed with training points,
and on an autocorrelated series the model effectively interpolates between neighbors it
has 'seen', a fake, inflated score (the benchmark: R2 0.98 that is pure leakage). The fix
is TIME-RESPECTING validation: TimeSeriesSplit does WALK-FORWARD, each fold trains ONLY on
data BEFORE the test period, exactly how a real strategy runs (you never have tomorrow's
data today). This listing shows the walk-forward structure, deterministically.
"""

import numpy as np
from sklearn.model_selection import TimeSeriesSplit


def main() -> None:
    n = 100
    indices = np.arange(n)                          # 100 time-ordered samples

    print("--- TimeSeriesSplit: walk-forward, train grows, test moves forward ---")
    tscv = TimeSeriesSplit(n_splits=5)
    fold = 0
    all_train_before_test = True
    for train_idx, test_idx in tscv.split(indices):
        fold += 1
        train_end = int(train_idx.max())
        test_start = int(test_idx.min())
        if train_end >= test_start:
            all_train_before_test = False
        print(f"  fold {fold}: train [0..{train_end}] ({len(train_idx)}), test [{test_start}..{int(test_idx.max())}] ({len(test_idx)})")

    print("--- the invariant: every training point is BEFORE every test point ---")
    print(f"  no future data ever leaks into training : {all_train_before_test}")

    print("--- contrast: standard shuffled k-fold VIOLATES this ---")
    print(f"  shuffled k-fold puts test points among train points (future in train),")
    print(f"  which on a time series is LOOK-AHEAD BIAS: a fantasy backtest")

    print("--- a real backtest mimics live trading: decide using only PAST data ---")
    print(f"  at each step, train on history up to t, predict t+1, never peek ahead")

    print("--- the rule ---")
    print(f"  validate time series with walk-forward (TimeSeriesSplit): train on the")
    print(f"  past, test on the future; a shuffled split leaks the future and lies")


if __name__ == "__main__":
    main()
