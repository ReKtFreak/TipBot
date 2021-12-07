import sys, traceback

import discord
from discord.ext import commands
from dislash import InteractionClient, ActionRow, Button, ButtonStyle, Option, OptionType

from config import config
from Bot import *

class Voucher(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @commands.group(
        usage="voucher <subcommand>", 
        aliases=['redeem'], 
        description="Voucher commands."
    )
    async def voucher(self, ctx):
        prefix = await get_guild_prefix(ctx)
        if ctx.invoked_subcommand is None:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} Required some command. Please use {prefix}help voucher')
            return


    @voucher.command(
        usage="voucher make <amount> <coin> <comment>", 
        aliases=['gen'], 
        description="Make a voucher and share to other friends."
    )
    @commands.bot_has_permissions(add_reactions=True)
    async def make(
        self, 
        ctx, 
        amount: str, 
        coin: str, 
        *, 
        comment
    ):
        # check if bot is going to restart
        if IS_RESTARTING:
            await ctx.message.add_reaction(EMOJI_REFRESH)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Bot is going to restart soon. Wait until it is back for using this.')
            return

        # Check if maintenance
        if IS_MAINTENANCE == 1 and int(ctx.author.id) not in MAINTENANCE_OWNER:
            await ctx.message.add_reaction(EMOJI_WARNING)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {config.maintenance_msg}')
            return
        # End Check if maintenance

        # Check if tx in progress
        if ctx.author.id in TX_IN_PROCESS:
            await ctx.message.add_reaction(EMOJI_HOURGLASS_NOT_DONE)
            msg = await ctx.reply(f'{EMOJI_ERROR} {ctx.author.mention} You have another tx in progress.')
            await msg.add_reaction(EMOJI_OK_BOX)
            return

        amount = amount.replace(",", "")
        
        voucher_numb = 1
        if 'x' in amount.lower():
            # This is a batch
            voucher_numb = amount.lower().split("x")[0]
            voucher_each = amount.lower().split("x")[1]
            try:
                voucher_numb = int(voucher_numb)
                voucher_each = float(voucher_each)
                if voucher_numb > config.voucher.max_batch:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Too many. Maximum allowed: **{config.voucher.max_batch}**')
                    return
            except ValueError:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid number or amount to create vouchers.')
                return
        elif '*' in amount.lower():
            # This is a batch
            voucher_numb = amount.lower().split("*")[0]
            voucher_each = amount.lower().split("*")[1]
            try:
                voucher_numb = int(voucher_numb)
                voucher_each = Decimal(voucher_each)
                if voucher_numb > config.voucher.max_batch:
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Too many. Maximum allowed: **{config.voucher.max_batch}**')
                    return
            except ValueError:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid number or amount to create vouchers.')
                return
        else:
            try:
                amount = Decimal(amount)
                voucher_each = amount
            except ValueError:
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Invalid amount to create a voucher.')
                return

        total_amount = voucher_numb * voucher_each

        COIN_NAME = coin.upper()
        if is_maintenance_coin(COIN_NAME):
            await ctx.message.add_reaction(EMOJI_MAINTENANCE)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} {COIN_NAME} in maintenance.')
            return
        if COIN_NAME not in ENABLE_COIN_VOUCHER:
            await ctx.message.add_reaction(EMOJI_INFORMATION)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} we do not have voucher feature for **{COIN_NAME}** yet. Try with **{config.Enable_Coin_Voucher}**.')
            return

        if isinstance(ctx.channel, discord.DMChannel) == False:
            if COIN_NAME != "TRTL" and ctx.guild.id == TRTL_DISCORD:
                # TRTL discord not allowed
                await ctx.message.add_reaction(EMOJI_ERROR)
                return

        coin_family = getattr(getattr(config,"daemon"+COIN_NAME),"coin_family","TRTL")
        real_amount = int(voucher_each * get_decimal(COIN_NAME)) if coin_family in ["XMR", "TRTL", "BCN", "NANO", "XCH"] else float(voucher_each)
        total_real_amount = int(total_amount * get_decimal(COIN_NAME)) if coin_family in ["XMR", "TRTL", "BCN", "NANO", "XCH"] else float(total_amount)
        secret_string = str(uuid.uuid4())
        unique_filename = str(uuid.uuid4())

        user = await store.sql_get_userwallet(str(ctx.author.id), COIN_NAME)
        if user is None:
            user = await store.sql_register_user(str(ctx.author.id), COIN_NAME, SERVER_BOT, 0)

        userdata_balance = await store.sql_user_balance(str(ctx.author.id), COIN_NAME)
        xfer_in = 0
        if COIN_NAME not in ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            xfer_in = await store.sql_user_balance_get_xfer_in(str(ctx.author.id), COIN_NAME)
        if COIN_NAME in ENABLE_COIN_DOGE+ENABLE_COIN_ERC+ENABLE_COIN_TRC:
            actual_balance = float(xfer_in) + float(userdata_balance['Adjust'])
        elif COIN_NAME in ENABLE_COIN_NANO:
            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])
            actual_balance = round(actual_balance / get_decimal(COIN_NAME), 6) * get_decimal(COIN_NAME)
        else:
            actual_balance = int(xfer_in) + int(userdata_balance['Adjust'])

        # Negative check
        try:
            if actual_balance < 0:
                msg_negative = 'Negative balance detected:\nUser: '+str(ctx.author.id)+'\nCoin: '+COIN_NAME+'\nAtomic Balance: '+str(actual_balance)
                await logchanbot(msg_negative)
        except Exception as e:
            await logchanbot(traceback.format_exc())
        
        # If voucher in setting
        voucher_setting = await store.sql_voucher_get_setting(COIN_NAME)
        if isinstance(voucher_setting, dict):
            min_voucher_amount = float(voucher_setting['real_min_amount']) * get_decimal(COIN_NAME)
            max_voucher_amount = float(voucher_setting['real_max_amount']) * get_decimal(COIN_NAME)
            fee_voucher_amount = float(voucher_setting['real_voucher_fee']) * get_decimal(COIN_NAME)
            logo = Image.open(voucher_setting['logo_image_path'])
            img_frame = Image.open(voucher_setting['frame_image_path'])
        else:
            min_voucher_amount = get_min_voucher_amount(COIN_NAME)
            max_voucher_amount = get_max_voucher_amount(COIN_NAME)
            fee_voucher_amount = get_voucher_fee(COIN_NAME)
            logo = Image.open(config.voucher.coin_logo_path + COIN_NAME.lower() + ".png")
            img_frame = Image.open(config.voucher.path_voucher_defaultimg)
        if real_amount < min_voucher_amount or real_amount > max_voucher_amount:
            min_amount = num_format_coin(min_voucher_amount, COIN_NAME) + COIN_NAME
            max_amount = num_format_coin(max_voucher_amount, COIN_NAME) + COIN_NAME
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Voucher amount must between {min_amount} and {max_amount}.')
            return

        if actual_balance < real_amount + fee_voucher_amount:
            having_amount = num_format_coin(actual_balance, COIN_NAME)
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to create voucher.\n'
                           f'A voucher needed amount + fee: {num_format_coin(real_amount + fee_voucher_amount, COIN_NAME)} {COIN_NAME}\n'
                           f'Having: {having_amount} {COIN_NAME}.')
            return

        comment = comment.strip().replace('\n', ' ').replace('\r', '')
        if len(comment) > config.voucher.max_comment:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Please limit your comment to max. **{config.voucher.max_comment}** chars.')
            return
        if not is_ascii(comment):
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Unsupported char(s) detected in comment.')
            return

        # If it is a batch oir not
        if voucher_numb > 1:
            # Check if sufficient balance
            if actual_balance < (real_amount + fee_voucher_amount) * voucher_numb:
                having_amount = num_format_coin(actual_balance, COIN_NAME)
                await ctx.message.add_reaction(EMOJI_ERROR)
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Insufficient balance to create **{voucher_numb}** vouchers.\n'
                               f'**{voucher_numb}** vouchers needed amount + fee: {num_format_coin((real_amount + fee_voucher_amount*voucher_numb), COIN_NAME)} {COIN_NAME}\n'
                               f'Having: {having_amount} {COIN_NAME}.')
                return

            # Check if bot can DM him first. If failed reject
            try:
                await ctx.author.send(f'{ctx.author.mention} I am creating a voucher for you and will direct message to you the pack of vouchers.')
            except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                # If failed to DM, message we stop
                await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} Voucher batch will not work if you disable DM or I failed to DM you.')
                return
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            if isinstance(ctx.channel, discord.DMChannel) == False:
                try:
                    await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} You should do this in Direct Message.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    pass   
            for i in range(voucher_numb):
                secret_string = str(uuid.uuid4())
                unique_filename = str(uuid.uuid4())
                # loop voucher_numb times
                # do some QR code
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=2,
                )
                qrstring = config.voucher.voucher_url + "/claim/" + secret_string
                qr.add_data(qrstring)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                qr_img = qr_img.resize((280, 280))
                qr_img = qr_img.convert("RGBA")

                #Logo
                try:
                    box = (115,115,165,165)
                    qr_img.crop(box)
                    region = logo
                    region = region.resize((box[2] - box[0], box[3] - box[1]))
                    qr_img.paste(region,box)
                    # qr_img.save(config.voucher.path_voucher_create + unique_filename + "_2.png")
                except Exception as e: 
                    await logchanbot(traceback.format_exc())
                # Image Frame on which we want to paste  
                img_frame.paste(qr_img, (100, 150)) 

                # amount font
                try:
                    msg = str(num_format_coin(real_amount, COIN_NAME)) + COIN_NAME
                    W, H = (1123,644)
                    draw =  ImageDraw.Draw(img_frame)
                    myFont = ImageFont.truetype(config.font.digital7, 44)
                    # w, h = draw.textsize(msg, font=myFont)
                    w, h = myFont.getsize(msg)
                    # draw.text(((W-w)/2,(H-h)/2), msg, fill="black",font=myFont)
                    draw.text((250-w/2,275+125+h), msg, fill="black",font=myFont)

                    # Instruction to claim
                    myFont = ImageFont.truetype(config.font.digital7, 36)
                    msg_claim = "SCAN TO CLAIM IT!"
                    w, h = myFont.getsize(msg_claim)
                    draw.text((250-w/2,275+125+h+60), msg_claim, fill="black",font=myFont)

                    # comment part
                    comment_txt = "COMMENT: " + comment.upper()
                    myFont = ImageFont.truetype(config.font.digital7, 24)
                    w, h = myFont.getsize(comment_txt)
                    draw.text((561-w/2,275+125+h+120), comment_txt, fill="black",font=myFont)
                except Exception as e: 
                    await logchanbot(traceback.format_exc())
                # Saved in the same relative location 
                img_frame.save(config.voucher.path_voucher_create + unique_filename + ".png")
                if ctx.author.id not in TX_IN_PROCESS:
                    TX_IN_PROCESS.append(ctx.author.id)
                    try:
                        voucher_make = await store.sql_send_to_voucher(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                                       ctx.message.content, real_amount, fee_voucher_amount, comment, 
                                                                       secret_string, unique_filename + ".png", COIN_NAME, SERVER_BOT)
                    except Exception as e: 
                        await logchanbot(traceback.format_exc())
                    await asyncio.sleep(config.interval.tx_lap_each)
                    TX_IN_PROCESS.remove(ctx.author.id)
                else:
                    # reject and tell to wait
                    msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You have another tx in process. Please wait it to finish. ')
                    await msg.add_reaction(EMOJI_OK_BOX)
                    return
                    
                if voucher_make:             
                    try:
                        msg = await ctx.author.send(f'New Voucher Link ({i+1} of {voucher_numb}): {qrstring}\n'
                                            '```'
                                            f'Amount: {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}\n'
                                            f'Voucher Fee (Incl. network fee): {num_format_coin(fee_voucher_amount, COIN_NAME)} {COIN_NAME}\n'
                                            f'Voucher comment: {comment}```')
                        await msg.add_reaction(EMOJI_OK_BOX)
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        await logchanbot(traceback.format_exc())
                        await ctx.message.add_reaction(EMOJI_ERROR)
                        await ctx.reply(f'{ctx.author.mention} Sorry, I failed to DM you.')
                else:
                    await ctx.message.add_reaction(EMOJI_ERROR)
            return
        elif voucher_numb == 1:
            # do some QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qrstring = config.voucher.voucher_url + "/claim/" + secret_string
            qr.add_data(qrstring)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((280, 280))
            qr_img = qr_img.convert("RGBA")
            # qr_img.save(config.voucher.path_voucher_create + unique_filename + "_1.png")

            #Logo
            try:
                box = (115,115,165,165)
                qr_img.crop(box)
                region = logo
                region = region.resize((box[2] - box[0], box[3] - box[1]))
                qr_img.paste(region,box)
                # qr_img.save(config.voucher.path_voucher_create + unique_filename + "_2.png")
            except Exception as e: 
                await logchanbot(traceback.format_exc())
            # Image Frame on which we want to paste 
            img_frame.paste(qr_img, (100, 150)) 

            # amount font
            try:
                msg = str(num_format_coin(real_amount, COIN_NAME)) + COIN_NAME
                W, H = (1123,644)
                draw =  ImageDraw.Draw(img_frame)
                myFont = ImageFont.truetype(config.font.digital7, 44)
                # w, h = draw.textsize(msg, font=myFont)
                w, h = myFont.getsize(msg)
                # draw.text(((W-w)/2,(H-h)/2), msg, fill="black",font=myFont)
                draw.text((250-w/2,275+125+h), msg, fill="black",font=myFont)

                # Instruction to claim
                myFont = ImageFont.truetype(config.font.digital7, 36)
                msg_claim = "SCAN TO CLAIM IT!"
                w, h = myFont.getsize(msg_claim)
                draw.text((250-w/2,275+125+h+60), msg_claim, fill="black",font=myFont)

                # comment part
                comment_txt = "COMMENT: " + comment.upper()
                myFont = ImageFont.truetype(config.font.digital7, 24)
                w, h = myFont.getsize(comment_txt)
                draw.text((561-w/2,275+125+h+120), comment_txt, fill="black",font=myFont)
            except Exception as e: 
                await logchanbot(traceback.format_exc())
            # Saved in the same relative location 
            img_frame.save(config.voucher.path_voucher_create + unique_filename + ".png")
            if ctx.author.id not in TX_IN_PROCESS:
                TX_IN_PROCESS.append(ctx.author.id)
                try:
                    voucher_make = await store.sql_send_to_voucher(str(ctx.author.id), '{}#{}'.format(ctx.author.name, ctx.author.discriminator), 
                                                                   ctx.message.content, real_amount, fee_voucher_amount, comment, 
                                                                   secret_string, unique_filename + ".png", COIN_NAME, SERVER_BOT)
                except Exception as e: 
                    await logchanbot(traceback.format_exc())
                await asyncio.sleep(config.interval.tx_lap_each)
                TX_IN_PROCESS.remove(ctx.author.id)
            else:
                # reject and tell to wait
                msg = await ctx.reply(f'{EMOJI_RED_NO} {ctx.author.mention} You have another tx in process. Please wait it to finish. ')
                await msg.add_reaction(EMOJI_OK_BOX)
                return

            if voucher_make:
                await ctx.message.add_reaction(EMOJI_OK_HAND)
                if isinstance(ctx.channel, discord.DMChannel) == False:
                    try:
                        await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} You should do this in Direct Message.')
                    except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                        pass                
                try:
                    msg = await ctx.reply(f'New Voucher Link: {qrstring}\n'
                                        '```'
                                        f'Amount: {num_format_coin(real_amount, COIN_NAME)} {COIN_NAME}\n'
                                        f'Voucher Fee (Incl. network fee): {num_format_coin(fee_voucher_amount, COIN_NAME)} {COIN_NAME}\n'
                                        f'Voucher comment: {comment}```')
                    await msg.add_reaction(EMOJI_OK_BOX)
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    await logchanbot(traceback.format_exc())
                    await ctx.message.add_reaction(EMOJI_ERROR)
                    await ctx.reply(f'{ctx.author.mention} Sorry, I failed to DM you.')
            else:
                await ctx.message.add_reaction(EMOJI_ERROR)
            return


    @voucher.command(
        usage="voucher view", 
        description="View recent made voucher in a list."
    )
    async def view(self, ctx):
        get_vouchers = await store.sql_voucher_get_user(str(ctx.author.id), SERVER_BOT, 15, 'YESNO')
        if get_vouchers and len(get_vouchers) > 0:
            table_data = [
                ['Ref Link', 'Amount', 'Claimed?', 'Created']
            ]
            for each in get_vouchers:
                table_data.append([each['secret_string'], num_format_coin(each['amount'], each['coin_name'])+each['coin_name'], 
                                   'YES' if each['already_claimed'] == 'YES' else 'NO', 
                                   datetime.fromtimestamp(each['date_create']).strftime('%Y-%m-%d')])
            table = AsciiTable(table_data)
            table.padding_left = 1
            table.padding_right = 1
            if isinstance(ctx.channel, discord.DMChannel) == False:
                try:
                    await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} You should do this in Direct Message.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    pass
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            msg = await ctx.reply(f'**[ YOUR VOUCHER LIST ]**\n'
                                 f'```{table.table}```\n')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} You did not create any voucher yet.')
        return


    @voucher.command(
        usage="voucher unclaim", 
        description="View list of unclaimed vouchers."
    )
    async def unclaim(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be in public.')
            return
        get_vouchers = await store.sql_voucher_get_user(str(ctx.author.id), SERVER_BOT, 50, 'NO')
        if get_vouchers and len(get_vouchers) >= 25:
            # list them in text
            unclaim = ', '.join([each['secret_string'] for each in get_vouchers])
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            await ctx.reply(f'{ctx.author.mention} You have many unclaimed vouchers: {unclaim}')
            return
        elif get_vouchers and len(get_vouchers) > 0:
            table_data = [
                ['Ref Link', 'Amount', 'Claimed?', 'Created']
            ]
            for each in get_vouchers:
                table_data.append([each['secret_string'], num_format_coin(each['amount'], each['coin_name'])+each['coin_name'], 
                                   'YES' if each['already_claimed'] == 'YES' else 'NO', 
                                   datetime.fromtimestamp(each['date_create']).strftime('%Y-%m-%d')])
            table = AsciiTable(table_data)
            table.padding_left = 1
            table.padding_right = 1
            if isinstance(ctx.channel, discord.DMChannel) == False:
                try:
                    await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} You should do this in Direct Message.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    pass
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            msg = await ctx.reply(f'**[ YOUR VOUCHER LIST ]**\n'
                                 f'```{table.table}```\n')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} You did not create any voucher yet.')
        return


    @voucher.command(
        usage="voucher claim", 
        aliases=['claimed'], 
        description="View list of claimed vouchers."
    )
    async def claim(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be in public.')
            return
        get_vouchers = await store.sql_voucher_get_user(str(ctx.author.id), SERVER_BOT, 50, 'YES')
        if get_vouchers and len(get_vouchers) >= 25:
            # list them in text
            unclaim = ', '.join([each['secret_string'] for each in get_vouchers])
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            await ctx.reply(f'{ctx.author.mention} You have many claimed vouchers: {unclaim}')
            return
        elif get_vouchers and len(get_vouchers) > 0:
            table_data = [
                ['Ref Link', 'Amount', 'Claimed?', 'Created']
            ]
            for each in get_vouchers:
                table_data.append([each['secret_string'], num_format_coin(each['amount'], each['coin_name'])+each['coin_name'], 
                                   'YES' if each['already_claimed'] == 'YES' else 'NO', 
                                   datetime.fromtimestamp(each['date_create']).strftime('%Y-%m-%d')])
            table = AsciiTable(table_data)
            table.padding_left = 1
            table.padding_right = 1
            if isinstance(ctx.channel, discord.DMChannel) == False:
                try:
                    await ctx.reply(f'{EMOJI_INFORMATION} {ctx.author.mention} You should do this in Direct Message.')
                except (discord.Forbidden, discord.errors.Forbidden, discord.errors.HTTPException) as e:
                    pass
            await ctx.message.add_reaction(EMOJI_OK_HAND)
            msg = await ctx.reply(f'**[ YOUR VOUCHER LIST ]**\n'
                                 f'```{table.table}```\n')
            await msg.add_reaction(EMOJI_OK_BOX)
            return
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} You did not create any voucher yet.')
        return


    @voucher.command(
        usage="voucher getunclaim", 
        description="Get a list of unclaimed vouchers as a file."
    )
    async def getunclaim(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be in public.')
            return
        get_vouchers = await store.sql_voucher_get_user(str(ctx.author.id), SERVER_BOT, 10000, 'NO')
        if get_vouchers and len(get_vouchers) > 0:
            try:
                filename = config.voucher.claim_csv_tmp + str(uuid.uuid4()) + '_unclaimed.csv'
                write_csv_dumpinfo = open(filename, "w")
                for item in get_vouchers:
                    write_csv_dumpinfo.write(config.voucher.voucher_url + '/claim/' + item['secret_string'] + '\n')
                write_csv_dumpinfo.close()
                if os.path.exists(filename):
                    try:
                        await ctx.author.send(f"YOUR UNCLAIMED VOUCHER LIST IN CSV FILE:",
                                                      file=discord.File(filename))
                    except Exception as e:
                        await ctx.message.add_reaction(EMOJI_ERROR) 
                        await ctx.reply(f'{ctx.author.mention} I failed to send CSV file to you.')
                        await logchanbot(traceback.format_exc())
                    os.remove(filename)
            except Exception as e:
                await logchanbot(traceback.format_exc())
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} You did not create any voucher yet.')
        return


    @voucher.command(
        usage="voucher getclaim", 
        description="Get a list of claimed vouchers as a file."
    )
    async def getclaim(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel) == False:
            await ctx.message.add_reaction(EMOJI_ERROR) 
            await ctx.reply(f'{ctx.author.mention} This command can not be in public.')
            return
        get_vouchers = await store.sql_voucher_get_user(str(ctx.author.id), SERVER_BOT, 10000, 'YES')
        if get_vouchers and len(get_vouchers) > 0:
            try:
                filename = config.voucher.claim_csv_tmp + str(uuid.uuid4()) + '_claimed.csv'
                write_csv_dumpinfo = open(filename, "w")
                for item in get_vouchers:
                    write_csv_dumpinfo.write(config.voucher.voucher_url + '/claim/' + item['secret_string'] + '\n')
                write_csv_dumpinfo.close()
                if os.path.exists(filename):
                    try:
                        await ctx.author.send(f"YOUR CLAIMED VOUCHER LIST IN CSV FILE:",
                                                      file=discord.File(filename))
                    except Exception as e:
                        await ctx.message.add_reaction(EMOJI_ERROR) 
                        await ctx.reply(f'{ctx.author.mention} I failed to send CSV file to you.')
                        await logchanbot(traceback.format_exc())
                    os.remove(filename)
            except Exception as e:
                await logchanbot(traceback.format_exc())
        else:
            await ctx.message.add_reaction(EMOJI_ERROR)
            await ctx.reply(f'{ctx.author.mention} You did not create any voucher yet.')
        return


def setup(bot):
    bot.add_cog(Voucher(bot))