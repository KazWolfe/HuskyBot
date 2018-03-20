from enum import Enum


class Colors(Enum):
    PRIMARY = 0x007BFF
    SECONDARY = 0x6C757D
    SUCCESS = 0x28A745
    DANGER = 0xDC3545
    WARNING = 0xFFC107
    INFO = 0x17A2B8

    # Shortcuts
    ERROR = DANGER


class ChannelKeys(Enum):
    STAFF_LOG = "logs"
    STAFF_HUB = "modChannel"
    STAFF_ALERTS = "staffAlerts"
    PUBLIC_LOG = "audit"
