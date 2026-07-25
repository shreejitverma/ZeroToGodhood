# Chapter 61: Time Series

Most real data is a **time series**: market ticks, server logs, sensor readings, metrics, transactions, each row stamped with *when* it happened.
Time is not just another column; it is the axis along which the data is ordered, bucketed, and analyzed, and pandas gives it first-class support built on a **datetime index**.
This chapter covers the three operations that make time-series work fast and clean: building datetime indexes, **resampling** (bucketing rows into time intervals and aggregating), and the vectorized **`.dt` accessor** (extracting components like year, month, weekday over a whole column).

The unifying insight, and the one the measurement drives home, is that **`resample` is a time-based `groupby`** (Chapter 58): it splits rows into time buckets, applies an aggregation, and combines, all in C over the datetime index.
So the cardinal rule of Deep U applies once more, and sharply: never loop over timestamps.
A manual per-timestamp loop that floors each timestamp to its bucket and accumulates is measured at **400-900x** slower than `resample`, the same order of magnitude as the `iterrows` disaster of Chapter 57, because it pays Python-level datetime operations per row.

**This is Deep U's time-series chapter.**
It is `groupby` (Chapter 58) specialized to time, built on the DataFrame (Chapter 57), and essential to **Book III**, whose data, market and otherwise, is overwhelmingly time-stamped.

## Section index

- **61.1** Datetime index, resample, and `.dt`
- **61.2** Thinking in time buckets and vectorized components
- **61.3** Measurement: `resample` versus a loop
- **61.4** Edges and failure modes
- **61.5** Connections
- **61.6** Exercises
- **61.7** Summary and cross-references

Listings live under `code/ch142/` and are re-executed by `make verify` on both verification interpreters.

---

## 61.1 Datetime index, resample, and `.dt`

```python
# code/ch142/l01_timeseries.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a datetime index over a fixed date range ---
  number of days : 6
  first / last   : 2026-01-01 / 2026-01-06
--- resample: a TIME-based groupby (bucket + aggregate) ---
  2-day bucket sums : [3, 7, 11]   (1+2, 3+4, 5+6)
  number of buckets : 3
--- the .dt accessor: vectorized datetime components over a column ---
  dt.year    : [2026, 2026, 2026]
  dt.month   : [1, 6, 12]
  dt.day     : [15, 20, 31]
  dt.day_name (first): 'Thursday'
--- time arithmetic and selection are vectorized ---
  ts + 7 days (first) : 2026-01-22
--- the rule ---
  a datetime index enables resample (time groupby) and vectorized .dt
  component/arithmetic operations; never loop over timestamps
```

**A datetime index** turns a Series/DataFrame into a time series.
`pd.date_range("2026-01-01", periods=6, freq="D")` builds six daily timestamps; `pd.to_datetime([...])` parses strings into timestamps.
With a datetime index, pandas knows the rows are ordered in time and unlocks the time-aware operations.

**`resample` is a time-based groupby.**
`series.resample("2D").sum()` buckets the rows into 2-day intervals and sums each, `[1+2, 3+4, 5+6]` = `[3, 7, 11]`.
This is split-apply-combine (Chapter 58) with *time intervals* as the grouping key: the frequency string (`"D"` day, `"h"` hour, `"2D"` two days, `"ME"` month-end, `"W"` week) defines the buckets, and the aggregation (`sum`, `mean`, `ohlc` for financial bars, etc.) reduces each.
"Hourly totals from per-second data", "daily averages from hourly readings", "monthly counts", all are one `resample`.

**The `.dt` accessor** extracts datetime components, vectorized over a whole column.
`df["ts"].dt.year`, `.dt.month`, `.dt.day`, `.dt.day_name()`, `.dt.weekday`, `.dt.hour`, each returns a whole column of the component, in C, no loop.
`2026-01-15` is a `Thursday` (the calendar is computed vectorized).
This is how you derive time-based features or grouping keys ("group by weekday", "filter to business hours") without iterating.

**Time arithmetic is vectorized** too: `df["ts"] + pd.Timedelta(days=7)` shifts the whole column by a week.
Comparisons, differences (`ts2 - ts1` gives a `Timedelta` column), and range selection (`df["2026-01":"2026-06"]`) all operate on whole columns.

So the datetime index makes time a first-class, vectorized dimension: `resample` for time bucketing, `.dt` for components, and vectorized arithmetic/selection for the rest.

---

## 61.2 Thinking in time buckets and vectorized components

Time-series work, done well, is expressed as bucketing and vectorized component operations, never as timestamp loops.

**Resample for any time-bucket aggregation.**
The mental move is the same as `groupby` (Chapter 58): if the question is "X per time-interval", it is a `resample`. "Sales per day", "errors per hour", "average latency per minute", "OHLC bars per 5 minutes", the interval is the frequency, the aggregation is the reducer. `resample("5min").agg(["open", "high", "low", "close"])`-style aggregations build financial bars from ticks; `resample("D").mean()` builds daily averages. Downsampling (fine to coarse) aggregates; upsampling (coarse to fine) interpolates or forward-fills.

