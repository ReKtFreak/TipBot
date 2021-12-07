import sys, traceback

import discord
from discord.ext import commands
from dislash import InteractionClient, Option, OptionType
import dislash

from config import config
from Bot import *


class Calculator(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @inter_client.slash_command(usage="cal <expression>",
                                options=[
                                    Option("eval_string", "Math to evaluate", OptionType.STRING, required=True)
                                ],
                                description="Do some math.")
    async def cal(
        self, 
        ctx, 
        eval_string: str = None
    ):
        if isinstance(ctx.channel, discord.DMChannel) == True:
            return
        if eval_string is None:
            await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention}, Example: `cal 2+3+4/2`')
            return
        else:
            eval_string_original = eval_string
            eval_string = eval_string.replace(",", "")
            supported_function = ['+', '-', '*', '/', '(', ')', '.', ',']
            additional_support = ['exp', 'sqrt', 'abs', 'log10', 'log', 'sinh', 'cosh', 'tanh', 'sin', 'cos', 'tan']
            test_string = eval_string
            for each in additional_support:
                test_string = test_string.replace(each, "")
            if all([c.isdigit() or c in supported_function for c in test_string]):
                try:
                    result = numexpr.evaluate(eval_string).item()
                    msg = await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} result of `{eval_string_original}`:```{result}```')
                    await msg.add_reaction(EMOJI_OK_BOX)
                except Exception as e:
                    await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} I can not find the result for `{eval_string_original}`.')
                return
            else:
                await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} Unsupported usage for `{eval_string_original}`.')
            return


    @commands.command(
        usage="cal <expression>", 
        aliases=['calc', 'calculate'], 
        description="Do some math."
    )
    async def cal(
        self, 
        ctx, 
        eval_string: str = None
    ):
        if isinstance(ctx.channel, discord.DMChannel) == True:
            return
        if eval_string is None:
            await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention}, Example: `cal 2+3+4/2`')
            return
        else:
            eval_string_original = eval_string
            eval_string = eval_string.replace(",", "")
            supported_function = ['+', '-', '*', '/', '(', ')', '.', ',']
            additional_support = ['exp', 'sqrt', 'abs', 'log10', 'log', 'sinh', 'cosh', 'tanh', 'sin', 'cos', 'tan']
            test_string = eval_string
            for each in additional_support:
                test_string = test_string.replace(each, "")
            if all([c.isdigit() or c in supported_function for c in test_string]):
                try:
                    result = numexpr.evaluate(eval_string).item()
                    msg = await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} result of `{eval_string_original}`:```{result}```')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                except Exception as e:
                    await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} I can not find the result for `{eval_string_original}`.')
                    return
            else:
                await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} Unsupported usage for `{eval_string_original}`.')
                return


def setup(bot):
    bot.add_cog(Calculator(bot))