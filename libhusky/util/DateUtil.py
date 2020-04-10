import datetime
import re

from libhusky import HuskyStatics


def get_timestamp():
    """
    Get the UTC timestamp in YYYY-MM-DD HH:MM:SS format (Bot Standard)
    """

    return datetime.datetime.utcnow().strftime(HuskyStatics.DATETIME_FORMAT)


def get_timedelta_from_string(timestring: str):
    regex = re.compile(r'((?P<days>\d+?)d)?((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

    parts = regex.match(timestring)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    if time_params == {}:
        raise ValueError("Invalid time string! Must be in form #d#h#m#s.")
    return datetime.timedelta(**time_params)


def get_delta_timestr(timediff: datetime.timedelta):
    time_components = []

    hours = (timediff.seconds // 3600) % 24
    minutes = (timediff.seconds // 60) % 60
    seconds = timediff.seconds % 60

    if timediff.days > 1:
        time_components.append(f"{timediff.days} days")
    elif timediff.days == 1:
        time_components.append(f"{timediff.days} day")

    if hours > 1 or timediff.days:
        time_components.append(f"{hours} hours")
    elif hours == 1:
        time_components.append(f"{hours} hour")

    if minutes > 1 or hours or timediff.days:
        time_components.append(f"{minutes} minutes")
    elif minutes == 1:
        time_components.append(f"{minutes} minute")

    if seconds > 1 or hours or minutes or timediff.days:
        time_components.append(f"{seconds} seconds")
    elif seconds == 1:
        time_components.append(f"{seconds} second")
    else:
        time_components.append("now")

    return ", ".join(time_components)
