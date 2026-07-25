"""Listing 36.1 - naive vs aware datetimes, and ISO parsing.

The single most common datetime bug is the NAIVE datetime: one with no tzinfo,
which Python treats as "local, but unspecified," and which silently produces
wrong answers the moment two time zones (or a DST boundary) are involved. The
fix is the AWARE datetime, one that carries a tzinfo. This listing shows the
distinction, timezone-aware arithmetic, and ISO-8601 parsing with
fromisoformat, which since 3.11 accepts 'Z' and a space separator.
"""

from datetime import datetime, timezone, timedelta


def main() -> None:
    print("--- naive vs aware: the tzinfo is the whole story ---")
    naive = datetime(2026, 7, 24, 12, 0, 0)
    aware = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    print(f"  naive.tzinfo        : {naive.tzinfo}")
    print(f"  aware.tzinfo        : {aware.tzinfo}")
    print(f"  naive is aware?     : {naive.tzinfo is not None}")
    print(f"  aware is aware?     : {aware.tzinfo is not None}")

    print("--- aware arithmetic: convert between zones correctly ---")
    ist = timezone(timedelta(hours=5, minutes=30))   # Asia/Kolkata offset
    in_ist = aware.astimezone(ist)
    print(f"  12:00 UTC in IST    : {in_ist.strftime('%H:%M %z')}")
    print(f"  same instant?       : {aware == in_ist}")   # equal: same moment

    print("--- durations are timedeltas ---")
    later = aware + timedelta(hours=36)
    print(f"  +36h                : {later.isoformat()}")
    print(f"  span in hours       : {(later - aware).total_seconds() / 3600}")

    print("--- fromisoformat: fast, and since 3.11 accepts Z and space ---")
    print(f"  offset form         : {datetime.fromisoformat('2026-07-24T12:00:00+00:00').isoformat()}")
    print(f"  Z suffix            : {datetime.fromisoformat('2026-07-24T12:00:00Z').isoformat()}")
    print(f"  space separator     : {datetime.fromisoformat('2026-07-24 12:00:00').isoformat()}")


if __name__ == "__main__":
    main()
