from enum import Enum, IntEnum

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

GIT_URL = "https://www.github.com/KazWolfe/DakotaBot"

__developers__ = [
    142494680158961664  # KazWolfe#2896, notification PoC
]


class Colors(IntEnum):
    PRIMARY = 0x007BFF
    SECONDARY = 0x6C757D
    SUCCESS = 0x28A745
    DANGER = 0xDC3545
    WARNING = 0xFFC107
    INFO = 0x17A2B8

    GUILD_COLOR = 0x3AC4FF

    # Shortcuts
    ERROR = DANGER


class ChannelKeys(Enum):
    STAFF_LOG = "logs"
    STAFF_HUB = "modChannel"
    STAFF_ALERTS = "staffAlerts"
    PUBLIC_LOG = "audit"
    MESSAGE_LOG = "messageLogs"


class SpecialRoleKeys(Enum):
    BOTS = "bots"
    MUTED = "muted"
    MODS = "moderators"
    ADMINS = "administrators"


class Emojis:
    NO_ENTRY = "\U0001F6AB"
    TRIANGLE = "\U000026A0"
    DOOR = "\U0001F6AA"
    SUNRISE = "\U0001F304"
    WOLF = "\U0001F43A"
    PARTY = "\U0001F389"
    BOMB = "\U0001F4A3"
    UNLOCK = "\U0001F513"
    FIRE = "\U0001F525"
    SKULL = "\U0001F480"
    BOOK = "\U0001F4DA"
    MUTED_SPEAKER = "\U0001F507"
    LOUD_SPEAKER = "\U0001F50A"
    SHIELD = "\U0001F6E1"
    BOOKMARK2 = "\U0001F4D1"
    RED_FLAG = "\U0001F6A9"
    TADA = "\U0001F389"
    REPEAT = "\U0001F501"
    DOG = "\U0001F436"
    HEART = "\U00002764"
    MEAT = "\U0001F356"
    BATTERY = "\U0001F50B"
    STAR = "\U00002B50"

    # Mod shortcuts
    BAN = NO_ENTRY
    WARNING = TRIANGLE
    UNBAN = UNLOCK
    MUTE = MUTED_SPEAKER
    UNMUTE = LOUD_SPEAKER

    # Giveaway shortcut
    GIVEAWAY = TADA


class Regex:
    URL_REGEX = r"\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>" \
                r"]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{}" \
                r";:'\".,<>?«»“”‘’]))"
