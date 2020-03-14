import collections
import datetime
import gzip
import hashlib
import imghdr
import logging
import os
import re
import struct
import subprocess
from logging import handlers

import discord
import math
import unicodedata

from libhusky import HuskyStatics, HuskyConfig


def member_has_role(member, role_id):
    for r in member.roles:
        if r.id == role_id:
            return True

    return False


def member_has_any_role(member, roles):
    if roles is None:
        return True

    for r in member.roles:
        if r.id in roles:
            return True

    return False


def get_fancy_game_data(member):
    if member.activity is not None:
        state = {discord.ActivityType.playing: "Playing ",
                 discord.ActivityType.streaming: "Streaming ",
                 discord.ActivityType.listening: "Listening to ",
                 discord.ActivityType.watching: "Watching ",
                 4: "Custom: "}

        if isinstance(member.activity, discord.Spotify):
            m = "(Listening to Spotify)"

            if member.activity.title is not None and member.activity.artist is not None:
                track_url = "https://open.spotify.com/track/{}"

                m += f"\n\n**Now Playing:** [{member.activity.title} by " \
                     f"{member.activity.artist}]({track_url.format(member.activity.track_id)})"

            return m
        # custom status
        elif member.activity.type == 4:
            return f"({member.activity.state})"
        elif not isinstance(member.activity, discord.Game) and member.activity.url is not None:
            return f"([{state[member.activity.type] + member.activity.name}]({member.activity.url}))"
        else:
            return f"({state[member.activity.type] + member.activity.name})"

    return ""


def tail(filename, n):
    p = subprocess.Popen(['tail', '-n', str(n), filename], stdout=subprocess.PIPE)
    soutput, sinput = p.communicate()
    return soutput.decode('utf-8')


def should_process_message(message: discord.Message):
    # Don't process direct messages
    if not isinstance(message.channel, discord.TextChannel):
        return False

    # Don't process messages from ignored guilds (developer mode)
    if message.guild.id in HuskyConfig.get_config().get("ignoredGuilds", []):
        return False

    # Don't process messages from other bots.
    if message.author.bot:
        return False

    # Otherwise, process.
    return True


def trim_string(string: str, limit: int, add_suffix: bool = True, trim_suffix: str = "\n\n..."):
    s = string

    if len(string) > limit:
        s = string[:limit]

        if add_suffix:
            s = s[:-len(trim_suffix)] + trim_suffix

    return s


def get_timestamp():
    """
    Get the UTC timestamp in YYYY-MM-DD HH:MM:SS format (Bot Standard)
    """

    return datetime.datetime.utcnow().strftime(HuskyStatics.DATETIME_FORMAT)


def get_user_id_from_arbitrary_str(guild: discord.Guild, string: str):
    if string.isnumeric():
        potential_uid = int(string)
    elif string.startswith("<@") and string.endswith(">"):
        potential_uid = int(string.replace("<@", "").replace(">", "").replace("!", ""))
    else:
        potential_user = guild.get_member_named(string)

        if potential_user is None:
            raise ValueError(f"No member by the name of {string} was found.")

        return potential_user.id

    # if guild.get_member(potential_uid) is None:
    #    raise ValueError("Member ID {} (translated from {}) was not found. ".format(potential_uid, string))

    return potential_uid


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


def get_sort_index(target_list: list, new_object, attribute: str):
    comparator = new_object[attribute]

    # special null case
    if comparator is None:
        return len(target_list)

    for i in range(0, len(target_list)):
        item = target_list[i]

        if comparator < item[attribute]:
            return i

    return len(target_list)


def get_image_size(fname):
    """
    Determine the image type of fhandle and return its size.
    from draco

    see: https://stackoverflow.com/a/20380514/1817097
    """

    with open(fname, 'rb') as fhandle:
        head = fhandle.read(24)
        if len(head) != 24:
            return
        if imghdr.what(fname) == 'png':
            check = struct.unpack('>i', head[4:8])[0]
            if check != 0x0d0a1a0a:
                return
            width, height = struct.unpack('>ii', head[16:24])
        elif imghdr.what(fname) == 'gif':
            width, height = struct.unpack('<HH', head[6:10])
        elif imghdr.what(fname) == 'jpeg':
            try:
                fhandle.seek(0)  # Read 0xff next
                size = 2
                ftype = 0
                while not 0xc0 <= ftype <= 0xcf:
                    fhandle.seek(size, 1)
                    byte = fhandle.read(1)
                    while ord(byte) == 0xff:
                        byte = fhandle.read(1)
                    ftype = ord(byte)
                    size = struct.unpack('>H', fhandle.read(2))[0] - 2
                # We are at a SOFn block
                fhandle.seek(1, 1)  # Skip `precision' byte.
                height, width = struct.unpack('>HH', fhandle.read(4))
            except IOError:
                return
        else:
            return
        return width, height


async def send_to_keyed_channel(bot: discord.Client, channel: HuskyStatics.ChannelKeys, embed: discord.Embed):
    log_channel = HuskyConfig.get_config().get('specialChannels', {}).get(channel.value, None)
    if log_channel is not None:
        log_channel: discord.TextChannel = bot.get_channel(log_channel)

        await log_channel.send(embed=embed)


