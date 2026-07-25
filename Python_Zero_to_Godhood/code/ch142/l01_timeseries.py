"""Listing 142.1 - time series: a datetime index, resampling, and the dt accessor.

Time is the axis of most real data (market ticks, logs, metrics, sensor readings), and
pandas has first-class time-series support built on a DATETIME INDEX:
  - pd.date_range / pd.to_datetime build datetime indexes and columns.
  - RESAMPLE is a time-based groupby: bucket rows into time intervals ("D", "h", "2D",
    month-end) and aggregate each bucket, "hourly totals from per-second data".
  - The .dt accessor extracts datetime components (year, month, day, weekday) VECTORIZED
    over a whole column, no Python loop.
Because time bucketing and component extraction run in C, they are orders of magnitude
faster than a per-timestamp Python loop (the benchmark). This listing shows each,
deterministically.
"""

import pandas as pd


def main() -> None:
    print("--- a datetime index over a fixed date range ---")
    idx = pd.date_range("2026-01-01", periods=6, freq="D")
    series = pd.Series([1, 2, 3, 4, 5, 6], index=idx)
    print(f"  number of days : {len(idx)}")
    print(f"  first / last   : {idx[0].date()} / {idx[-1].date()}")

    print("--- resample: a TIME-based groupby (bucket + aggregate) ---")
    two_day = series.resample("2D").sum()               # 2-day buckets, sum each
    print(f"  2-day bucket sums : {two_day.tolist()}   (1+2, 3+4, 5+6)")
    print(f"  number of buckets : {len(two_day)}")

    print("--- the .dt accessor: vectorized datetime components over a column ---")
    dates = pd.to_datetime(["2026-01-15", "2026-06-20", "2026-12-31"])
    df = pd.DataFrame({"ts": dates})
    print(f"  dt.year    : {df['ts'].dt.year.tolist()}")
    print(f"  dt.month   : {df['ts'].dt.month.tolist()}")
    print(f"  dt.day     : {df['ts'].dt.day.tolist()}")
    print(f"  dt.day_name (first): {df['ts'].dt.day_name().tolist()[0]!r}")

    print("--- time arithmetic and selection are vectorized ---")
    plus_week = df["ts"] + pd.Timedelta(days=7)
    print(f"  ts + 7 days (first) : {plus_week.dt.date.tolist()[0]}")

    print("--- the rule ---")
    print(f"  a datetime index enables resample (time groupby) and vectorized .dt")
    print(f"  component/arithmetic operations; never loop over timestamps")


if __name__ == "__main__":
    main()
