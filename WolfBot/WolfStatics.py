from enum import Enum, IntEnum

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"

GIT_URL = "https://www.github.com/KazWolfe/DakotaBot"

DEVELOPERS = [
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
    """
    Quick reference for channels used internally.

    STAFF_LOG - Automatic log for moderative actions taken by users or the bot. Generic log.
    STAFF_HUB - The channel used for internal moderator discussion, non-urgent.
    STAFF_ALERTS - Urgent notifications for immediate review by active staff members.
    PUBLIC_LOG - Publicly-available log used to track guild events and display them for transparency.
    MESSAGE_LOG - Message-based event tracking (e.g. deletions or edits)
    USER_LOG - User-based event tracking (e.g. join/leave/rename)
    """

    STAFF_LOG = "logs"
    STAFF_HUB = "modChannel"
    STAFF_ALERTS = "staffAlerts"
    PUBLIC_LOG = "audit"
    MESSAGE_LOG = "messageLogs"
    USER_LOG = "userLogs"


class SpecialRoleKeys(Enum):
    BOTS = "bots"
    MUTED = "muted"
    MODS = "moderators"
    ADMINS = "administrators"
    BOT_DEVS = "botDevelopers"


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
    TICKETS = "\U0001F39F"
    TADA = "\U0001F389"
    REPEAT = "\U0001F501"
    DOG = "\U0001F436"
    HEART = "\U00002764"
    MEAT = "\U0001F356"
    BATTERY = "\U0001F50B"
    STAR = "\U00002B50"
    STOP = "\U0001F6D1"
    ROBOT = "\U0001F916"
    CHECK = "\U00002705"
    X = "\U0000274C"
    LOCK = "\U0001F512"
    INBOX = "\U0001F4E5"
    MEMO = "\U0001F4DD"
    REFRESH = "\U0001F504"
    WAVE = "\U0001F44B"
    NAMETAG = "\U0001F4DB"
    SPARKLES = "\U00002728"
    RADIO = "\U0001F4FB"

    # Mod shortcuts
    BAN = NO_ENTRY
    WARNING = TRIANGLE
    UNBAN = UNLOCK
    MUTE = MUTED_SPEAKER
    UNMUTE = LOUD_SPEAKER

    # Giveaway shortcut
    GIVEAWAY = TICKETS


class Regex:
    # @stephenhay's regex from https://mathiasbynens.be/demo/url-regex
    URL_REGEX = r"\b(([\w-]+://?|www[.])[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|\/)))"

    INVITE_REGEX = r'(discord\.gg|discordapp.com/invite)/(?P<fragment>[0-9a-z\-]+)'