**Use `.dt` for time-derived features and keys.**
To group by or filter on a time component, extract it vectorized: `df.groupby(df["ts"].dt.hour)` groups by hour of day; `df[df["ts"].dt.weekday < 5]` filters to weekdays; `df["month"] = df["ts"].dt.month` adds a feature column. Never loop to compute `.year` per row.

**Related time-series operations, all vectorized:**

- **Rolling windows** (`.rolling(window).mean()`): moving averages, rolling sums, over a sliding window, in C.
- **Shifting** (`.shift(1)`): lag/lead, "compare each row to the previous", the basis of returns and diffs (`.diff()`).
- **Range selection** (`df["2026-Q1"]`): slice by time labels.
- **Timezone handling** (`.dt.tz_localize`, `.tz_convert`): correct cross-timezone alignment.
- **Frequency conversion / alignment** (`.asfreq`, `merge_asof` for nearest-time joins).

**The anti-pattern to avoid:** a `for` loop over timestamps.
Flooring each timestamp, computing a component per row, or comparing consecutive rows in a Python loop is the timestamp version of `iterrows` (Chapter 57), and just as catastrophically slow (§61.3).
Every timestamp operation has a vectorized form, `resample` for bucketing, `.dt` for components, `.shift`/`.diff` for row-relative operations, `.rolling` for windows, and the vectorized form is both far faster and far clearer.

The rule: **express time-series computation as `resample`, `.dt`, `.rolling`, and `.shift`, never as a timestamp loop.** This is Chapter 57's "columns not rows" and Chapter 58's split-apply-combine, applied to the time axis.

---

## 61.3 Measurement: `resample` versus a loop

**Methodology.** `code/ch142/bench_resample.py`.
Hourly sums from 500,000 per-second values, computed with `resample("h").sum()` versus a Python loop that floors each timestamp to its hour and accumulates into a dict.
CPython 3.13.5, pandas 2.2.3, Apple M3 Pro, macOS 27.0, arm64.

| hourly sums from 500,000 per-second rows | time | vs resample |
|---|---|---|
| `resample("h").sum()` | ~12 ms | 1x |
| per-timestamp Python loop | ~4,800 ms | **~403x slower** |

`resample` is **~403x** faster than the manual loop (900x on 3.14.6).
`resample` buckets the datetime index and aggregates in C over contiguous arrays.
The loop iterates 500,000 times in the interpreter, and, worse, calls a Python-level `floor("h")` on *each* timestamp, an expensive per-row operation, then accumulates into a dict.

This is the time-axis form of Deep U's cardinal rule, and the number, hundreds of times, is the same order as `iterrows` (Chapter 57, over 1,000x) and `groupby`-vs-loop (Chapter 58).
The pattern is identical across all of Deep U: the data is columnar and typed (here, a typed datetime index and a typed value array), the vectorized operation processes it in C, and a Python loop over rows/timestamps throws that away for a several-hundred-x penalty.

So the rule stands unqualified for time series: **use `resample` for time bucketing, `.dt` for components, `.rolling`/`.shift` for windowed and row-relative operations, never a timestamp loop.**
The deeper lesson, closing the arc of Chapters 57-61, is that pandas is fast *only when used vectorially*, on columns, on groups, on time buckets, and the recurring mistake, in every one of these chapters, is the same: falling back to a Python loop (`iterrows`, a manual group accumulation, a timestamp loop) and paying hundreds to thousands of times the cost.
Time is just another axis to vectorize over, and `resample` is `groupby` for it.
**Book III**'s time-stamped data, market bars, event streams, metric histories, is processed exactly this way, as `resample` aggregations and vectorized `.dt`/`.rolling` operations, so a computation over years of tick data is seconds of C work, not hours of Python looping.

---

## 61.4 Edges and failure modes

**Never loop over timestamps.** §61.2, §61.3.
Hundreds of times slower than `resample`/`.dt`/`.rolling`. Every timestamp operation has a vectorized form.

**Resample needs a datetime index (or `on=`).**
`resample` operates on the datetime index; if your timestamps are a column, set it as the index (`set_index`) or pass `on="ts"`. Resampling a non-datetime index errors or misbehaves.

**Frequency strings and their meanings.**
`"D"` (day), `"h"` (hour), `"min"`, `"s"`, `"W"` (week), `"ME"`/`"MS"` (month end/start), `"QE"`, `"YE"`, and multiples (`"5min"`). Some aliases changed across pandas versions (`"M"` -> `"ME"`, `"H"` -> `"h"` in 2.2), a source of version-specific breakage. Use the current aliases.

**Timezones are a correctness minefield.**
Naive timestamps (no timezone) silently assume a single zone; mixing naive and aware timestamps errors. Cross-timezone data must be localized (`tz_localize`) and converted (`tz_convert`) correctly, or comparisons and resampling are wrong. DST transitions add non-existent and ambiguous times. Handle timezones explicitly for any cross-zone data.

**Upsampling creates missing values.**
Resampling to a *finer* frequency (hourly to per-minute) creates rows with no data (`NaN`); you must `ffill`, `interpolate`, or otherwise fill them. Downsampling aggregates; upsampling interpolates.

