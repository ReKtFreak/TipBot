import sys, traceback
import math, random

import discord
from discord.ext import commands

from config import config
from Bot import *

class RandomNumber(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.command(
        usage="random <1-100>", 
        aliases=['random'], 
        description="Generate random number with TipBot."
    )
    async def rand(
        self, 
        ctx, 
        randstring: str = None
    ):
        rand_numb = None
        if randstring is None:
            rand_numb = random.randint(1,100)
        else:
            randstring = randstring.replace(",", "")
            rand_min_max = randstring.split("-")
            if len(rand_min_max) <= 1:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid range given. Example, use: `rand 1-50`')
                return
            try:
                min_numb = int(rand_min_max[0])
                max_numb = int(rand_min_max[1])
                if max_numb - min_numb <= 0:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid range given. Example, use: `rand 1-50`')
                    return
                else:
                    rand_numb = random.randint(min_numb,max_numb)
            except ValueError:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.send(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid range given. Example, use: `rand 1-50`')
                return
        if rand_numb:
            await ctx.message.add_reaction(EMOJI_OK_BOX)
            try:
                msg = await ctx.send('{} Random number: **{:,}**'.format(ctx.author.mention, rand_numb))
                await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                return


def setup(bot):
    bot.add_cog(RandomNumber(bot))