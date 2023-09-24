import json
import random
import ast
from datetime import datetime
import os
import traceback  

import discord
from discord import Member
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions

# These color constants are taken from discord.js library
with open("embed_colors.txt") as f:
    data = f.read()
    colors = ast.literal_eval(data)
    color_list = [c for c in colors.values()]

class Warn(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # Define a new command
    @commands.command(
        name='warn',
        description='The famous warn command',
        usage='<@offender> called my mommy a fat :((((((( cri' # Todo: add direct messageID functionality for paired channels
    )
    async def warn_command(self, ctx, user: discord.Member, *, reason: str):
        if user.id == self.bot.user.id:
            await ctx.send("Oh, REALLY now, huh? I do my best at maintaining this server and THIS is how you treat me? Screw this..")
            return
        if user.bot:
            await ctx.send("It's useless to warn a bot. Why would you even try.")
            return
        if user == ctx.author:
            await ctx.send("Why the heck would you warn yourself? You hate yourself THAT much?")
            return
        if user.guild_permissions.manage_messages:
            await ctx.send("The specified user has the \"Manage Messages\" permission (or higher) inside the guild/server.")
            return

        dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Load existing data from the file
        try:
            with open("members.json", "r") as f:
                data = json.load(f)
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
        with open("members.json", "w") as f:
            json.dump(data, f, indent=4)

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
        await ctx.send(
            content="Successfully added new warn.",
            embed=embed
        )
        # Creates and sends embed
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
        print(error)
        await ctx.send(error)

    @commands.command(
        name='warns',
        description='See all the warns a user has',
        usage='<@offender>',
        aliases=['warnings']
    )
    async def warns_command(self, ctx, user:discord.Member):
        try:
            with open("members.json") as f:
                data = json.load(f)
        except FileNotFoundError:
            await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] does not have any warns.")
            return
    
        if 'warns' not in data.get(str(user.id), {}) or data[str(user.id)].get('warns') <= 0:
            await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] does not have any warns.")
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
    
        await ctx.send(
            content=None,
            embed=embed
        )
        # Send embed.
    @warns_command.error
    async def warns_handler(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'user':
                # Author did not specify user
                await ctx.send("Please mention someone to verify their warns.")
                return
        await ctx.send(error)

    @commands.command(
        name='remove_warn',
        description='Removes a specific warn from a specific user.',
        usage='@user 2',
        aliases=['removewarn','clearwarn']
    )
    @has_permissions(manage_messages=True)
    async def remove_warn_command(self, ctx, user: discord.Member, *, warn: str):
        try:
            with open("members.json") as f:
                data = json.load(f)
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
    
        await ctx.send(content='Are you sure you want to remove this warn? (Reply with y or n)', embed=confirmation_embed)
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
            json.dump(data, open("members.json", "w"), indent=4)
            await ctx.send(f"{ctx.author.name}, user [{user.name} ({user.id})] has had their warn removed.")
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
    async def edit_warn_command(self, ctx, user: discord.Member, *, warn: str):
        try:
            with open("members.json") as f:
                data = json.load(f)
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
    
        await ctx.send(content='Are you sure you want to edit this warn like this? (Reply with y/yes or n/no)', embed=confirmation_embed)
    
        msg = await self.bot.wait_for('message', check=check)
        reply = msg.content.lower()
    
        if reply in ('y', 'yes', 'confirm'):
            specified_warn['reason'] = warn_new_reason
            json.dump(data, open("members.json", "w"), indent=4)
            await ctx.send(f"[{ctx.author.name}], user [{user.name} ({user.id})] has had their warn edited.")
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
