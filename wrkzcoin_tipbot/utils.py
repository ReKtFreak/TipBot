import asyncio
import datetime
import difflib
import re
from enum import Enum
import sys, traceback

import disnake
import numpy as np
from disnake.embeds import _EmptyEmbed
from disnake.ext.commands import BadArgument, Converter

from disnake import ActionRow, Button, ButtonStyle
from disnake.enums import OptionType
from disnake.app_commands import Option, OptionChoice
from typing import List


# Defines a simple paginator of buttons for the embed.
class MenuPage(disnake.ui.View):
    def __init__(self, inter, embeds: List[disnake.Embed]):
        super().__init__(timeout=None)
        self.inter = inter

        # Sets the embed list variable.
        self.embeds = embeds

        # Current embed number.
        self.embed_count = 0

        # Disables previous page button by default.
        self.prev_page.disabled = True
        
        self.first_page.disabled = True

        # Sets the footer of the embeds with their respective page numbers.
        for i, embed in enumerate(self.embeds):
            embed.set_footer(text=f"Page {i + 1} of {len(self.embeds)}")


    @disnake.ui.button(label="⏪", style=disnake.ButtonStyle.red)
    async def first_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.author != self.inter.author:
            return

        # Decrements the embed count.
        self.embed_count = 0

        # Gets the embed object.
        embed = self.embeds[self.embed_count]
        
        self.last_page.disabled = False

        # Enables the next page button and disables the previous page button if we're on the first embed.
        self.next_page.disabled = False
        if self.embed_count == 0:
            self.prev_page.disabled = True
            self.first_page.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


    @disnake.ui.button(label="◀️", style=disnake.ButtonStyle.red)
    async def prev_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.author != self.inter.author:
            return

        # Decrements the embed count.
        self.embed_count -= 1

        # Gets the embed object.
        embed = self.embeds[self.embed_count]
        
        self.last_page.disabled = False

        # Enables the next page button and disables the previous page button if we're on the first embed.
        self.next_page.disabled = False
        if self.embed_count == 0:
            self.prev_page.disabled = True
            self.first_page.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    # @disnake.ui.button(label="⏹️", style=disnake.ButtonStyle.red)
    @disnake.ui.button(label="⏹️", style=disnake.ButtonStyle.red)
    async def remove(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.author != self.inter.author:
            return
        #await interaction.response.edit_message(view=None)
        await interaction.message.delete()


    # @disnake.ui.button(label="", emoji="▶️", style=disnake.ButtonStyle.green)
    @disnake.ui.button(label="▶️", style=disnake.ButtonStyle.green)
    async def next_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.author != self.inter.author:
            return
        # Increments the embed count.
        self.embed_count += 1

        # Gets the embed object.
        embed = self.embeds[self.embed_count]

        # Enables the previous page button and disables the next page button if we're on the last embed.
        self.prev_page.disabled = False
        
        self.first_page.disabled = False

        if self.embed_count == len(self.embeds) - 1:
            self.next_page.disabled = True
            self.last_page.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


    @disnake.ui.button(label="⏩", style=disnake.ButtonStyle.green)
    async def last_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if interaction.author != self.inter.author:
            return
        # Increments the embed count.
        self.embed_count = len(self.embeds) - 1

        # Gets the embed object.
        embed = self.embeds[self.embed_count]
        
        self.first_page.disabled = False

        # Enables the previous page button and disables the next page button if we're on the last embed.
        self.prev_page.disabled = False
        if self.embed_count == len(self.embeds) - 1:
            self.next_page.disabled = True
            self.last_page.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


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
