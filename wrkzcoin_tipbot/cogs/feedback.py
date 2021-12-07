import sys
import traceback

import discord
from discord.ext import commands
from Bot import *

from config import config

class Feedback(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.botLogChan = self.bot.get_channel(LOG_CHAN)


    async def bot_log(self):
        if self.botLogChan is None:
            self.botLogChan = self.bot.get_channel(LOG_CHAN)


    @commands.group(
        usage="feedback", 
        aliases=['fb'], 
        description="Submit a feedback."
    )
    async def feedback(self, ctx):
        await self.bot_log()
        prefix = await get_guild_prefix(ctx)
        if ctx.invoked_subcommand is None:
            if config.feedback_setting.enable != 1:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{ctx.author.mention} Feedback is not enable right now. Check back later.')
                return

            # Check if user has submitted any and reach limit
            check_feedback_user = await store.sql_get_feedback_count_last(str(ctx.author.id), config.feedback_setting.intervial_last_10mn_s)
            if check_feedback_user and check_feedback_user >= config.feedback_setting.intervial_last_10mn:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{ctx.author.mention} You had submitted {config.feedback_setting.intervial_last_10mn} already. '
                               'Waiting a bit before next submission.')
                return
            check_feedback_user = await store.sql_get_feedback_count_last(str(ctx.author.id), config.feedback_setting.intervial_each_user)
            if check_feedback_user and check_feedback_user >= 1:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{ctx.author.mention} You had submitted one feedback already for the last {config.feedback_setting.intervial_each_user}s.'
                               'Waiting a bit before next submission.')
                return
            # OK he can submitted
            try:
                msg = await ctx.reply(f'{ctx.author.mention} We are welcome for all feedback, inquiry or suggestion. '
                                     f'You can also join our support server as in {prefix}about command.\n'
                                     f'Please type in your feedback here (timeout {config.feedback_setting.waiting_for_feedback_text}s):')
                # DESC
                feedback = None
                while feedback is None:
                    waiting_feedbackmsg = None
                    try:
                        waiting_feedbackmsg = await self.bot.wait_for('message', timeout=config.feedback_setting.waiting_for_feedback_text, check=lambda msg: msg.author == ctx.author)
                    except asyncio.TimeoutError:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.reply(f'{ctx.author.mention} **Timeout** for feedback submission. '
                                       'You can try again later.')
                        return
                    if waiting_feedbackmsg is None:
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.reply(f'{ctx.author.mention} **Timeout** for feedback submission. '
                                       'You can try again later.')
                        return
                    else:
                            feedback = waiting_feedbackmsg.content.strip()
                            if len(feedback) <= config.feedback_setting.min_chars:
                                await ctx.message.add_reaction(EMOJI_ERROR)
                                msg = await ctx.reply(f'{ctx.author.mention}, feedback message is too short.')
                                return
                            else:
                                # OK, let's add
                                feedback_id = str(uuid.uuid4())
                                text_in = "DM"
                                if isinstance(ctx.channel, discord.DMChannel) == False: text_in = str(ctx.channel.id)
                                howto_contact_back = "N/A"
                                msg = await ctx.reply(f'{ctx.author.mention} (Optional) Please let us know if and how we can contact you back '
                                                     f'(timeout {config.feedback_setting.waiting_for_feedback_text}s) - default N/A:')
                                try:
                                    waiting_howtoback = await self.bot.wait_for('message', timeout=config.feedback_setting.waiting_for_feedback_text, check=lambda msg: msg.author == ctx.author)
                                except asyncio.TimeoutError:
                                    pass
                                else:
                                    if len(waiting_howtoback.content.strip()) > 0: howto_contact_back = waiting_howtoback.content.strip()
                                add = await store.sql_feedback_add(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                                   feedback_id, text_in, feedback, howto_contact_back)
                                if add:
                                    msg = await ctx.reply(f'{ctx.author.mention} Thank you for your feedback / inquiry. Your feedback ref: **{feedback_id}**')
                                    await msg.add_reaction(EMOJI_OK_BOX)
                                    await self.botLogChan.send(f'{EMOJI_INFORMATION} A user has submitted a feedback `{feedback_id}`')
                                    return
                                else:
                                    msg = await ctx.reply(f'{ctx.author.mention} Internal Error.')
                                    await msg.add_reaction(EMOJI_OK_BOX)
            except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                await ctx.message.add_reaction(EMOJI_ERROR)
                return


    @feedback.command(
        usage="feedback view <ref>", 
        aliases=['vfb'], 
        description="View a feedback."
    )
    @commands.is_owner()
    async def view(
        self, 
        ctx, 
        ref: str
    ):
        if config.feedback_setting.enable != 1:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} Feedback is not enable right now. Check back later.')
            return
        get_feedback = await store.sql_feedback_by_ref(ref)
        if get_feedback is None:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} We can not find feedback reference **{ref}**.')
            return
        else:
            # If he is bot owner or feedback owner:
            if int(get_feedback['user_id']) == ctx.author.id or ctx.author.id == OWNER_ID_TIPBOT:
                response_txt = 'Feedback ref: **{}** submitted by user id: {}, name: {}\n'.format(ref, get_feedback['user_id'], get_feedback['user_name'])
                response_txt += 'Content:\n\n{}\n\n'.format(get_feedback['feedback_text'])
                response_txt += 'Submitted date: {}'.format(datetime.fromtimestamp(get_feedback['feedback_date']))
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                msg = await ctx.reply(f'{response_txt}')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{ctx.author.mention} You do not have permission to view **{ref}**.')
                return


    @feedback.command(
        usage="feedback list", 
        aliases=['ls'], 
        description="List feedback."
    )
    @commands.is_owner()
    async def list(
        self, 
        ctx, 
        userid: str=None
    ):
        if config.feedback_setting.enable != 1:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} Feedback is not enable right now. Check back later.')
            return
        if userid is None:
            get_feedback_list = await store.sql_feedback_list_by_user(str(ctx.author.id), 10)
            if get_feedback_list and len(get_feedback_list) > 0:
                table_data = [['Ref', 'Brief']]
                for each in get_feedback_list:
                    table_data.append([each['feedback_id'], each['feedback_text'][0:48]])
                table = AsciiTable(table_data)
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                msg = await ctx.reply(f'{ctx.author.mention} Your feedback list:```{table.table}```')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{ctx.author.mention} You do not have any feedback submitted.')
                return
        else:
            if ctx.author.id != OWNER_ID_TIPBOT:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{ctx.author.mention} You have no permission.')
                return
            else:
                get_feedback_list = await store.sql_feedback_list_by_user(userid, 10)
                if get_feedback_list and len(get_feedback_list) > 0:
                    table_data = [['Ref', 'Brief']]
                    for each in get_feedback_list:
                        table_data.append([each['feedback_id'], each['feedback_text'][0:48]])
                    table = AsciiTable(table_data)
                    await ctx.message.add_reaction(EMOJI_OK_HAND)
                    msg = await ctx.reply(f'{ctx.author.mention} Feedback user {userid} list:```{table.table}```')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.reply(f'{ctx.author.mention} There is no feedback by {userid}.')
                    return


def setup(bot):
    bot.add_cog(Feedback(bot))