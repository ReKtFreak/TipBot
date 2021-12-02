import sys, traceback
import math, random

import discord
from discord.ext import commands
from dislash import InteractionClient, Option, OptionType

from config import config
from Bot import *


class RandomNumber(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    async def rand_number(
        self,
        ctx,
        number_string: str=None
    ):
        rand_numb = None
        if number_string is None:
            rand_numb = random.randint(1, 100)
        else:
            number_string = number_string.replace(",", "")
            rand_min_max = number_string.split("-")
            if len(rand_min_max) <= 1:
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid range given. Example, use: `rand 1-50`')
                return
            try:
                min_numb = int(rand_min_max[0])
                max_numb = int(rand_min_max[1])
                if max_numb - min_numb <= 0:
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid range given. Example, use: `rand 1-50`')
                    return
                else:
                    rand_numb = random.randint(min_numb,max_numb)
            except ValueError:
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid range given. Example, use: `rand 1-50`')
                return
        if rand_numb:
            try:
                msg = await ctx.reply('{} Random number: **{:,}**'.format(ctx.author.mention, rand_numb))
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                return


    @inter_client.slash_command(usage="rand [1-100]",
                                options=[
                                    Option("range_number", "Enter a range from to (ex. 1-100)", OptionType.STRING, required=False)
                                ],
                                description="Generate a random number with TipBot.")
    async def rand(
        self, 
        ctx, 
        range_number: str=None
    ):
        await self.rand_number(ctx, range_number)


    @commands.command(
        usage="random [1-100]", 
        aliases=['random'], 
        description="Generate a random number with TipBot."
    )
    async def rand(
        self, 
        ctx, 
        randstring: str = None
    ):
        await self.rand_number(ctx, randstring)


def setup(bot):
    bot.add_cog(RandomNumber(bot))