def get_fragment_from_invite(data: str) -> str:
    """
    Attempt to get a fragment from an invite data string.

    This method makes no attempt to verify the legitimacy (or accuracy) of the invite fragment. It will only attempt
    to strip out the URL portion (if it exists).

    :param data: The data to attempt to strip a fragment from
    :return: The best guess for the invite fragment
    """
    discordgg_link_check = re.search(HuskyStatics.Regex.INVITE_REGEX, data, flags=re.IGNORECASE)

    if discordgg_link_check is not None:
        return discordgg_link_check.group('fragment')

    return data


def confirm_dialog_check(triggering_user: discord.Member):
    def wrap(reaction: discord.Reaction, user: discord.Member):
        if user.bot:
            # Ignore all bots.
            return False

        if not (user == triggering_user or user.guild_permissions.administrator):
            return False

        if reaction.emoji in [HuskyStatics.Emojis.CHECK, HuskyStatics.Emojis.X]:
            return True
        else:
            return False

    return wrap


def calculate_str_entropy(string):
    probabilities = [n_x / len(string) for x, n_x in collections.Counter(string).items()]
    e_x = [-p_x * math.log(p_x, 2) for p_x in probabilities]
    return sum(e_x)


def escape_markdown(string):
    markdown_characters = ["\\", "~", "`", "*", "_", "[", "@"]

    for c in markdown_characters:
        string = string.replace(c, "\\" + c)

    return string


def is_docker():
    path = '/proc/self/cgroup'
    return (
            os.path.exists('/.dockerenv') or
            os.path.isfile(path) and any('docker' in line for line in open(path))
    )


def get_platform_type():
    if is_docker():
        return os.environ.get('HUSKYBOT_PLATFORM', 'Docker')

    if HuskyConfig.get_session_store().get('daemonMode', False):
        return os.environ.get('HUSKYBOT_PLATFORM', 'Daemonized')

    return os.environ.get('HUSKYBOT_PLATFORM', None)


def get_mutual_guilds(bot, user_a: discord.User, user_b: discord.User):
    mutuals = []

    for g in bot.guilds:
        if user_a not in g.members:
            continue

        if user_b not in g.members:
            continue

        mutuals.append(g)

    return mutuals


def convert_emoji_to_hex(string: str):
    splits = []
    for character in string:
        if unicodedata.category(character) != "So":
            continue

        splits.append(character)

    return splits


def get_sha1_hash_of_file(path):
    blocksize = 65536
    hasher = hashlib.sha1()
    with open(path, 'rb') as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()


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


class TwitterSnowflake:
    def __init__(self):
        self.timestamp = None
        self.machine_id = None
        self.sequence_number = None

        # data itself
        self.flake = None

        # custom stuff
        self.epoch = 0

    def __calculate__(self):
        self.flake = self.sequence_number
        self.flake += self.machine_id << 12
        self.flake += int((self.timestamp - self.epoch) * 1000) << 22

    def __decode__(self):
        self.timestamp = ((self.flake >> 22) + (self.epoch * 1000)) / 1000
        self.machine_id = (self.flake & 0x3E0000) >> 12
        self.sequence_number = (self.flake & 0xFFF)

    def __repr__(self):
        return f"<TwitterSnowflake={self.flake} timestamp={self.timestamp} machine_id={self.machine_id} " \
               f"seq={self.sequence_number}>"

    @staticmethod
    def new(timestamp: int, machine_id: int, sequence_number: int, epoch=0):
        flake = TwitterSnowflake()
        flake.timestamp = timestamp
        flake.machine_id = machine_id
        flake.sequence_number = sequence_number
        flake.epoch = epoch
        flake.__calculate__()

        return flake

    @staticmethod
    def load(flake, epoch=0):
        snowflake = TwitterSnowflake()
        snowflake.flake = flake
        snowflake.epoch = epoch
        snowflake.__decode__()

        return snowflake

    def get_datetime(self):
        return datetime.datetime.fromtimestamp(self.timestamp)


class CompressingRotatingFileHandler(logging.handlers.RotatingFileHandler):
    # Code source: https://stackoverflow.com/a/35547094/1817097
    # Modified by Kaz Wolfe

    def __init__(self, filename, **kws):
        backup_count = kws.get('backupCount', 0)
        self.backup_count = backup_count
        os.makedirs(os.path.dirname(filename), exist_ok=True)  # Make logs if we need to
        logging.handlers.RotatingFileHandler.__init__(self, filename, **kws)

    @staticmethod
    def do_archive(old_log):
        with open(old_log, 'rb') as log:
            with gzip.open(old_log + '.gz', 'wb') as comp_log:
                comp_log.writelines(log)

        os.remove(old_log)

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        if self.backup_count > 0:
            for i in range(self.backup_count - 1, 0, -1):
                sfn = "%s.%d.gz" % (self.baseFilename, i)
                dfn = "%s.%d.gz" % (self.baseFilename, i + 1)
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)

        dfn = self.baseFilename + ".1"

        if os.path.exists(dfn):
            os.remove(dfn)

        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, dfn)
            self.do_archive(dfn)

        if not self.delay:
            self.stream = self._open()


class Singleton(type):
    # Borrowed from https://stackoverflow.com/a/6798042/1817097
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
