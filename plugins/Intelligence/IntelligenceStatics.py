import discord

from libhusky.HuskyStatics import Emojis

INVSPY_VL_MAP = {
    discord.enums.VerificationLevel.none: "No Verification",
    discord.enums.VerificationLevel.low: "Verified Email Needed",
    discord.enums.VerificationLevel.medium: "User for 5+ minutes",
    discord.enums.VerificationLevel.high: "Member for 10+ minutes",
    discord.enums.VerificationLevel.extreme: "Verified Phone Needed"
}

INVSPY_CHANNEL_PREFIX_MAP = {
    discord.ChannelType.text: "#",
    discord.ChannelType.voice: f"{Emojis.LOUD_SPEAKER} ",
    discord.ChannelType.category: f"{Emojis.CARD_INDEX} ",
    discord.ChannelType.news: f"{Emojis.NEWSPAPER} #",
    discord.ChannelType.store: f"{Emojis.SHOPPING_BAGS} #",
    discord.ChannelType.private: "#",
    discord.ChannelType.group: "#"
}
