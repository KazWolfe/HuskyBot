import datetime

import discord


class Mute:
    def __getitem__(self, item):
        return getattr(self, item)

    def __eq__(self, other):
        return (self.expiry == other.expiry) \
               and (self.guild == other.guild) \
               and (self.channel == other.channel) \
               and (self.user_id == other.user_id)

    def __lt__(self, other):
        return (self.expiry is not None) and (self.expiry < other.expiry)

    def __gt__(self, other):
        return (self.expiry is None) or (self.expiry > other.expiry)

    user_id = 0
    reason = ""

    # Guild ID. Mandatory.
    guild = 0

    # None for guildwide, ID for a channel
    channel = None

    # Expiry of None is permanent.
    expiry = None

    # Permissions cache (None is either guild mute *or* "no manual permissions")
    # tens digit = react (0 = not set, 1 = no, 2 = yes) [ perms_cache / 10 ]
    # ones digit = send  (0 = not set, 1 = no, 2 = yes) [ perms_cache % 10 ]
    perms_cache = None

    def load_dict(self, data: dict):
        self.user_id = data.get('user_id')

        self.reason = data.get('reason')
        self.guild = data.get('guild')
        self.channel = data.get('channel')
        self.expiry = data.get('expiry')

        self.perms_cache = data.get('perms_cache')

        return self

    def to_data(self):
        return {
            "user_id": self.user_id,
            "reason": self.reason,
            "guild": self.guild,
            "channel": self.channel,
            "expiry": self.expiry,
            "perms_cache": self.perms_cache
        }

    def to_json(self):
        return self.to_data()

    def get_cached_override(self):
        c = {0: None, 1: False, 2: True}

        if self.perms_cache is None:
            return None

        return discord.PermissionOverwrite(
            add_reactions=c[int(self.perms_cache / 10)],
            send_messages=c[int(self.perms_cache % 10)]
        )

    def set_cached_override(self, perms: discord.PermissionOverwrite):
        c = {None: 0, False: 1, True: 2}

        if perms is None or perms.is_empty():
            self.perms_cache = None
            return None

        i = 0

        i = i + c[perms.add_reactions] * 10
        i = i + c[perms.send_messages]

        self.perms_cache = int(i)

        return i

    def is_expired(self):
        if self.expiry is None:
            return False

        return self.expiry <= datetime.datetime.utcnow().timestamp()


class GiveawayObject:
    def __getitem__(self, item):
        return getattr(self, item)

    def __eq__(self, other):
        return (self.end_time == other.end_time) \
               and (self.name == other.name) \
               and (self.register_channel_id == other.register_channel_id) \
               and (self.register_message_id == other.register_message_id) \
               and (self.winner_count == other.winner_count)

    def __lt__(self, other):
        return (self.end_time is not None) and (self.end_time < other.end_time)

    def __gt__(self, other):
        return (self.end_time is None) or (self.end_time > other.end_time)

    name = ""

    start_time = None
    end_time = None

    register_channel_id = 0
    register_message_id = 0

    winner_count = 1

    def load_dict(self, data: dict):
        self.name = data.get('name')

        self.end_time = data.get('end_time')

        self.register_channel_id = data.get('register_channel_id')
        self.register_message_id = data.get('register_message_id')

        self.winner_count = data.get('winner_count')

        return self

    def is_over(self):
        return self.end_time <= datetime.datetime.utcnow().timestamp()
