import datetime
import logging
import os
import secrets
import uuid

import discord
from discord.ext import commands

from HuskyBot import HuskyBot
from libhusky import HuskyUtils, HuskyChecks
from libhusky.HuskyStatics import *

LOG = logging.getLogger("HuskyBot.Plugin." + __name__)
CTF_PATH = "ctf"
FLAG_TEMPLATE = """
HuskyBot CTF Challenge
----------------------

Congratulations on managing to find the flag! Report the following flag to an administrator, or optionally 
use the `/ctf verify <flag>` command.

FLAG = {flag_key}

This flag was generated at {ts}.

--- BELOW IS NOT THE FLAG JUST IGNORE IT ---
{salt}
"""


class CTFChallenge(commands.Cog):
    """
    Welcome to the HuskyBot Bug Bounty!

    In order to get you started off with an idea, we have a little game of Capture The Flag. Hidden in the bot's base
    directory is a file, named "ctf". Inside of this file, you will find a secret flag that you'll need to give to the
    bot or an administrator.

    The flag file is a plaintext file, with standard Unix line endings (LF only). The flag itself is on a line that
    starts with "FLAG = ", and the flag will always be a UUID4 string. When you verify the flag, it will also be case
    sensitive. Additionally, the flag file contains a bunch of descriptive text, the exact time of generation, and a
    randomly generated salt. The hash of the ctf flag file is provided to you, just to make your job easier.

    When validating a flag, you have three guesses in a five minute period, so make them count! Run `/help ctf` to get a
    list of commands you can run.
    """

    def __init__(self, bot: HuskyBot):
        self.bot = bot
        self._config = bot.config
        self.generate_ctf_file()
        LOG.info("Loaded plugin!")

    def generate_ctf_file(self, force: bool = False):
        ctf_config = self._config.get('ctf', {})
        if os.path.isfile(CTF_PATH) and not force:
            LOG.debug("A CTF file already exists, so not regenerating.")
            return

        with open(CTF_PATH, 'w') as f:
            f.write(FLAG_TEMPLATE.format(
                flag_key=str(uuid.uuid4()),
                ts=HuskyUtils.get_timestamp(),
                salt=secrets.token_urlsafe(64)))

        ctf_config['pwned_by'] = None
        ctf_config['pwned_at'] = None
        self._config.set('ctf', ctf_config)

        LOG.info("Generated a CTF flag file!")

    @commands.group(name="ctf", brief="Base command for the CTF Challenge")
    async def ctf(self, ctx: commands.Context):
        """
        The base command for interacting with the CTF Challenge module. Please see sub-command help docs for more
        information. For information about the CTF challenge itself, please run `/help CTFChallenge`.
        """
        pass

    @ctf.command(name="hash", brief="Get the SHA1 hash of the CTF flag file.")
    async def get_file_hash(self, ctx: commands.Context):
        """
        This command will expose the SHA1 hash of the CTF flag file, and not much else.

        For information about what's in the flag file, do `/help CTFChallenge`.
        """
        if not os.path.isfile(CTF_PATH):
            await ctx.send(embed=discord.Embed(
                title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
                description=f"A CTF flag file does not currently exist. Please contact a bot admin.",
                color=Colors.DANGER
            ))
            return

        fhash = HuskyUtils.get_sha1_hash_of_file(CTF_PATH)

        await ctx.send(embed=discord.Embed(
            title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
            description=f"The flag file's SHA1 hash is: \n```{fhash}```",
            color=Colors.SUCCESS
        ))

    @ctf.command(name="verify", brief="Attempt to verify a stolen flag")
    @commands.cooldown(3, 300, commands.BucketType.user)
    async def verify_flag(self, ctx: commands.Context, suspect_flag: str):
        """
        This command attempts to verify a stolen flag against the CTF file. To prevent abuse, this command may only be
        run three times every five minutes.

        Parameters
        ----------
            ctx          :: discord context <!nodoc>
            suspect_flag :: The flag string to test against

        Examples
        --------
            /ctf verify some_dumb_flag :: Check if the string some_dumb_flag is the CTF flag.
        """
        ctf_config = self._config.get('ctf', {})

        if not os.path.isfile(CTF_PATH):
            await ctx.send(embed=discord.Embed(
                title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
                description=f"A CTF flag file does not currently exist. Please contact a bot admin.",
                color=Colors.DANGER
            ))
            return

        with open(CTF_PATH, 'r') as flag_file:
            for line in flag_file:
                if line.startswith("FLAG = "):
                    flag_line = line
                    break
            else:
                await ctx.send(embed=discord.Embed(
                    title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
                    description=f"The CTF file is malformed or invalid. Contact a bot admin.",
                    color=Colors.DANGER
                ))
                return

        if not flag_line:
            await ctx.send(embed=discord.Embed(
                title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
                description=f"The CTF file is malformed or invalid. Contact a bot admin.",
                color=Colors.DANGER
            ))
            return

        if ctf_config.get('pwned_by'):
            await ctx.send(embed=discord.Embed(
                title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
                description=f"The flag file can't be verified because it's already been pwned.",
                color=Colors.WARNING
            ))
            return

        flag = flag_line.split(" ")[2].strip()

        if suspect_flag.upper() != flag.upper():
            await ctx.send(embed=discord.Embed(
                title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
                description=f"The flag you have entered is not correct. Keep on trying!",
                color=Colors.WARNING
            ))
            return

        admin_role = ctx.guild.get_role(self._config.get("specialRoles", {}).get(SpecialRoleKeys.ADMINS.value))
        await ctx.send((admin_role.mention if admin_role else ""), embed=discord.Embed(
            title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
            description=f"Congratulations! You've successfully extracted the flag! {Emojis.PARTY}\n\nAn admin will "
                        f"DM you shortly to discuss this exploit, and ensure you can claim your prize.",
            color=Colors.SUCCESS
        ))

        ctf_config['pwned_by'] = ctx.author.id
        ctf_config['pwned_at'] = datetime.datetime.now().timestamp()
        self._config.set('ctf', ctf_config)

    @ctf.command(name="generate", brief="Generate a new CTF flag file.")
    @HuskyChecks.is_superuser()
    async def generate_flag(self, ctx: commands.Context):
        """
        When necessary, this command allows the bot to generate a new flag file for internal use. This command will
        invalidate the existing flag file entirely.
        """
        self.generate_ctf_file(True)
        fh = HuskyUtils.get_sha1_hash_of_file(CTF_PATH)

        await ctx.send(embed=discord.Embed(
            title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
            description=f"The flag file has been generated. The file's hash is `{fh[-8:]}`.",
            color=Colors.SUCCESS
        ))

    @ctf.command(name="status", brief="Get the pwn state of the flag.")
    @HuskyChecks.is_superuser()
    async def get_pwn_state(self, ctx: commands.Context):
        ctf_config = self._config.get('ctf', {})

        if not ctf_config.get('pwned_by'):
            await ctx.send(embed=discord.Embed(
                title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
                description=f"The flag file has yet to be pwned.",
                color=Colors.SUCCESS
            ))
            return

        user = await self.bot.fetch_user(ctf_config.get('pwned_by'))

        embed = discord.Embed(
            title=Emojis.RED_FLAG + " HuskyBot CTF Challenge",
            description="The HuskyBot CTF flag file has been successfully pwned.",
            color=Colors.WARNING
        )

        if user:
            embed.add_field(
                name="Pwning User",
                value=user.mention if ctx.guild.get_member(user.id) else str(user),
                inline=True
            )
            embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(name="User ID", value=ctf_config.get('pwned_by'), inline=True)
        embed.add_field(
            name="Pwning Date",
            value=datetime.datetime.utcfromtimestamp(ctf_config.get('pwned_at')).strftime(DATETIME_FORMAT),
            inline=False
        )

        await ctx.send(embed=embed)


def setup(bot: HuskyBot):
    bot.add_cog(CTFChallenge(bot))
