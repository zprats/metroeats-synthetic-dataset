from datetime import date, datetime, time, timedelta, timezone


IST = timezone(timedelta(hours=5, minutes=30))
DATA_START = date(2025, 1, 1)
DATA_END = date(2025, 12, 31)
HOUR_WEIGHTS = (2, 1, 1, 1, 1, 2, 4, 7, 9, 7, 5, 12, 17, 17, 12, 7, 7, 9, 13, 20, 24, 22, 16, 8)


def weighted_calendar(start=DATA_START, end=DATA_END):
    if end < start:
        raise ValueError("end must not precede start")
    days = []
    weights = []
    current = start
    while current <= end:
        weight = 1.22 if current.weekday() >= 5 else 1.0
        if current.month in {10, 11, 12}:
            weight *= 1.08
        days.append(current)
        weights.append(weight)
        current += timedelta(days=1)
    return days, weights


def random_order_time(random_source, calendar, hour_weights=HOUR_WEIGHTS):
    days, weights = calendar
    if not days or len(days) != len(weights):
        raise ValueError("calendar days and weights must be non-empty and aligned")
    if len(hour_weights) != 24:
        raise ValueError("hour_weights must contain 24 values")
    day = random_source.choices(days, weights=weights, k=1)[0]
    hour = random_source.choices(tuple(range(24)), weights=hour_weights, k=1)[0]
    return datetime.combine(
        day,
        time(hour, random_source.randrange(60), random_source.randrange(60)),
        tzinfo=IST,
    )


def format_timestamp(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.isoformat(timespec="seconds")
