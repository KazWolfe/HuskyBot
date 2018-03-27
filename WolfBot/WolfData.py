class Mute:
    id = 0
    timestamp = None

    user_id = 0
    reason = ""

    # None for guildwide, ID for a channel
    channel = None

    # Expiry of None is permanent.
    expiry = None

    def load_dict(self, data: dict):
        mute = Mute()

        mute.id = data.get('id')
        mute.user_id = data.get('user_id')

        mute.reason = data.get('reason')
        mute.channel = data.get('channel')
        mute.expiry = data.get('expiry')

        return mute
