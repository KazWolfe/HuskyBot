# HuskyBot - Discord Assistant

HuskyBot is a powerful Discord bot designed from the ground up to assist with advanced moderation and
guild management. It boasts one of the most powerful anti-spam systems ever designed in a Discord bot,
with more features being added every now and then.

HuskyBot is built to be easy to use, easy to manage, and easy to deploy. It's based on KazWolfe's WolfBot
platform, using [`discord.py`](https://github.com/Rapptz/discord.py/) as the provider. HuskyBot was specifically built 
for [DIY Tech](https://discord.gg/diytech), but has since seen a number of changes to make it more available to the 
general public.

HuskyBot features an extremely powerful plugin system based on discord.py's cog system, augmented with
WolfBot's management and configuration tools. As such, it is trivial to both deploy plugins to HuskyBot
as well as write your own.

***Caution:*** HuskyBot is an *advanced* Discord bot. While efforts have been made to make the bot easier to use, 
certain powerful features of the bot are still somewhat difficult. Little to no consideration was put into the UX of 
HuskyBot outside of core functionality and usability. If you are running your own HuskyBot instance, it is strongly 
recommended that you know or have someone who knows how to read and understand Python code. Support for the bot is
generally available, but response times may vary.

If you require assistance or support with the bot at any time (and you're using the master branch), swing
on by DIY Tech's `#husky-support` channel to get (mostly) live developer assistance.

### Installation

It is *highly* recommended that HuskyBot be deployed via [Docker Compose](https://docs.docker.com/compose/), as it will
take care of the hard work of setting up dependencies and managing the environment. Docker Compose also offers the 
capability to automatically restart the bot in case of failure, as well as isolate it from the rest of a server for 
security purposes.

To get started with the Compose installation of the bot:

1. Clone the repository somewhere and `cd` to it,
2. Copy `env.sample` to `.env`.
3. Open the `.env` file and add your Discord bot API token on the `DISCORD_TOKEN` line.
4. Save the file, and run the bot with `docker-compose up -d`. The bot and all dependencies will automatically launch.
5. [Add the bot to your guild](https://discordapp.com/developers/docs/topics/oauth2#bots), and enjoy.

The initial run of HuskyBot may take a while to complete. Dependency installation (while automatic) may take a while to
build all necessary packages and cache all other relevant information. Future runs of the bot will go through a minified
version of the dependency installation (mostly to ensure any dependency changes are reflected) and will be faster.

Each "instance" of HuskyBot must also be bound to a single specific guild (at least for the time being). This is a
hardcoded limitation of HuskyBot and was made due to some design choices early in the bot's creation. Typically, it is
recommended that no more than a single instance of HuskyBot (and its associated Docker images) run on a single server. 
If you would like to run multiple instances on a single physical machine, see the [`docker-compose` FAQ](https://docs.docker.com/compose/faq/#how-do-i-run-multiple-copies-of-a-compose-file-on-the-same-host)
for a guide. Note that certain features will not work and support for this configuration is currently not offered.

#### Development Environment

If you would like to develop on the HuskyBot platform, the code may be run without the use of Docker Compose. This mode
of execution is ***not*** supported for production. 

The following dependences are required to run the bot:

* A POSIX-compliant operating system, such as Linux or macOS.
* Python version 3.6 or newer
* Python's PIP installed
* All of HuskyBot's dependencies installed (`python3 -m pip install -Ur requirements.txt`)

While not necessary, the use of `venv` is ***highly*** recommended for development purposes. Additionally, two 
environment variables must be set for the bot to run properly in development mode:

* The `DISCORD_TOKEN` environment variable must be set to a Discord bot API token. Selfbot tokens are not supported.
* The `HUSKYBOT_DEVMODE` environment variable must be set to `1` or another truthy value.

Simply running `HuskyBot.py` will be enough to start up the environment.

### Required Permissions

For the best experience, it is highly recommended you give HuskyBot **Administrator** privileges in your
guild. If you are uncomfortable with this, custom permissions may be used. Be sure that the bot at the
very least has permission to **Read Messages**, **Send Messages**, and **Attach Embeds**. Moderator features
and other more advanced parts of HuskyBot require more sophisticated permissions - please check the log to
see what permissions will need to be granted.

### Command Reference
Once your bot is online, you may use `/help` to get a list of all commands HuskyBot knows.
