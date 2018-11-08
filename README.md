# HuskyBot - Discord Assistant

HuskyBot is a powerful Discord bot designed from the ground up to assist with advanced moderation and
guild management. It boasts one of the most powerful anti-spam systems ever designed in a Discord bot,
with more features being added almost daily.

HuskyBot is built to be easy to use, easy to manage, and easy to deploy. It's based on KazWolfe's WolfBot
platform, using [`discord.py`  (rewrite)](https://github.com/Rapptz/discord.py/) as the provider.

Dakota was specifically built for [DIY Tech](https://discord.gg/diytech), but has since seen a number of
changes to make it more available to the general public.

HuskyBot features an extremely powerful plugin system based on discord.py's cog system, augmented with
WolfBot's management and configuration tools. As such, it is trivial to both deploy plugins to HuskyBot
as well as write your own.

***Caution:*** HuskyBot is an *advanced* Discord bot. It is strongly assumed that if you are running a
version of HuskyBot, you either know how to code or you have someone close by who does. HuskyBot is
not necessarily friendly to administrators or configuration, as it was initially designed for a specific
guild.

### Installation
HuskyBot *must* be installed once for every guild that it will be used on. Due to design choices made
during the bot's inception, the bot was built specifically to run in a single guild. 

0. Please be sure that you meet the following requirements before attempting to install HuskyBot:

    * A Discord API key. You may get one [here](https://discordapp.com/developers/applications/).
    * Ubuntu 18.04 or newer. ***The bot will not work reliably on Windows platforms!***
    * A server with at least 1GB RAM. I highly recommend [Digital Ocean](https://m.do.co/c/77962b668c59).
    * Python 3.6 or newer.
    * Python's PIP installed for Python 3.6

2. Once all prerequisites are set, run the below commands (as a non-privileged user) to install the bot:

       git clone https://github.com/KazWolfe/HuskyBot.git; cd HuskyBot
       sudo python3 -m pip install -r requirements.txt
       
3. [Add the bot to your guild](https://discordapp.com/developers/docs/topics/oauth2#bots).
4. Once your bot is in your guild and ready to go, start it with `python3 BotCore.py`.
5. When prompted, paste in your bot API key, and hit ENTER.
6. Run `/help config` to get a list of base configuration values, and configure the bot as you see fit.

#### Docker Installation

HuskyBot can optionally be installed as a Docker container, and is more or less self-reliant. When you have been cleared
by a bot developer to run your own build of HuskyBot, you will receive a zipfile containing the `Dockerfile` and a 
folder named `keys`. Extract both of these to an empty folder somewhere. When the files are extracted, switch to that 
folder and run:

    docker build -t huskybot .
    docker run -e "DISCORD_TOKEN=<your_api_key>" huskybot:latest
    
Alternatively, you can set `DISCORD_TOKEN` in your environment variables if you'd rather not pass it in via commands.
This configuration also allows Docker to be launched on managed services, like ECS. See the Docker manual for 
instructions on how to do this.

Note that the initial build will take a while due to dependency updates. This is normal, and future launches using 
`docker run` will be quick. The bot will automatically take care of updates after it is built, meaning bot owners have 
a seamless experience.

Once your bot is running, you may [add the bot](https://discordapp.com/developers/docs/topics/oauth2#bots) to your 
guild.

### Required Permissions
For the best experience, it is highly recommended you give HuskyBot **Administrator** privileges in your
guild. If you are uncomfortable with this, custom permissions may be used. Be sure that the bot at the
very least has permission to **Read Messages**, **Send Messages**, and **Attach Embeds**. Moderator features
and other more advanced parts of HuskyBot require more sophisticated permissions - please check the log to
see what permissions will need to be granted.

### Command Reference
Once your bot is online, you may use `/help` to get a list of all commands HuskyBot knows.
