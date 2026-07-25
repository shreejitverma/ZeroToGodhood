# Chapter 70: Backtesting and Look-Ahead Bias

This chapter is where machine learning meets **quantitative finance**, and it is about the one error that destroys more trading strategies than any other: **look-ahead bias**, using information from the future to predict the past.
A model evaluated with future information leaking in looks *brilliant* in testing and *loses money* live, and the leakage is often invisible, so this is the most important, and most dangerous, topic in quant ML.

The trap hides inside a tool you have already learned.
Standard k-fold cross-validation (Chapter 68) *shuffles* the data, so test points end up *interspersed* with training points, and on a time series, where nearby points are correlated, a model trains on a test point's *neighbors* (data from the same time it is trying to predict) and simply *interpolates*.
It has effectively *seen the future*.
The measurement is devastating: on an autocorrelated series, shuffled CV reports a near-perfect **R2 = 0.98**, and the honest time-respecting split reveals **R2 = -4.94**, the model has *no real predictive power* on genuinely unseen future data.
The shuffled score was not optimistic; it was *fiction*.

The fix is **time-respecting validation**: `TimeSeriesSplit` does **walk-forward** evaluation, each fold trains *only* on data *before* the test period, exactly as a live strategy runs (you never have tomorrow's data today).
The chapter's rule is absolute: **validate time series only with walk-forward splits, never a shuffled split, and audit every feature for future information.**

**This is Deep W's quant chapter.**
It combines time series (Chapter 61), cross-validation (Chapter 68), and the leakage principle (Chapter 66) into the discipline that makes a backtest *honest*, the foundation of every credible trading strategy in **Book III**.

## Section index

- **70.1** Walk-forward validation
- **70.2** Look-ahead bias and the sources of leakage
- **70.3** Measurement: the leakage that fakes a great backtest
- **70.4** Edges and failure modes
- **70.5** Connections
- **70.6** Exercises
- **70.7** Summary and cross-references

Listings live under `code/ch151/` and are re-executed by `make verify` on both verification interpreters.

---

## 70.1 Walk-forward validation

```python
# code/ch151/l01_backtest.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- TimeSeriesSplit: walk-forward, train grows, test moves forward ---
  fold 1: train [0..19] (20), test [20..35] (16)
  fold 2: train [0..35] (36), test [36..51] (16)
  fold 3: train [0..51] (52), test [52..67] (16)
  fold 4: train [0..67] (68), test [68..83] (16)
  fold 5: train [0..83] (84), test [84..99] (16)
--- the invariant: every training point is BEFORE every test point ---
  no future data ever leaks into training : True
--- contrast: standard shuffled k-fold VIOLATES this ---
  shuffled k-fold puts test points among train points (future in train),
  which on a time series is LOOK-AHEAD BIAS: a fantasy backtest
--- a real backtest mimics live trading: decide using only PAST data ---
  at each step, train on history up to t, predict t+1, never peek ahead
--- the rule ---
  validate time series with walk-forward (TimeSeriesSplit): train on the
  past, test on the future; a shuffled split leaks the future and lies
```

**`TimeSeriesSplit` does walk-forward validation.**
Look at the folds: each trains on `[0..k]` and tests on the *next* block `[k+1..]`, and the training window *grows* while the test block *moves forward*.
Fold 1 trains on the first 20 points and tests on 20-35; fold 5 trains on 0-83 and tests on 84-99.
The **invariant** is the whole point: **every training point is before every test point** (the output confirms it), so the model is *never* trained on data from the test period or later. No future leaks into training.

This mirrors *reality*.
A live trading strategy, at each moment `t`, has only the *history* up to `t` and must decide about `t+1` using *only* that history, it cannot use tomorrow's prices to trade today.
Walk-forward validation *simulates* exactly this: train on the past, predict the future, roll forward.
So a walk-forward backtest's performance is an *honest* estimate of how the strategy would have done *live*, because it respects the same information constraint (only past data available) that live trading imposes.

**Shuffled k-fold violates this fatally.**
Standard k-fold *shuffles*, scattering test points among training points, so a test point at time `t` may have *neighbors* at `t-1` and `t+1` in the *training* set.
On a time series (where `t+1` is highly correlated with `t`), the model learns from `t+1` (the future) to predict `t`, look-ahead bias.
The result is a *fantasy* backtest: a score that could never be achieved live, because live you would not have `t+1` when predicting `t`.

So the structure of the split *is* the correctness of the backtest: walk-forward (past -> future) is honest; shuffled (future mixed into past) is fiction.

---

## 70.2 Look-ahead bias and the sources of leakage

Look-ahead bias is subtler and more pervasive than just the shuffled split, and finding it is the core skill of quant validation.

**Look-ahead bias** is any use of information not available at the *decision time*.
It always *inflates* backtest performance (the model "knows" things it would not know live), and it always *fails* in production (the future information is not there). The gap between a leaky backtest and live results has ended countless strategies.

**Sources of leakage (all must be audited):**

- **Shuffled/random CV on time series.** §70.1, §70.3. The split itself leaks. Use walk-forward.
- **Feature leakage:** a feature computed using future data. Examples: a "20-day moving average" *centered* on the current point (uses 10 future days); a normalization using the *whole* series' mean/std (uses future statistics, Chapter 66); a label derived from data that includes the prediction target's future.
- **Survivorship bias:** backtesting on only the assets that *survived* to today (delisted/bankrupt ones removed), which excludes exactly the failures a real strategy would have hit.
- **Point-in-time data:** using *revised* data (later corrections, restatements) that was not available at the original time. Earnings, economic figures, and index constituents are revised; a backtest must use what was *known then*, not the corrected version.
- **Fill/execution assumptions:** assuming you could trade at a price (the close, the exact signal price) that was not actually available at decision time.

**The discipline:**

- **Walk-forward validation** (`TimeSeriesSplit`, or expanding/rolling windows), never shuffled.
- **Compute every feature and normalization using only past data**, within the training window (pipelines inside the walk-forward split, Chapter 66).
- **Use point-in-time data** (what was known then), not revised.
- **Include delisted/failed assets** (no survivorship bias).
- **Model realistic execution** (transaction costs, slippage, achievable fills), a strategy profitable before costs is often unprofitable after.

The rule: **treat every step of a backtest as if it were running live at each historical moment, with access only to what was known then**, and audit relentlessly for any future information. This is the difference between a backtest that predicts live performance and one that is an elaborate way to lie to yourself.

---

## 70.3 Measurement: the leakage that fakes a great backtest

**Methodology.** `code/ch151/bench_lookahead.py`.
A correctness measurement. On an autocorrelated time series (a random walk), a `RandomForestRegressor` evaluated by standard shuffled k-fold versus `TimeSeriesSplit` (walk-forward).
CPython 3.13.5, scikit-learn 1.6.1.

| validation | R2 |
|---|---|
| shuffled k-fold (leaks) | **0.977** |
| `TimeSeriesSplit` (honest) | **-4.940** |

The two numbers are the entire lesson (identical on both interpreters).
Shuffled CV reports **R2 = 0.98**, near-perfect, and it is *pure leakage*.
The honest walk-forward split reports **R2 = -4.94**, deeply negative (worse than predicting the mean), the model has *no* real predictive power on unseen future data.

The mechanism is §70.1 quantified.
On this autocorrelated series (a random walk, where each value is close to the previous), shuffling scatters test points among training points, so for each test point the model has trained on its *immediate temporal neighbors*, values from essentially the *same time* it is predicting.
It simply *interpolates* between known nearby points, which is easy and gives a great score, but it is *cheating*: live, when predicting time `t`, you do *not* have `t-1` and `t+1` in your training set (you only have the past).
The walk-forward split enforces the real constraint, and the model, deprived of the future it was secretly using, is revealed to be worthless (R2 -4.94).

The consequence is the starkest correctness lesson in Deep W, and one of the starkest in the book.
**A shuffled backtest on time-series data does not overestimate performance; it fabricates it.**
The 0.98 was never real, it was the model reading answers it would not have live, and a strategy deployed on the strength of that 0.98 would lose money immediately (its true skill is negative).
This is why look-ahead bias is the *deadliest* error in quant: unlike a merely optimistic estimate, it can make a *worthless* (or harmful) strategy look *excellent*, and the failure surfaces only with real money.
It completes Deep W's evaluation methodology (Chapters 65-70) with its most consequential rule: for time series, honest evaluation *requires* time-respecting validation, and the whole apparatus, held-out data, no leakage, right metric, cross-validation, *walk-forward*, exists to ensure the backtest measures *real, live-achievable* skill, not a fantasy.
**Book III**'s strategies live or die on this: every signal is validated walk-forward, every feature audited for future information, every backtest run with point-in-time data, survivorship-bias-free universes, and realistic costs, because in quant finance the backtest is the *only* evidence before capital is risked, and a leaky backtest is worse than no backtest, it is *false confidence* that directly causes losses. The order-book system's strategy research uses strictly time-respecting walk-forward validation, treats any hint of look-ahead bias as a critical bug, and discounts backtest results for costs and slippage, the §70.2 discipline as the gate between research and live capital, because the §70.3 gap (0.98 fantasy versus -4.94 reality) is, in production, the gap between a profitable system and a blown-up account.

---

## 70.4 Edges and failure modes

**Never use shuffled CV on time series.** §70.1, §70.3.
It leaks the future via correlated neighbors, fabricating performance. Use `TimeSeriesSplit` / walk-forward. This is the most important rule in the chapter.

**Audit every feature for future information.** §70.2.
Centered moving averages, whole-series normalization, future-derived labels, all leak. Compute features and normalization using only past data (pipelines inside the walk-forward split).

**Use point-in-time data.** §70.2.
Revised/restated data (earnings, economic figures, index membership) was not available originally. Backtest with what was known *then*, not the corrected version, or the backtest is leaky.

**Avoid survivorship bias.** §70.2.
Backtesting only on surviving assets excludes the failures a real strategy would hit. Include delisted/bankrupt names.

**Model realistic execution and costs.** §70.2.
Assuming perfect fills at the signal price ignores slippage, spread, and transaction costs. Many "profitable" backtests are unprofitable after costs. Subtract realistic costs.

**Multiple-testing / overfitting the backtest.**
Trying many strategies/features and keeping the best backtest is overfitting to the historical data (a form of the Chapter 65 test-set leakage). The more strategies you try, the more likely one looks good by chance. Use out-of-sample holdout, correct for multiple testing, and be skeptical of a strategy found by extensive search.

**A negative or near-zero honest score means no edge.** §70.3.
If walk-forward validation shows no skill, there is no strategy, do not deploy it hoping the backtest was too pessimistic. The honest score is the estimate.

**Regime changes limit backtest validity.**
A strategy that worked in one market regime may fail in another; even an honest backtest on past data does not guarantee future performance if the market changes. Backtests estimate, they do not promise.

---

## 70.5 Connections

**Backward.**
Walk-forward is `TimeSeriesSplit`, the time-respecting variant of cross-validation (Chapter 68). It enforces the time-order of time series (Chapter 61). Feature/normalization leakage is Chapter 66 (fit on past/train only) applied to time. The "honest evaluation" theme is Chapters 65-69. The negative R2 is the regression-metric of Chapter 67's family.

**Forward.**
Expanding versus rolling windows, purged/embargoed cross-validation (removing points near the test boundary to prevent subtler leakage), realistic backtesting frameworks (with costs, slippage, position sizing), and strategy evaluation metrics (Sharpe ratio, drawdown) are the rest of **Deep W** / quant. Multiple-testing correction and combinatorial purged CV are advanced quant-validation topics.

**Across books.**
Look-ahead-bias-free backtesting is the *central discipline* of **Book III**'s strategy research, because the backtest is the sole evidence before risking capital, and a leaky one causes direct losses. The order-book system validates every signal with strict walk-forward (or purged) cross-validation, audits every feature for future information, uses point-in-time survivorship-bias-free data, and applies realistic transaction costs, so a strategy reaches live trading only if its *honest*, costed, time-respecting backtest shows a real edge. The §70.3 measurement, a fantasy 0.98 versus a real -4.94, is the reason: in a domain where the backtest drives a capital decision, the integrity of the validation *is* the integrity of the decision, and look-ahead bias is the failure that turns a research result into a real-money loss. Deep W's evaluation methodology culminates here, at the discipline that makes a quant strategy trustworthy.

---

## 70.6 Exercises

**1. Walk-forward structure.** Reproduce §70.1: use `TimeSeriesSplit` and confirm each fold trains only on data before its test period (the invariant). Contrast with a shuffled split. Explain how walk-forward mirrors live trading.

**2. Measure the leakage.** Reproduce §70.3. Confirm shuffled CV fakes a great score while walk-forward reveals no skill. Explain the interpolation-between-neighbors mechanism and why the honest score is negative.

**3. Feature leakage.** Build a feature with a centered moving average (uses future) and one with a trailing average (uses only past), and show the centered one inflates a backtest. Fix it. Explain the leakage.

**4. Costs matter.** Take a strategy with a small positive walk-forward return and subtract realistic transaction costs. Show it may become unprofitable. Explain why costs are part of an honest backtest.

**5. The design question.** Look-ahead bias fabricates backtest performance (§70.3), unlike a merely optimistic estimate. Argue why it is the deadliest error in quant, why walk-forward validation and feature auditing are mandatory (not optional), and how this completes the evaluation methodology (Chapters 65-70). Why is a leaky backtest worse than no backtest?

---

## 70.7 Summary and cross-references

- **Look-ahead bias** (using future information to predict the past) is the deadliest error in quant ML: it **fabricates** backtest performance and fails live. It is often invisible.
- **Standard shuffled k-fold leaks the future on time series:** test points interspersed with train let the model interpolate between correlated neighbors it should not see. **Measured:** shuffled CV reports **R2 = 0.98** (fantasy); honest **`TimeSeriesSplit`** reveals **R2 = -4.94** (no real skill).
- **Walk-forward validation** (`TimeSeriesSplit`) trains *only* on data before each test period, mirroring live trading (only past data available). **Validate time series only with time-respecting splits, never shuffled.**
- **Audit every source of leakage:** feature leakage (centered averages, whole-series normalization, future labels), survivorship bias, revised (non-point-in-time) data, unrealistic fills. Use point-in-time data, include failed assets, model realistic costs.
- **This completes Deep W's evaluation methodology (Chapters 65-70):** held-out, no leakage, right metric, cross-validation, and **walk-forward for time series**, all ensuring the backtest measures real, live-achievable skill.
- **Edges:** a negative honest score means no edge (do not deploy); costs can erase a small edge; multiple-testing overfits the backtest; regime changes limit validity.

**Cross-references.** `TimeSeriesSplit` / cross-validation → Chapter 68. Time-order of time series → Chapter 61. Feature/normalization leakage → Chapter 66. Honest evaluation → Chapters 65-69. Regression metrics → Chapter 67. Purged CV, backtesting frameworks, Sharpe/drawdown, multiple-testing → the rest of Deep W. Book III strategy research → Deep W / Book III.
