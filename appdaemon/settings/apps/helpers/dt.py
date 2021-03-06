"""Define date/time utilities."""
from datetime import datetime, timedelta


def ceil_dt(target_dt: datetime, delta: timedelta) -> datetime:
    """Round a datetime up to the nearest delta."""
    return target_dt + (datetime.min - target_dt) % delta


def relative_time_of_day(hass) -> str:
    """Return the relative time of day based on time."""
    greeting = None
    now = hass.datetime()

    if now.hour < 12:
        greeting = 'morning'
    elif 12 <= now.hour < 18:
        greeting = 'afternoon'
    else:
        greeting = 'evening'

    return greeting


def time_is_between(
        hass, target_dt: datetime, start_time: str,
        end_time: str) -> bool:
    """Generalization of AppDaemon's now_is_between method."""
    start_time_dt = hass.parse_time(start_time)  # type: datetime
    end_time_dt = hass.parse_time(end_time)  # type: datetime
    start_dt = target_dt.replace(
        hour=start_time_dt.hour,
        minute=start_time_dt.minute,
        second=start_time_dt.second)
    end_dt = target_dt.replace(
        hour=end_time_dt.hour,
        minute=end_time_dt.minute,
        second=end_time_dt.second)

    if end_dt < start_dt:
        # Spans midnight
        if target_dt < start_dt and target_dt < end_dt:
            target_dt = target_dt + timedelta(days=1)
        end_dt = end_dt + timedelta(days=1)
    return start_dt <= target_dt <= end_dt
