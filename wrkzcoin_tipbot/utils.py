import asyncio
import datetime
import difflib
import re
from enum import Enum
import sys, traceback

import discord
import numpy as np
from discord.embeds import _EmptyEmbed
from discord.ext.commands import BadArgument, Converter
from dislash import InteractionClient, ActionRow, Button, ButtonStyle
import dislash

class MemberLookupConverter(discord.ext.commands.MemberConverter):
    async def convert(self, ctx, mem, guild: discord.Guild = None) -> discord.Member:
        if not ctx.guild:
            ctx.guild = guild

        if not mem.isdigit():
            if isinstance(mem, str):
                members = ctx.guild.members
                if len(mem) > 5 and mem[-5] == '#':
                    # The 5 length is checking to see if #0000 is in the string,
                    # as a#0000 has a length of 6, the minimum for a potential
                    # discriminator lookup.
                    potential_discriminator = mem[-4:]

                    # do the actual lookup and return if found
                    # if it isn't found then we'll do a full name lookup below.
                    result = discord.utils.get(members, name=mem[:-5], discriminator=potential_discriminator)
                    if result is not None:
                        return result

                def pred(m):
                    if m.nick:
                        if " | " in m.nick:
                            names = m.nick.split(" | ")
                            for n in names:
                                if "".join([m.lower() for m in n if m.isalpha()]) == mem:
                                    return True
                        else:
                            if "".join([m.lower() for m in m.nick if m.isalpha()]) == mem:
                                return True
                    return False

                res = discord.utils.find(pred, members)
                if res is not None:
                    return res

            try:
                member = await super().convert(ctx, mem)  # Convert parameter to discord.member
                return member
            except discord.ext.commands.BadArgument:
                pass

            nicks = []
            mems = []
            for m in ctx.guild.members:
                if m.nick:
                    nicks.append(m.nick.lower())
                    mems.append(m)

            res = difflib.get_close_matches(mem.lower(), nicks, n=1, cutoff=0.8)
            if res:
                index = nicks.index(res[0])
                return mems[index]

            desc = f"No members found with the name: {mem}. "
            raise BadArgument(desc)
        else:
            try:
                member = await super().convert(ctx, mem)  # Convert parameter to discord.member
                return member
            except discord.ext.commands.BadArgument:
                raise BadArgument(f"No members found with the name: {mem}"
                                  "Check your spelling and try again!")


class EmbedPaginatorInter:

    def __init__(self, bot, inter, pages):
        self.bot = bot
        self.inter = inter
        self.pages = pages
        self.msg = None


    async def paginate_with_slash(self):
        if self.pages:
            pagenum = 0
            embed: discord.Embed = self.pages[pagenum]
            if not isinstance(embed.title, _EmptyEmbed):
                if f" (Page {pagenum + 1}/{len(self.pages)})" not in str(embed.title):
                    embed.title = embed.title + f" (Page {pagenum + 1}/{len(self.pages)})"
            else:
                embed.title = f" (Page {pagenum + 1}/{len(self.pages)})"

            # Create a row of buttons
            row = ActionRow(
                Button(
                    style=ButtonStyle.blurple,
                    label="⏪",
                    custom_id="first_page"
                ),
                Button(
                    style=ButtonStyle.blurple,
                    label="◀️",
                    custom_id="step_back_page"
                ),
                Button(
                    style=ButtonStyle.blurple,
                    label="⏹️",
                    custom_id="stop_page"
                ),
                Button(
                    style=ButtonStyle.blurple,
                    label="▶️",
                    custom_id="step_forward_page"
                ),
                Button(
                    style=ButtonStyle.blurple,
                    label="⏩",
                    custom_id="last_page"
                )
            )

            # Note that we assign a list of rows to components
            if hasattr(self.inter, 'message'):
                self.msg = await self.inter.send(embed=self.pages[pagenum], components=[row])
            else:
                self.msg = await self.inter.reply(embed=self.pages[pagenum], components=[row], ephemeral=True)
            starttime = datetime.datetime.utcnow()

            while True:
                def check(inter):
                    return inter.author == self.inter.author

                try:
                    timeleft = 60  # 1 minute timeout
                    # Wait for a button click under the bot's message
                    inter = await self.bot.wait_for('button_click', check=check, timeout=timeleft)

                except asyncio.TimeoutError:
                    return await self.end_pagination_with_slash(self.msg)

                timeleft = timeleft - (datetime.datetime.utcnow() - starttime).seconds
                if inter.clicked_button.label == "◀️":
                    if pagenum == 0:
                        pagenum = len(self.pages) - 1
                    else:
                        pagenum -= 1
                elif inter.clicked_button.label == "▶️":
                    if pagenum == len(self.pages) - 1:
                        pagenum = 0
                    else:
                        pagenum += 1
                elif inter.clicked_button.label == "⏪":
                    pagenum = 0
                elif inter.clicked_button.label == "⏩":
                    pagenum = len(self.pages) - 1
                elif inter.clicked_button.label == "⏹️":
                    return await self.end_pagination_with_slash(inter)
                else:
                    continue

                embed: discord.Embed = self.pages[pagenum]
                if not isinstance(embed.title, _EmptyEmbed):
                    if f" (Page {pagenum + 1}/{len(self.pages)})" not in str(embed.title):
                        embed.title = embed.title + f" (Page {pagenum + 1}/{len(self.pages)})"
                else:
                    embed.title = f" (Page {pagenum + 1}/{len(self.pages)})"
                await inter.create_response(embed=self.pages[pagenum], components=[row], ephemeral=True, type=dislash.ResponseType.UpdateMessage)
                continue


    async def end_pagination_with_slash(self, inter):
        try:
            if hasattr(self.inter, 'message'):
                await inter.message.delete()
            else:
                await inter.message.delete()
        except Exception as e:
            print(traceback.format_exc())


