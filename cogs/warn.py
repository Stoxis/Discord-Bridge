import json
import random
import ast
from datetime import datetime
import re
import compress_json
import traceback

import discord
from discord import Member
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions

# Todo nicknames for mirrored embeds

class bidict(dict):
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, []).append(key) 

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key) 
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value, []).append(key)        

    def __delitem__(self, key):
        value = self[key] 
        self.inverse.setdefault(value, []).remove(key)
        if value in self.inverse and not self.inverse[value]: 
            del self.inverse[value]
        super(bidict, self).__delitem__(key)

def load_data(filename, global_var, default=None):
    try:
        data = compress_json.load(filename)
        if isinstance(default, bidict):
            globals()[global_var] = bidict(data)
        else:
            globals()[global_var] = data
    except FileNotFoundError:
        if isinstance(default, bidict):
            globals()[global_var] = bidict()
        else:
            globals()[global_var] = default

# These color constants are taken from discord.js library
with open("embed_colors.txt") as f:
    data = f.read()
    colors = ast.literal_eval(data)
    color_list = [c for c in colors.values()]

# Bi-Directional Dictionary to store message channel pairs
message_channel_pairs = bidict()

# Bi-Directional Dictionary to store message message pairs
message_pairs = bidict()

async def get_opposite_message(message_id, bot): # Outputs the key in a dictionary if either the value matches or vice versa
    global message_pairs
    global message_channel_pairs
    load_data('message_pairs.json.lzma', 'message_pairs', bidict())
    load_data('message_channel_pairs.json.lzma', 'message_channel_pairs', bidict())
    for key, value in message_pairs.items():
        try:
            if value == int(message_id) or key == str(message_id): # Key is real message id
                channel = bot.get_channel(message_channel_pairs[str(value)])
                message = await channel.fetch_message(value)
                return channel, message # This'll probabably break if there's multiple channel pairs since it won't return an array containing all the results, just the first channel found
        except:
            return None, None
    return None, None  # Return None if the value is not found in the dictionary

async def get_original_message(message_id, bot): # Outputs the key in a dictionary if either the key or value of that pair matches
    global message_pairs
    global message_channel_pairs
    load_data('message_pairs.json.lzma', 'message_pairs', bidict())
    load_data('message_channel_pairs.json.lzma', 'message_channel_pairs', bidict())
    for key, value in message_pairs.items():
        try:
            if value == int(message_id) or key == str(message_id): # Key is real message id
                channel = bot.get_channel(message_channel_pairs[str(key)])
                real_message = await channel.fetch_message(key)
                return real_message
        except:
            return None
    return None  # Return None if the value is not found in the dictionary

async def get_user_from_input(input_str, bot):
    # Regular expression pattern to match user mentions and IDs
    user_pattern = re.compile(r'<@!?(\d+)>|(\d+)')

    # Try to find a match in the input string
    try:
        match = user_pattern.match(input_str)
    except TypeError:
        return None

    if match:
        # Check if a user mention (<@user_id> or <@!user_id>) was found
        try:
            if match.group(1):
                user_id = int(match.group(1))
            else:
                # Use the numeric ID if no mention was found
                user_id = int(match.group(2))
        except ValueError:
            return None
            
        # Get the user object
        for guild in bot.guilds:
            try:
                user = await guild.fetch_member(user_id)
                if user:
                    # User found, break out of the loop
                    break
            except discord.NotFound:
                # User not found in this guild, continue to the next guild
                user = None
                continue
        if user:
            # Log successful user retrieval
            print(f"User found: {user.name} (ID: {user.id})")
            return user
        else:
            # Log user not found
            print(f"User not found with ID: {user_id}")
            return None
    else:
        return None

async def check_user(user, bot, ctx):
        user_obj = await get_user_from_input(user, bot)
        if user_obj == None and user == None: # Nothing provided
            await ctx.send("You forgot to provide a user as an argument.")
            return
        elif user_obj == None and user is not None: # Text channel(?)
            message = await get_original_message(user, bot)
            if message is not None:
                user = await message.channel.guild.fetch_member(message.author.id)
                return user
            else:
                await ctx.send("The user provided is not valid.")
                return
        elif user_obj is not None and user is not None:
            user = user_obj
            return user
        else:
            return

