import sys, traceback
import time, timeago
import discord
from discord.ext import commands

from config import config
from Bot import *

class TipTag(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    ## TODO: Improve this usage.
    @commands.command(usage="tag <arguments>", description="Manage or display tag(s).")
    async def tag(self, ctx, *args):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{ctx.author.mention} {EMOJI_RED_NO} This command can not be in private.')
            return

        ListTag = await store.sql_tag_by_server(str(ctx.guild.id), None)

        if len(args) == 0:
            if len(ListTag) > 0:
                tags = (', '.join([w['tag_id'] for w in ListTag])).lower()
                msg = await ctx.reply(f'{ctx.author.mention} Available tag: `{tags}`.\nPlease use `.tag tagname` to show it in detail.'
                                    'If you have permission to manage discord server.\n'
                                    'Use: `.tag -add|del tagname <Tag description ... >`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            else:
                msg = await ctx.reply(f'{ctx.author.mention} There is no tag in this server. Please add.\n'
                                    'If you have permission to manage discord server.\n'
                                    'Use: `.tag -add|-del tagname <Tag description ... >`')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        elif len(args) == 1 or len(ctx.message.mentions) > 0:
            # if .tag test
            TagIt = await store.sql_tag_by_server(str(ctx.guild.id), args[0].upper())
            # If there is mention
            mention_users = None
            if len(ctx.message.mentions) > 0:
                try:
                    mention_users = ''
                    for each_user in ctx.message.mentions:
                        mention_users += '<@{}>, '.format(str(each_user.id))
                except Exception as e:
                    print(traceback.format_exc())
                    await logchanbot(traceback.format_exc())
            if TagIt:
                tagDesc = TagIt['tag_desc']
                try:
                    if mention_users:
                        msg = await ctx.reply(f'{mention_users} {ctx.author.mention} {tagDesc}')
                    else:
                        msg = await ctx.reply(f'{ctx.author.mention} {tagDesc}')
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                    await ctx.message.add_reaction(EMOJI_ZIPPED_MOUTH)
                except Exception as e:
                    print(traceback.format_exc())
                    await logchanbot(traceback.format_exc())
                return
            else:
                msg = await ctx.reply(f'{ctx.author.mention} There is no tag {args[0]} in this server.\n'
                                    'If you have permission to manage discord server.\n'
                                    'Use: ```.tag -add|-del tagname <Tag description ... >```')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
        if (args[0].lower() in ['-add', '-del']) and (ctx.author.guild_permissions.manage_guild == False and ctx.author.guild_permissions.view_guild_insights == False):
            msg = await ctx.reply(f'{ctx.author.mention} Permission denied.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        if args[0].lower() == '-add' and (ctx.author.guild_permissions.manage_guild or ctx.author.guild_permissions.view_guild_insights):
            if re.match('^[a-zA-Z0-9]+(-[a-zA-Z0-9]+)*$', args[1]):
                tag = args[1].upper()
                if len(tag) >= 32:
                    await ctx.reply(f'{ctx.author.mention} Tag ***{args[1]}*** is too long.')
                    return

                tagDesc = ctx.message.content.strip()[(9 + len(tag) + 1):]
                if len(tagDesc) <= 3:
                    msg = await ctx.reply(f'{ctx.author.mention} Tag desc for ***{args[1]}*** is too short.')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                if len(ListTag) > 0:
                    d = [i['tag_id'] for i in ListTag]
                    if tag.upper() in d:
                        await ctx.reply(f'{ctx.author.mention} Tag **{args[1]}** already exists here.')
                        return
                addTag = await store.sql_tag_by_server_add(str(ctx.guild.id), tag.strip(), tagDesc.strip(),
                                                           ctx.author.name, str(ctx.author.id))
                if addTag is None:
                    msg = await ctx.reply(f'{ctx.author.mention} Failed to add tag **{args[1]}**')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                if addTag.upper() == tag.upper():
                    msg = await ctx.reply(f'{ctx.author.mention} Successfully added tag **{args[1]}**')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                else:
                    msg = await ctx.reply(f'{ctx.author.mention} Failed to add tag **{args[1]}**')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
            else:
                msg = await ctx.reply(f'{ctx.author.mention} Tag {args[1]} is not valid.')
                await msg.add_reaction(EMOJI_OK_BOX)
                return
            return
        elif args[0].lower() == '-del' and (ctx.author.guild_permissions.manage_guild or ctx.author.guild_permissions.view_guild_insights):
            #print('Has permission:' + str(ctx.message.content))
            if re.match('^[a-zA-Z0-9]+(-[a-zA-Z0-9]+)*$', args[1]):
                tag = args[1].upper()
                delTag = await store.sql_tag_by_server_del(str(ctx.guild.id), tag.strip())
                if delTag is None:
                    await ctx.reply(f'{ctx.author.mention} Failed to delete tag ***{args[1]}***')
                    return
                if delTag.upper() == tag.upper():
                    await ctx.reply(f'{ctx.author.mention} Successfully deleted tag ***{args[1]}***')
                    return
                else:
                    await ctx.reply(f'{ctx.author.mention} Failed to delete tag ***{args[1]}***')
                    return
            else:
                await ctx.reply(f'Tag {args[1]} is not valid.')
                return
            return


    @commands.command(
        usage="itag <arguments>", 
        description="Manage or display itag(s)."
    )
    async def itag(
        ctx, 
        *, 
        itag_text: str = None
    ):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.reply(f'{EMOJI_RED_NO} This command can not be in private.')
            return
        ListiTag = await store.sql_itag_by_server(str(ctx.guild.id))
        if not ctx.message.attachments:
            # Find available tag
            if itag_text is None:
                if len(ListiTag) > 0:
                    itags = (', '.join([w['itag_id'] for w in ListiTag])).lower()
                    await ctx.reply(f'Available itag: `{itags}`.\nPlease use `.itag tagname` to show it.')
                    return
                else:
                    await ctx.reply('There is no **itag** in this server. Please add.\n')
                    return
            else:
                # .itag -del tagid
                command_del = itag_text.split(" ")
                if len(command_del) >= 2:
                    TagIt = await store.sql_itag_by_server(str(ctx.guild.id), command_del[1].upper())
                    if command_del[0].upper() == "-DEL" and TagIt:
                        # check permission if there is attachment with .itag
                        if ctx.author.guild_permissions.manage_guild == False and ctx.author.guild_permissions.view_guild_insights == False:
                            await message.add_reaction(EMOJI_ERROR) 
                            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} **itag** Permission denied.')
                            return
                        else:
                            DeliTag = await store.sql_itag_by_server_del(str(ctx.guild.id), command_del[1].upper())
                            if DeliTag:
                                await ctx.reply(f'{ctx.author.mention} iTag **{command_del[1].upper()}** deleted.\n')
                            else:
                                await ctx.reply(f'{ctx.author.mention} iTag **{command_del[1].upper()}** error deletion.\n')
                            return
                    else:
                        await ctx.reply(f'{ctx.author.mention} iTag unknow operation.\n')
                        return
                elif len(command_del) == 1:
                    TagIt = await store.sql_itag_by_server(str(ctx.guild.id), itag_text.upper())
                    if TagIt:
                        tagLink = config.itag.static_link + TagIt['stored_name']
                        await ctx.reply(f'{tagLink}')
                        return
                    else:
                        await ctx.reply(f'There is no itag **{itag_text}** in this server.\n')
                        return
        else:
            if itag_text is None:
                await ctx.reply(f'{EMOJI_RED_NO} You need to include **tag** for this image.')
                return
            else:
                # check permission if there is attachment with .itag
                if ctx.author.guild_permissions.manage_guild == False and ctx.author.guild_permissions.view_guild_insights == False:
                    await message.add_reaction(EMOJI_ERROR) 
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} **itag** Permission denied.')
                    return
                d = [i['itag_id'] for i in ListiTag]
                if itag_text.upper() in d:
                    await ctx.reply(f'{EMOJI_RED_NO} iTag **{itag_text}** already exists here.')
                    return
                else:
                    pass
        # we passed of no attachment
        attachment = ctx.message.attachments[0]
        if not (attachment.filename.lower()).endswith(('.gif', '.jpeg', '.jpg', '.png', '.mp4')):
            await ctx.reply(f'{EMOJI_RED_NO} Attachment type rejected.')
            return
        else:
            print('Filename: {}'.format(attachment.filename))
        if attachment.size >= config.itag.max_size:
            await ctx.reply(f'{EMOJI_RED_NO} File too big.')
            return
        else:
            print('Size: {}'.format(attachment.size))
        print("iTag: {}".format(itag_text))
        if re.match(r'^[a-zA-Z0-9_-]*$', itag_text):
            if len(itag_text) >= 32:
                await ctx.reply(f'itag **{itag_text}** is too long.')
                return
        else:
            await ctx.reply(f'{EMOJI_RED_NO} iTag id not accepted.')
            return
        link = attachment.url # https://cdn.discordapp.com/attachments
        attach_save_name = str(uuid.uuid4()) + '.' + link.split(".")[-1].lower()
        try:
            if link.startswith("https://cdn.discordapp.com/attachments"):
                async with aiohttp.ClientSession() as session:
                    async with session.get(link) as resp:
                        if resp.status == 200:
                            if resp.headers["Content-Type"] not in ["image/gif", "image/png", "image/jpeg", "image/jpg", "video/mp4"]:
                                await ctx.reply(f'{EMOJI_RED_NO} Unsupported format file.')
                                return
                            else: 
                                with open(config.itag.path + attach_save_name, 'wb') as f:
                                    f.write(await resp.read())
                                # save to DB and inform
                                addiTag = await store.sql_itag_by_server_add(str(ctx.guild.id), itag_text.upper(),
                                                                             str(ctx.author), str(ctx.author.id),
                                                                             attachment.filename, attach_save_name, attachment.size)
                                if addiTag is None:
                                    await ctx.reply(f'{ctx.author.mention} Failed to add itag **{itag_text}**')
                                    return
                                elif addiTag.upper() == itag_text.upper():
                                    await ctx.reply(f'{ctx.author.mention} Successfully added itag **{itag_text}**')
                                    return
        except Exception as e:
            await logchanbot(traceback.format_exc())


def setup(bot):
    bot.add_cog(TipTag(bot))