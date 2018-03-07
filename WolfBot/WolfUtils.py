import subprocess

from BotCore import BOT_CONFIG


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
    fancy_game = ""
    if member.game is not None:
        state = {0: "Playing ", 1: "Streaming ", 2: "Listening to "}

        fancy_game += "("
        if member.game.url is not None:
            fancy_game += "["

        fancy_game += state[member.game.type]
        fancy_game += member.game.name

        if member.game.url is not None:
            fancy_game += "](" + member.game.url + ")"

        fancy_game += ")"

    return fancy_game


def tail(filename, n):
    p=subprocess.Popen(['tail', '-n', str(n), filename], stdout=subprocess.PIPE)
    soutput, sinput = p.communicate()
    return soutput.decode('utf-8')


def should_process_message(message):
    if message.guild.id in BOT_CONFIG.get("ignoredGuilds", []):
        return False

    if message.author.bot:
        return False

    return True
