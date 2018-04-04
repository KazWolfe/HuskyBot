from enum import Enum, IntEnum

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


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


class ChannelKeys(str, Enum):
    STAFF_LOG = "logs"
    STAFF_HUB = "modChannel"
    STAFF_ALERTS = "staffAlerts"
    PUBLIC_LOG = "audit"


class SpecialRoleKeys(str, Enum):
    BOTS = "bots"
    MUTED = "muted"
    MODS = "moderators"
    ADMINS = "administrators"


class Emojis:
    NO_ENTRY = "\uD83D\uDEAB"
    TRIANGLE = "\u26A0\uFE0F"
    DOOR = "\uD83D\uDEAA"
    SUNRISE = "\uD83C\uDF04"
    WOLF = "\uD83D\uDC3A"
    PARTY = "\uD83C\uDF89"
    BOMB = "\uD83D\uDCA3"
    UNLOCK = "\uD83D\uDD13"
    FIRE = "\uD83D\uDD25"
    SKULL = "\uD83D\uDC80"
    BOOK = "\uD83D\uDCDA"
    MUTED_SPEAKER = "\uD83D\uDD07"
    LOUD_SPEAKER = "\uD83D\uDD0A"
    SHIELD = "\uD83D\uDEE1"
    BOOKMARK2 = "\uD83D\uDCD1"

    # Mod shortcuts
    BAN = NO_ENTRY
    WARNING = TRIANGLE
    UNBAN = UNLOCK
    MUTE = MUTED_SPEAKER
    UNMUTE = LOUD_SPEAKER
