from datetime import datetime, timedelta

CHECK_MINUTES = (1, 31)


def next_check_time(now: datetime) -> datetime:
    candidate = now.replace(second=0, microsecond=0)
    for _ in range(61):
        candidate += timedelta(minutes=1)
        if candidate.minute in CHECK_MINUTES and candidate > now:
            return candidate
    raise RuntimeError("unreachable: CHECK_MINUTES misconfigured")
