import sys
import traceback
from datetime import datetime, timedelta
import time

import disnake
from disnake.ext import commands
from disnake.enums import OptionType
from disnake.app_commands import Option, OptionChoice

from Bot import *


class Core(commands.Cog):
    """Houses core commands & listeners for the bot"""

    def __init__(self, bot):
        self.bot = bot
        

    async def get_uptime(
        self,
        ctx
    ):
        uptime_seconds = int(time.time()) - int(bot_start_time)
        msg = await ctx.reply(f"{EMOJI_INFORMATION} {ctx.author.mention}, Current Uptime: {'{:0>8}'.format(str(timedelta(seconds=uptime_seconds)))}")


    @commands.guild_only()
    @commands.slash_command(
        usage="uptime", 
        description="Tells how long the bot has been running."
    )
    async def uptime(
        self, 
        ctx
    ):
        get_uptime = await self.get_uptime(ctx)
        if get_uptime and "error" in get_uptime:
            msg = await ctx.reply(get_uptime['error'])


    @commands.guild_only()
    @commands.command(
        usage="uptime", 
        description="Tells how long the bot has been running."
    )
    async def uptime(self, ctx):
        get_uptime = await self.get_uptime(ctx)
        if get_uptime and "error" in get_uptime:
            msg = await ctx.reply(get_uptime['error'])


    @commands.dm_only()
    @commands.command(
        name='commands', 
        usage="commands", 
        description="View a full list of all available commands.",
        aliases=["cmd"]
    )
    async def commandlist(self, ctx):
        embed = disnake.Embed(title="Command List", description="A full list of all available commands.\n", color=disnake.Color.teal())
        for _, cog_name in enumerate(sorted(self.bot.cogs)):
            if cog_name in ["Owner", "Admin"]:
                continue
            cog = self.bot.get_cog(cog_name)
            cog_commands = cog.get_commands()
            if len(cog_commands) == 0:
                continue
            cmds = "```yml\n" + ", ".join([ctx.prefix + cmd.name for cmd in cog_commands]) + "```"
            embed.add_field(name=cog.qualified_name + " Commands", value=cmds, inline=False)
        msg = await ctx.reply(embed=embed)


def setup(bot):
    bot.add_cog(Core(bot))