class Warn(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Define a new command
    @commands.command(
        name='warn',
        description='The famous warn command',
        usage='<@offender> called my mommy a fat :((((((( cri' # Todo: add direct messageID functionality for paired channels
    )
    @has_permissions(manage_messages=True)
    async def warn_command(self, ctx, user=None, *, reason: str):
        user = await check_user(user, self.bot, ctx)
        if user.guild_permissions.manage_messages == True:
            await ctx.send("The specified user has the \"Manage Messages\" permission (or higher) inside the guild/server.")
            return           
        if user.id == self.bot.user.id:
            await ctx.send("Oh, REALLY now, huh? I do my best at maintaining this server and THIS is how you treat me? Screw this..")
            return
        if user.bot:
            await ctx.send("It's useless to warn a bot. Why would you even try.")
            return
        if user == ctx.author:
            await ctx.send("Why the heck would you warn yourself? You hate yourself THAT much?")
            return

        dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Load existing data from the file
        try:
            data = compress_json.load("members.json.lzma")
        except FileNotFoundError:
            # If the file doesn't exist, initialize an empty dictionary
            data = {}

        # Check if the user ID exists in the data and the 'warns' key is present and <= 0
        if str(user.id) in data and 'warns' in data[str(user.id)] and data[str(user.id)]['warns'] <= 0:
            # Modify the data in memory
            data[str(user.id)]['warns'] = 1
            data[str(user.id)]['1'] = {
                'warner': ctx.author.id,
                'warner_name': ctx.author.name,
                'reason': reason,
                'channel': str(ctx.channel.id),
                'datetime': dt_string
            }
        else:
            # If the user has previous warns or doesn't exist in the data, update accordingly
            if str(user.id) not in data:
                data[str(user.id)] = {}

            # Increment warn count
            warn_amount = data[str(user.id)].get("warns", 0) + 1
            data[str(user.id)]["warns"] = warn_amount
            data[str(user.id)]["username"] = user.name

            # Add a new warn entry
            new_warn = {
                str(warn_amount): {
                    'warner': ctx.author.id,
                    'warner_name': ctx.author.name,
                    'reason': reason,
                    'channel': str(ctx.channel.id),
                    'datetime': dt_string
                }
            }
            data[str(user.id)].update(new_warn)

        # Write the modified data back to the file, overwriting the previous contents
        compress_json.dump(data, "members.json.lzma")

        # Create and send an embed showing that the user has been warned successfully
        embed = discord.Embed(
            title=f"{user.name}'s new warn",
            color=random.choice(color_list)
        )
        embed.set_author(
            name=ctx.message.author.name,
            icon_url=ctx.message.author.display_avatar.url,
            url=f"https://discord.com/users/{ctx.message.author.id}/"
        )
        embed.add_field(
            name=f"Warn {warn_amount}",
            value=f"Warner: {ctx.author.name} (<@{ctx.author.id}>)\nReason: {reason}\nChannel: <#{str(ctx.channel.id)}>\nDate and Time: {dt_string}",
            inline=True
        )
        # Creates and sends embed(s)
        await ctx.send(
            content="Successfully added new warn.",
            embed=embed
        )
        paired_channel, paired_message = await get_opposite_message(ctx.message.id, self.bot)
        if paired_channel:
                await paired_channel.send(
                content="Successfully added new warn.",
                embed=embed
            )
    @warn_command.error
    async def warn_handler(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            # Author is missing permissions
            await ctx.send('{0.author.name}, you do not have the correct permissions to do so. *(commands.MissingPermissions error, action cancelled)*'.format(ctx))
            return
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'user':
                # Author did not specify the user to warn
                await ctx.send("{0.author.name}, you forgot to specify a user to warn. *(commands.MissingRequiredArgument error, action cancelled)*".format(ctx))
                return
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'reason':
                # Author did not specify the reason
                await ctx.send("{0.author.name}, you forgot to specify a reason. *(commands.MissingRequiredArgument error, action cancelled)*".format(ctx))
                return
        traceback_str = traceback.format_exc()
        print(traceback_str)
        print(error)
        await ctx.send(error + " <@1143793302701879416>")

    @commands.command(
        name='warns',
        description='See all the warns a user has',
        usage='<@offender>',
        aliases=['warnings']
    )
    async def warns_command(self, ctx, user=None):
        user = await check_user(user, self.bot, ctx)
        paired_channel, paired_message = await get_opposite_message(ctx.message.id, self.bot)
        try:
            data = compress_json.load("members.json.lzma")
        except FileNotFoundError:
            await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] does not have any warns.")
            if paired_channel:
                await paired_channel.send(f"{ctx.author.name}, user [{user.name}] does not have any warns.")
            return
    
        try:
            if 'warns' not in data.get(str(user.id), {}) or data[str(user.id)].get('warns') <= 0:
                await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] does not have any warns.")
                if paired_channel:
                    await paired_channel.send(f"{ctx.author.name}, user [{user.name}] does not have any warns.")
                return
        except:
            #raise commands.CommandInvokeError("user")
            return
        warn_amount = data[str(user.id)].get("warns", 0)
        last_noted_name = data[str(user.id)].get("username", user.name)
        warns_word = "warn" if warn_amount == 1 else "warns"
    
        embed = discord.Embed(
            title=f"{user.name}'s warns",
            description=f"They have {warn_amount} {warns_word}.",
            color=random.choice(color_list)
        )
    
        embed.set_author(
            name=ctx.message.author.name,
            icon_url=ctx.message.author.display_avatar.url,
            url=f"https://discord.com/users/{ctx.message.author.id}/"
        )
    
        for x in range(1, warn_amount + 1):
            warn_dict = data[str(user.id)][str(x)]
            warner_id = warn_dict.get('warner')
            
            try:
                warner = await ctx.guild.fetch_member(warner_id)
            except discord.NotFound:
                warner = None
    
            warn_reason = warn_dict.get('reason')
            warn_channel = warn_dict.get('channel')
            warn_datetime = warn_dict.get('datetime')
    
            warner_name = warner.name if warner else warn_dict.get('warner_name', 'Unknown User')
    
            embed.add_field(
                name=f"Warn {x}",
                value=f"Warner: {warner_name} (<@{warner_id}>)\nReason: {warn_reason}\nChannel: <#{warn_channel}>\nDate and Time: {warn_datetime}",
                inline=True
            )
        # Send embed(s).
        await ctx.send(
            content=None,
            embed=embed
        )
        if paired_channel:
            await paired_channel.send(
                content=None,
                embed=embed
            )
    @warns_command.error
    async def warns_handler(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'user':
                # Author did not specify user
                await ctx.send("Please mention someone to verify their warns.")
            else:
                await ctx.send("Command usage: `^warns <user>`")
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send("An error occurred while processing the command. Please try again later.")
            traceback_str = traceback.format_exc()
            print(traceback_str)
            print(error)
        else:
            await ctx.send(f"An error occurred: {error}")
            traceback_str = traceback.format_exc()
            print(traceback_str)
            print(error)

    @commands.command(
        name='remove_warn',
        description='Removes a specific warn from a specific user.',
        usage='@user 2',
        aliases=['removewarn','clearwarn','warn_remove']
    )
    @has_permissions(manage_messages=True)
    async def remove_warn_command(self, ctx, user=None, *, warn: str):
        user = await check_user(user, self.bot, ctx)
        try:
            data = compress_json.load("members.json.lzma")
        except FileNotFoundError:
            await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] does not have any warns.")
            return
    
        if 'warns' not in data.get(str(user.id), {}) or data[str(user.id)].get('warns') <= 0:
            await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] does not have any warns.")
            return
    
        warn_amount = data[str(user.id)].get("warns", 0)
        specified_warn = data[str(user.id)].get(str(warn))
    
        if specified_warn is None:
            await ctx.send(f"{ctx.author.name}, there is no warn number {warn} for user [{user.name} ({user.id})].")
            return
    
        warn_warner = specified_warn.get('warner')
        warn_reason = specified_warn.get('reason')
        warn_channel = specified_warn.get('channel')
        warn_datetime = specified_warn.get('datetime')
    
        try:
            warn_warner_name = self.bot.get_user(id=warn_warner)
        except:
            # User probably left
            warn_warner_name = specified_warn.get('warner_name')
    
        confirmation_embed = discord.Embed(
            title=f'{user.name}\'s warn number {warn}',
            description=f'Warner: {warn_warner_name}\nReason: {warn_reason}\nChannel: <#{warn_channel}>\nDate and Time: {warn_datetime}',
            color=random.choice(color_list),
        )
        confirmation_embed.set_author(
            name=ctx.message.author.name,
            icon_url=ctx.message.author.display_avatar.url,
            url=f"https://discord.com/users/{ctx.message.author.id}/"
        )
    
        def check(ms):
            return ms.channel == ctx.message.channel and ms.author == ctx.message.author
        paired_channel, paired_message = await get_opposite_message(ctx.message.id, self.bot)
        await ctx.send(content='Are you sure you want to remove this warn? (Reply with y or n)', embed=confirmation_embed)
        if paired_channel:
            await paired_channel.send(content='Are you sure you want to remove this warn? (Reply with y or n)', embed=confirmation_embed)
        msg = await self.bot.wait_for('message', check=check)
        reply = msg.content.lower()
    
        if reply in ('y', 'yes', 'confirm'):
            if warn_amount == 1:
                del data[str(user.id)]['warns']
            else:
                for x in range(int(warn), int(warn_amount)):
                    data[str(user.id)][str(x)] = data[str(user.id)][str(x + 1)]
                    del data[str(user.id)][str(x + 1)]
                data[str(user.id)]['warns'] = warn_amount - 1
            compress_json.dump(data, "members.json.lzma")
            await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] has had their warn removed.")
            if paired_channel:
                await paired_channel.send(f"{ctx.author.name}, user [{user.name} ({user.id})] has had their warn removed.")
        elif reply in ('n', 'no', 'cancel'):
            await ctx.send("Alright, action cancelled.")
        else:
            await ctx.send("I have no idea what you want me to do. Action cancelled.")

    @remove_warn_command.error
    async def remove_warn_handler(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'user':
                # Author did not specify a user
                await ctx.send("Please mention someone to remove their warns.")
                return
            if error.param.name == 'warn':
                # Author did not specify a warn ID
                await ctx.send("You did not specify a warn ID to remove.")
                return
        if isinstance(error, commands.CommandInvokeError):
            # Author probably specified an invalid ID.
            await ctx.send("You specified an invalid ID.")
            return
        await ctx.send(error)

    @commands.command(
        name='edit_warn',
        description='Edits a specific warn from a specific user.',
        usage='@user 2',
        aliases=['editwarn','changewarn']
    )
    @has_permissions(manage_messages=True)
    async def edit_warn_command(self, ctx, user=None, *, warn: str):
        user = await check_user(user, self.bot, ctx)
        try:
            data = compress_json.load("members.json.lzma")
        except FileNotFoundError:
            await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] does not have any warns.")
            return
    
        if 'warns' not in data.get(str(user.id), {}) or data[str(user.id)].get('warns') <= 0:
            await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] does not have any warns.")
            return
    
        def check(ms):
            return ms.channel == ctx.message.channel and ms.author == ctx.message.author
    
        await ctx.send(content='What would you like to change the warn\'s reason to?')
        msg = await self.bot.wait_for('message', check=check)
        warn_new_reason = msg.content
    
        specified_warn = data[str(user.id)].get(warn)
    
        if specified_warn is None:
            await ctx.send(f"{ctx.author.name}, there is no warn number {warn} for user [{user.name} ({user.id})].")
            return
    
        warn_warner = specified_warn.get('warner')
        warn_channel = specified_warn.get('channel')
        warn_datetime = specified_warn.get('datetime')
    
        try:
            warn_warner_name = self.bot.get_user(id=warn_warner)
        except:
            # User probably left
            warn_warner_name = specified_warn.get('warner_name')
    
        confirmation_embed = discord.Embed(
            title=f'{user.name}\'s warn number {warn}',
            description=f'Warner: {warn_warner_name}\nReason: {warn_new_reason}\nChannel: <#{warn_channel}>\nDate and Time: {warn_datetime}',
            color=random.choice(color_list),
        )
        confirmation_embed.set_author(
            name=ctx.message.author.name,
            icon_url=ctx.message.author.display_avatar.url,
            url=f"https://discord.com/users/{ctx.message.author.id}/"
        )
        paired_channel, paired_message = await get_opposite_message(ctx.message.id, self.bot)
        await ctx.send(content='Are you sure you want to edit this warn like this? (Reply with y/yes or n/no)', embed=confirmation_embed)
        if paired_channel:
                await paired_channel.send(content='Are you sure you want to edit this warn like this? (Reply with y/yes or n/no)', embed=confirmation_embed)
        msg = await self.bot.wait_for('message', check=check)
        reply = msg.content.lower()
    
        if reply in ('y', 'yes', 'confirm'):
            specified_warn['reason'] = warn_new_reason
            compress_json.dump(data, "members.json.lzma")
            await ctx.send(f"[{ctx.author.name}], user [{user.name} ({user.id})] has had their warn edited.")
            if paired_channel:
                    await paired_channel.send(f"[{ctx.author.name}], user [{user.name} ({user.id})] has had their warn edited.")
        elif reply in ('n', 'no', 'cancel'):
            await ctx.send("Alright, action cancelled.")
        else:
            await ctx.send("I have no idea what you want me to do. Action cancelled.")
    @edit_warn_command.error
    async def edit_warn_handler(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'user':
                # Author did not specify a user
                await ctx.send("Please mention someone to remove their warns.")
                return
            if error.param.name == 'warn':
                # Author did not specify a warn ID
                await ctx.send("You did not specify a warn ID to remove.")
                return
        if isinstance(error, commands.CommandInvokeError):
            # Author probably specified an invalid ID.
            await ctx.send("You specified an invalid ID.")
            return
        await ctx.send(error)



async def setup(bot):
    await bot.add_cog(Warn(bot))
