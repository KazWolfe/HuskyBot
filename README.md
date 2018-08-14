# DakotaBot - Discord Assistant

DakotaBot is a powerful Discord bot designed from the ground up to assist with advanced moderation and
guild management. It boasts one of the most powerful anti-spam systems ever designed in a Discord bot,
with more features being added almost daily.

DakotaBot is built to be easy to use, easy to manage, and easy to deploy. It's based on KazWolfe's WolfBot
platform, using [`discord.py`  (rewrite)](https://github.com/Rapptz/discord.py/) as the provider.

Dakota was specifically built for [DIY Tech](https://discord.gg/diytech), but has since seen a number of
changes to make it more available to the general public.

DakotaBot features an extremely powerful plugin system based on discord.py's cog system, augmented with
WolfBot's management and configuration tools. As such, it is trivial to both deploy plugins to DakotaBot
as well as write your own.

***Caution:*** DakotaBot is an *advanced* Discord bot. It is strongly assumed that if you are running a
version of DakotaBot, you either know how to code or you have someone close by who does. DakotaBot is
not necessarily friendly to administrators or configuration, as it was initially designed for a specific
guild.

### Installation
DakotaBot *must* be installed once for every guild that it will be used on. Due to design choices made
during the bot's inception, the bot was built specifically to run in a single guild. 

0. Please be sure that you meet the following requirements before attempting to install DakotaBot:

    * A Discord API key. You may get one [here](https://discordapp.com/developers/applications/).
    * Ubuntu 18.04 or newer. ***The bot will not work reliably on Windows platforms!***
    * A server with at least 1GB RAM. I highly recommend [Digital Ocean](https://m.do.co/c/77962b668c59).
    * Python 3.6 or newer.
    * Python's PIP installed for Python 3.6

2. Once all prerequisites are set, run the below commands (as a non-privileged user) to install the bot:

       git clone https://github.com/KazWolfe/DakotaBot.git; cd DakotaBot
       sudo python3 -m pip install -r requirements.txt
       
3. *Before starting the bot*, [add it to your guild](https://discordapp.com/developers/docs/topics/oauth2#bots).
4. Once your bot is in your guild and ready to go, start it with `python3 BotCore.py`.
5. When prompted, paste in your bot API key, and hit ENTER.
6. Run `/help config` to get a list of base configuration values, and configure the bot as you see fit.

### Required Permissions
For the best experience, it is highly recommended you give DakotaBot **Administrator** privileges in your
guild. If you are uncomfortable with this, custom permissions may be used. Be sure that the bot at the
very least has permission to **Read Messages**, **Send Messages**, and **Attach Embeds**. Moderator features
and other more advanced parts of DakotaBot require more sophisticated permissions - please check the log to
see what permissions will need to be granted.

### Command Reference
Once your bot is online, you may use `/help` to get a list of all commands DakotaBot knows.