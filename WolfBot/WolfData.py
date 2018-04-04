import datetime

import discord


class Mute:
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
        self.user_id = data.get('userId')

        self.reason = data.get('reason')
        self.guild = data.get('guild')
        self.channel = data.get('channel')
        self.expiry = data.get('expiry')

        self.perms_cache = data.get('perms')

        return self

    def to_data(self):
        return {
            "userId": self.user_id,
            "reason": self.reason,
            "guild": self.guild,
            "channel": self.channel,
            "expiry": self.expiry,
            "perms": self.perms_cache
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