class EmbedPaginator:

    def __init__(self, bot, ctx, pages):
        self.bot = bot
        self.ctx = ctx
        self.pages = pages


    async def paginate(self):
        if self.pages:
            pagenum = 0
            embed: discord.Embed = self.pages[pagenum]
            if not isinstance(embed.title, _EmptyEmbed):
                if f" (Page {pagenum + 1}/{len(self.pages)})" not in str(embed.title):
                    embed.title = embed.title + f" (Page {pagenum + 1}/{len(self.pages)})"
            else:
                embed.title = f" (Page {pagenum + 1}/{len(self.pages)})"
            msg = await self.ctx.send(embed=self.pages[pagenum])
            await msg.add_reaction("⏮️")
            await msg.add_reaction("⬅️")
            await msg.add_reaction("⏹️")
            await msg.add_reaction("➡️")
            await msg.add_reaction("⏭️")

            starttime = datetime.datetime.utcnow()
            timeleft = 300  # 5 minute timeout
            while True:
                def check(react, usr):
                    return not usr.bot and react.message.id == msg.id and usr.id == self.ctx.author.id and str(react.emoji) in \
                           ["⏮️", "⬅️", "⏹️", "➡️", "⏭️"]
                    
                try:
                    done, pending = await asyncio.wait([
                                        self.bot.wait_for('reaction_remove', timeout=timeleft, check=check),
                                        self.bot.wait_for('reaction_add', timeout=timeleft, check=check)
                                    ], return_when=asyncio.FIRST_COMPLETED)
                    # stuff = done.pop().result()
                    reaction, user = done.pop().result()
                except asyncio.TimeoutError:
                    return await self.end_pagination(msg)

                if msg.guild:
                    try:
                        await msg.remove_reaction(reaction.emoji, self.ctx.author)
                    except:
                        pass
                timeleft = 300 - (datetime.datetime.utcnow() - starttime).seconds
                if str(reaction.emoji) == "⬅️":
                    if pagenum == 0:
                        pagenum = len(self.pages) - 1
                    else:
                        pagenum -= 1
                elif str(reaction.emoji) == "➡️":
                    if pagenum == len(self.pages) - 1:
                        pagenum = 0
                    else:
                        pagenum += 1
                elif str(reaction.emoji) == "⏮️":
                    pagenum = 0
                elif str(reaction.emoji) == "⏭️":
                    pagenum = len(self.pages) - 1
                elif str(reaction.emoji) == "⏹️":
                    return await self.end_pagination(msg)
                else:
                    continue

                embed: discord.Embed = self.pages[pagenum]
                if not isinstance(embed.title, _EmptyEmbed):
                    if f" (Page {pagenum + 1}/{len(self.pages)})" not in str(embed.title):
                        embed.title = embed.title + f" (Page {pagenum + 1}/{len(self.pages)})"
                else:
                    embed.title = f" (Page {pagenum + 1}/{len(self.pages)})"
                await msg.edit(embed=self.pages[pagenum])


    async def end_pagination(self, msg):
        try:
            if self.pages:
                await msg.edit(embed=self.pages[0])
            if not isinstance(msg.channel, discord.DMChannel):
                try:
                    await msg.delete()
                except:
                    pass
        except discord.NotFound:
            pass


    async def paginate_with_button(self):
        if self.pages:
            pagenum = 0
            embed: discord.Embed = self.pages[pagenum]
            if not isinstance(embed.title, _EmptyEmbed):
                if f" (Page {pagenum + 1}/{len(self.pages)})" not in str(embed.title):
                    embed.title = embed.title + f" (Page {pagenum + 1}/{len(self.pages)})"
            else:
                embed.title = f" (Page {pagenum + 1}/{len(self.pages)})"

            # Create a row of buttons
            row = ActionRow(
                Button(
                    style=ButtonStyle.red,
                    label="⏮️",
                    custom_id="first_page"
                ),
                Button(
                    style=ButtonStyle.blurple,
                    label="⬅️",
                    custom_id="step_back_page"
                ),
                Button(
                    style=ButtonStyle.blurple,
                    label="⏹️",
                    custom_id="stop_page"
                ),
                Button(
                    style=ButtonStyle.blurple,
                    label="➡️",
                    custom_id="step_forward_page"
                ),
                Button(
                    style=ButtonStyle.blurple,
                    label="⏭️",
                    custom_id="last_page"
                )
            )

            # Note that we assign a list of rows to components
            msg = await self.ctx.send(embed=self.pages[pagenum], components=[row])
            first_shown = True
            starttime = datetime.datetime.utcnow()
            timeleft = 60  # 1 minute timeout
            while True:
                def check(inter):
                    return inter.author == self.ctx.author
                    
                try:
                    # Wait for a button click under the bot's message
                    inter = await self.bot.wait_for('button_click', check=check, timeout=timeleft)

                    # Respond to the interaction
                    # await inter.reply(
                    #    f"Your choice: {inter.clicked_button.label}",
                    #    components=[] # This is how you remove buttons
                    #)
                except asyncio.TimeoutError:
                    return await self.end_pagination_with_button(msg)

                timeleft = timeleft - (datetime.datetime.utcnow() - starttime).seconds
                if inter.clicked_button.label == "⬅️":
                    if pagenum == 0:
                        pagenum = len(self.pages) - 1
                    else:
                        pagenum -= 1
                elif inter.clicked_button.label == "➡️":
                    if pagenum == len(self.pages) - 1:
                        pagenum = 0
                    else:
                        pagenum += 1
                elif inter.clicked_button.label == "⏮️":
                    pagenum = 0
                elif inter.clicked_button.label == "⏭️":
                    pagenum = len(self.pages) - 1
                elif inter.clicked_button.label == "⏹️":
                    return await self.end_pagination_with_button(inter)
                else:
                    continue

                embed: discord.Embed = self.pages[pagenum]
                if not isinstance(embed.title, _EmptyEmbed):
                    if f" (Page {pagenum + 1}/{len(self.pages)})" not in str(embed.title):
                        embed.title = embed.title + f" (Page {pagenum + 1}/{len(self.pages)})"
                else:
                    embed.title = f" (Page {pagenum + 1}/{len(self.pages)})"
                if first_shown == True:
                    await msg.delete()
                    first_shown = False
                    await inter.reply(embed=self.pages[pagenum], components=[row])
                else:
                    await inter.create_response(embed=self.pages[pagenum], components=[row], type=dislash.ResponseType.UpdateMessage)
                #await msg.edit(embed=self.pages[pagenum], components=[row])
                continue


    async def end_pagination_with_button(self, inter):
        try:
            await inter.message.delete()
        except discord.NotFound:
            pass




