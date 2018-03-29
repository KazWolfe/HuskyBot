import datetime
import subprocess

import discord

import WolfBot.WolfConfig
from WolfBot import WolfStatics


def memberHasRole(member, role_id):
    for r in member.roles:
        if r.id == role_id:
            return True

    return False


def memberHasAnyRole(member, roles):
    if roles is None:
        return True

    for r in member.roles:
        if r.id in roles:
            return True

    return False


def getFancyGameData(member):
    if member.activity is not None:
        state = {0: "Playing ", 1: "Streaming ", 2: "Listening to ", 3: "Watching "}

        if not isinstance(member.activity, discord.Game) and member.activity.url is not None:
            return "([{}]({}))".format(state[member.activity.type] + member.activity.name, member.activity.url)
        else:
            return "({})".format(state[member.activity.type] + member.activity.name)

    return ""


def tail(filename, n):
    p = subprocess.Popen(['tail', '-n', str(n), filename], stdout=subprocess.PIPE)
    soutput, sinput = p.communicate()
    return soutput.decode('utf-8')


def should_process_message(message):
    if message.guild is not None and message.guild.id in WolfBot.WolfConfig.getConfig().get("ignoredGuilds", []):
        return False

    if message.author.bot:
        return False

    return True


def trim_string(string: str, limit: int, add_ellipses: bool):
    s = string

    if len(string) > limit:
        s = string[:limit]

        if add_ellipses:
            s = s[:-5] + "\n\n..."

    return s


def get_timestamp():
    """
    Get the UTC timestamp in YYYY-MM-DD HH:MM:SS format (Bot Standard)
    """

    return datetime.datetime.utcnow().strftime(WolfStatics.DATETIME_FORMAT)