**Parsing dates is slow and ambiguous.**
`pd.to_datetime` on strings is slow for large data; pass `format=` to speed it and avoid ambiguity (`01/02/2026` is Jan 2 or Feb 1 depending on locale). Store dates as proper datetime dtype (or Parquet, Chapter 60) to avoid re-parsing.

**`.dt` only works on datetime Series.**
The `.dt` accessor requires a datetime dtype; on an `object` column of date strings it fails. Convert with `pd.to_datetime` first.

**Rolling windows have edge effects.**
The first `window-1` rows of a `.rolling(window)` are `NaN` (not enough history). Account for the warmup, or use `min_periods=`.

---

## 61.5 Connections

**Backward.**
`resample` is `groupby` (Chapter 58) with time-interval keys. It operates on the DataFrame's columns (Chapter 57), vectorized (Chapter 96). Timezone/encoding correctness touches Deep D. Storing dates typed (avoiding re-parsing) is Chapter 60 (Parquet preserves datetime dtype).

**Forward.**
Rolling/expanding windows, `merge_asof` (nearest-time joins, essential for aligning ticks to reference), timezone handling in depth, and financial time-series patterns (returns, bars, resampling to OHLC) are the rest of **Deep U** and **Deep W** (quant). Distributed time-series processing (Dask, Spark) scales it.

**Across books.**
Time series is the dominant data shape in **Book III**'s domain: market data is per-tick, resampled to bars; features are time-windowed; labels are forward-looking returns computed with `.shift`. The order-book system builds OHLCV bars from ticks with `resample`, computes rolling indicators (moving averages, volatility) with `.rolling`, aligns data across sources with `merge_asof`, and derives time features (hour, weekday, session) with `.dt`, all vectorized, so processing years of tick data is a pipeline of C operations rather than a timestamp loop, the §61.3 rule as the architecture of the market-data path. Deep U's arc, DataFrame, groupby, merge, columnar IO, time series, is the complete grammar of that pipeline, and "vectorize, never loop" is its single governing rule.

---

## 61.6 Exercises

**1. Datetime index and resample.** Reproduce §61.1: build a datetime-indexed Series, resample to a coarser frequency and aggregate, and extract components with `.dt`. Explain why `resample` is a time-based groupby.

**2. Measure it.** Reproduce §61.3. Confirm `resample` is hundreds of times faster than the timestamp loop. Relate the number to `iterrows` (Chapter 57) and `groupby`-vs-loop (Chapter 58), the same pattern.

**3. Vectorize a timestamp loop.** Take a loop that computes returns (`(price[i] - price[i-1]) / price[i-1]`) and rewrite it with `.shift`/`.diff` vectorized. Measure both. Explain the transformation.

**4. The timezone trap.** Create naive and timezone-aware timestamps and show a comparison/resample that goes wrong when they are mixed, then fix it with `tz_localize`/`tz_convert`. Explain why timezones require explicit handling.

**5. The design question.** `resample` is `groupby` for time; `.dt`, `.rolling`, and `.shift` vectorize component, window, and row-relative operations. Argue why the "vectorize, never loop over timestamps" rule holds for time series exactly as for rows (§61.3), and how it completes the Deep U arc (Chapters 57-61). Why is time just another axis to vectorize over?

---

## 61.7 Summary and cross-references

- A **datetime index** makes a Series/DataFrame a time series, unlocking time-aware operations. Build with `pd.date_range` / `pd.to_datetime`.
- **`resample` is a time-based `groupby`** (Chapter 58): bucket rows into time intervals (frequency strings: `"D"`, `"h"`, `"2D"`, `"ME"`, ...) and aggregate each. The **`.dt` accessor** extracts components (`year`, `month`, `weekday`, ...) vectorized; time arithmetic (`+ Timedelta`), `.shift`/`.diff`, and `.rolling` windows are all vectorized.
- **Measured:** hourly sums from 500,000 per-second rows are **~403x** faster with `resample` than a per-timestamp Python loop (which floors each timestamp), the same order as `iterrows` and `groupby`-vs-loop. **Never loop over timestamps.**
- **The Deep U rule, on the time axis:** express time bucketing as `resample`, components as `.dt`, windows as `.rolling`, row-relative operations as `.shift`/`.diff`, always vectorized.
- **Edges:** `resample` needs a datetime index; frequency aliases changed across versions (`"H"`->`"h"`, `"M"`->`"ME"`); timezones are a correctness minefield (localize/convert explicitly); upsampling creates `NaN`s; parse dates with `format=`; `.dt` needs datetime dtype; rolling windows have warmup `NaN`s.

**Cross-references.** `groupby` (resample is its time form) → Chapter 58. Columnar DataFrame → Chapter 57. Vectorization → Chapter 96. Datetime dtype preserved by Parquet → Chapter 60. Timezone/encoding correctness → Deep D. Rolling, `merge_asof`, financial bars, distributed time series → the rest of Deep U / Deep W. Book III market-data pipeline → Deep U / Book III.