def build_duration(**kwargs):
    """Converts a dict with the keys defined in `Duration` to a timedelta
    object. Here we assume a month is 30 days, and a year is 365 days.
    """
    weeks = kwargs.get('weeks', 0)
    days = 365 * kwargs.get('years', 0) + 30 * kwargs.get('months', 0) + kwargs.get('days')
    hours = kwargs.get('hours', 0)
    minutes = kwargs.get('minutes', 0)
    seconds = kwargs.get('seconds', 0)

    return datetime.timedelta(days=days, seconds=seconds, minutes=minutes, hours=hours, weeks=weeks, )


class Duration(Converter):
    """Convert duration strings into UTC datetime.datetime objects.
    Inspired by the https://github.com/python-discord/bot repository.
    """

    duration_parser = re.compile(r"((?P<years>\d+?) ?(years|year|Y|y) ?)?"
                                 r"((?P<months>\d+?) ?(months|month|M) ?)?"  # switched m to M
                                 r"((?P<weeks>\d+?) ?(weeks|week|W|w) ?)?"
                                 r"((?P<days>\d+?) ?(days|day|D|d) ?)?"
                                 r"((?P<hours>\d+?) ?(hours|hour|H|h) ?)?"
                                 r"((?P<minutes>\d+?) ?(minutes|minute|min|m) ?)?"  # switched M to m
                                 r"((?P<seconds>\d+?) ?(seconds|second|S|s))?")

    async def convert(self, ctx, duration: str) -> datetime.datetime:
        """
        Converts a `duration` string to a datetime object that's
        `duration` in the future.
        The converter supports the following symbols for each unit of time:
        - years: `Y`, `y`, `year`, `years`
        - months: `m`, `month`, `months`
        - weeks: `w`, `W`, `week`, `weeks`
        - days: `d`, `D`, `day`, `days`
        - hours: `H`, `h`, `hour`, `hours`
        - minutes: `m`, `minute`, `minutes`, `min`
        - seconds: `S`, `s`, `second`, `seconds`
        The units need to be provided in **descending** order of magnitude.
        """
        match = self.duration_parser.fullmatch(duration)
        if not match:
            raise BadArgument(f"`{duration}` is not a valid duration string.")

        duration_dict = {unit: int(amount) for unit, amount in match.groupdict(default=0).items()}
        delta = build_duration(**duration_dict)
        now = datetime.datetime.utcnow()

        return now + delta


def textProgressBar(iteration, total, prefix='```yml\nProgress:  ', percent_suffix="", suffix='\n```', decimals=1, length=100, fullisred=True, empty="<:gray:736515579103543336>"):
    """
    Call in a loop to create progress bar
    @params:
        iteration        - Required  : current iteration (Int)
        total            - Required  : total iterations (Int)
        prefix           - Optional  : prefix string (Str)
        percent_suffix   - Optional  : percent suffix (Str)
        suffix           - Optional  : suffix string (Str)
        decimals         - Optional  : positive number of decimals in percent complete (Int)
        length           - Optional  : character length of bar (Int)
        fill             - Optional  : bar fill character (Str)
        empty            - Optional  : bar empty character (Str)
    """
    iteration = total if iteration > total else iteration
    percent = 100 * (iteration / float(total))
    s_percent = ("{0:." + str(decimals) + "f}").format(percent)
    if fullisred:
        fill = "<:green:736390154549329950>" if percent <= 34 else "<:yellow:736390576932651049>" if percent <= 67 else "<:orange:736390576789782620>" \
            if percent <= .87 else "<:red:736390576978788363>"
    else:
        fill = "<:red:736390576978788363>" if percent <= 34 else "<:orange:736390576789782620>" if percent <= 67 else "<:yellow:736390576932651049>" \
            if percent <= .87 else "<:green:736390154549329950>"

    filledLength = int(length * iteration // total)
    bar = fill * filledLength + empty * (length - filledLength)
    res = f'{prefix} {bar} - {s_percent}% {percent_suffix} {suffix}' if percent_suffix != "" else f'\r{prefix}\n{bar}{suffix}'
    return res
