import traceback  
import discord
from discord.ext import commands
import json
import aiohttp
import re

# Todo queue for message edit-message delete
# Todo queue for reaction add-reaction remove
# ^^^ To prevent conflicts these functions must not run at the same time

# Todo display message reacts under message (Draglox suggestion)
# Todo add nicknames
# Todo add custom profile picture command
# Todo add slash command functionality
# Todo Profile command that displays real & fake user information
# Todo Add multi-bridge support so three channels can be bridged in a row (how to do without database?)

# Bot token and prefix
TOKEN = 'Token_here'
PREFIX = '^'

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

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
# bd = bidict({'a': 1, 'b': 2})
# bd['a'] = 1
# bd.inverse[1] = ['a'] 

# Bi-Directional Dictionary to store message pairs
message_pairs = bidict()

# Load channel pairs from a file on bot startup
def load_message_pairs():
    global message_pairs
    try:
        with open('message_pairs.json', 'r') as file:
            message_pairs = bidict(json.load(file))
    except FileNotFoundError:
        message_pairs = bidict()

# Save channel pairs to a file
def save_message_pairs():
    global message_pairs
    with open('message_pairs.json', 'w') as file:
        json.dump(message_pairs, file, indent=4)

# Create a custom check to verify "create webhook" permission
def has_create_webhook_permission():
    async def predicate(ctx):
        if ctx.guild:
            # Check if the user has the "create webhook" permission in the current guild
            permissions = ctx.author.guild_permissions
            if permissions.manage_webhooks:
                return True
            else:
                await ctx.send("You don't have permission to manage webhooks.")
                return False
        else:
            # This command only applies to guilds (servers)
            await ctx.send("This command can only be used in a server (guild).")
            return False

    return commands.check(predicate)

async def get_channel_from_input(input_str):
    # Regular expression pattern to match channel mentions and IDs
    channel_pattern = re.compile(r'<#(\d+)>|(\d+)')

    # Try to find a match in the input string
    match = channel_pattern.match(input_str)

    if match:
        # Check if a channel mention (<#channel_id>) was found
        if match.group(1):
            channel_id = int(match.group(1))
        else:
            # Use the numeric ID if no mention was found
            channel_id = int(match.group(2))
        
        # Get the channel object
        channel = bot.get_channel(channel_id)

        return channel
    else:
        return None

# Dictionary to store channel pairs
channel_pairs = {}

# Load channel pairs from a file on bot startup
def load_channel_pairs():
    global channel_pairs
    try:
        with open('channel_pairs.json', 'r') as file:
            channel_pairs = json.load(file)
    except FileNotFoundError:
        channel_pairs = {}

# Save channel pairs to a file
def save_channel_pairs():
    global channel_pairs
    with open('channel_pairs.json', 'w') as file:
        json.dump(channel_pairs, file, indent=4)
	# If you don't load_channel_pairs() after saving the new pair the new pair isn't recognized until the bot is restarted and the new pair is loaded.
    load_channel_pairs()

# Event listener for bot ready event
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    load_channel_pairs()
    load_message_pairs()

# Command to pair two channels
@bot.command()
@has_create_webhook_permission()
async def pair(ctx, channel1str, channel2str):
    global channel_pairs
    channel1 = await get_channel_from_input(channel1str)
    channel2 = await get_channel_from_input(channel2str)
    fetched_channels = None
    if channel1 == None:
        fetched_channels = channel1str
    if channel2 == None:
        if fetched_channels is not None:
            fetched_channels += ", " + channel2str
        else:
            fetched_channels = channel2str
    if channel1 == None or channel2 == None:
        await ctx.send(f':negative_squared_cross_mark: I\'m unable to access the channel(s) listed: {fetched_channels}')
        return

    # Check if the bot has permission to create webhooks in both guilds
    if (
        not ctx.guild.me.guild_permissions.manage_webhooks
        or not channel1.guild.me.guild_permissions.manage_webhooks
        or not channel2.guild.me.guild_permissions.manage_webhooks
    ):
        await ctx.send(':negative_squared_cross_mark: I require permissions to create a webhook in both guilds!')
        return

    # Check if both channels are provided
    if channel2 is None:
        await ctx.send(':negative_squared_cross_mark: You need to provide two channels to pair.')
        return

    try:
        # Create webhooks for both channels in their respective guilds
        webhook1 = await channel1.create_webhook(name='PairBot Webhook')
        webhook2 = await channel2.create_webhook(name='PairBot Webhook')

        # Save the channel pair in the dictionary
        channel_pairs[channel1.id] = (webhook1.url, channel2.id)
        channel_pairs[channel2.id] = (webhook2.url, channel1.id)
        save_channel_pairs()

        await ctx.send(':white_check_mark: Webhook successfully created!')
    except discord.errors.HTTPException as e:
        if e.status == 400 and e.code == 30007:
            await ctx.send(':x: Maximum number of webhooks reached in one of the channels. You may need to delete some webhooks in that channel to proceed.')
        else:
            await ctx.send(':x: An error occurred while creating the webhook.')

# Command to unpair two channels
@bot.command()
@has_create_webhook_permission()
async def unpair(ctx, channel1str, channel2str):
    global channel_pairs
    # Fix bug: Only remove this pair, if channel1 or 2 are linked to other non-specified channels, preserve those connections (current code unpairs those as well)
    channel1 = await get_channel_from_input(channel1str)
    channel2 = await get_channel_from_input(channel2str)
    # Check if the channels exist
    fetched_channels = None
    if channel1 == None:
        fetched_channels = channel1str
    if channel2 == None:
        if fetched_channels is not None:
            fetched_channels += ", " + channel2str
        else:
            fetched_channels = channel2str
    if channel1 == None or channel2 == None:
        await ctx.send(f':negative_squared_cross_mark: I\'m unable to access the channel(s) listed: {fetched_channels}')
        return
    # Check if the pairing exists
    fetched_channels = None
    if(str(channel1.id) not in channel_pairs):
        fetched_channels = channel1.mention
    if(str(channel2.id) not in channel_pairs):
        if fetched_channels is not None:
            fetched_channels += ", " + channel2.mention
        else:
            fetched_channels = channel2.mention
    if (str(channel1.id) not in channel_pairs) or (str(channel2.id) not in channel_pairs):
        await ctx.send(f':negative_squared_cross_mark: The channel(s) listed aren\'t paired: {fetched_channels}')
        return

    # Delete the webhooks
    await discord.Webhook.from_url(channel_pairs[str(channel1.id)][0], session=bot.http._HTTPClient__session).delete()
    await discord.Webhook.from_url(channel_pairs[str(channel2.id)][0], session=bot.http._HTTPClient__session).delete()

    # Remove the pair from the dictionary
    del channel_pairs[str(channel1.id)]
    del channel_pairs[str(channel2.id)]
    save_channel_pairs()

    await ctx.send(':white_check_mark: Webhook pair destroyed!')

# Command to list channel pairs
@bot.command()
@has_create_webhook_permission()
async def list(ctx):
    processed_channels = set()  # Create a set to keep track of processed channel IDs
    pair_list = []

    for ch1, (webhook_url, ch2) in channel_pairs.items():
        # Check if the channel ID has already been processed
        ch1 = int(ch1)
        if ch1 in processed_channels and ch2 in processed_channels:
            continue

        pair_list.append(f'<#{ch1}> :left_right_arrow: <#{ch2}>')
        processed_channels.add(ch1)
        processed_channels.add(ch2)

    # Create an embed to send the list
    embed = discord.Embed(
        title="Channel Pairs",
        description="\n".join(pair_list),
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed)

# Help command
@bot.command()
@has_create_webhook_permission()
async def help(ctx):
    # Create an embed for the help message
    embed = discord.Embed(
        title="Available Commands",
        description="Here are the available commands:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="^pair <Channel> <Channel>",
        value="Pair two channels",
        inline=False
    )

    embed.add_field(
        name="^unpair <Channel> <Channel>",
        value="Unpair two channels",
        inline=False
    )

    embed.add_field(
        name="^list",
        value="List paired channels",
        inline=False
    )

    embed.add_field(
        name="^help",
        value="Show this message",
        inline=False
    )

    await ctx.send(embed=embed)


# Event to handle message copying
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    global message_pairs

    # Find the paired channel for the current channel
    paired_channel_id = None
    for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if message.channel.id == int(channel_id):
            paired_channel_id = paired_id
            break

    if paired_channel_id:
        webhook_url, _ = channel_pairs[str(paired_channel_id)]
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            response = await webhook.send(username=message.author.display_name,content=message.content,avatar_url=message.author.display_avatar.url, wait=True)
            message_pairs[int(message.id)] = response.id
            save_message_pairs()

    await bot.process_commands(message)

# Event listener for raw message deletion events
@bot.event
async def on_raw_message_delete(payload):
    if(payload.cached_message is None):
        return
    # Check if the message ID is in the message_pairs dictionary
    message_id = payload.message_id
    if message_id in message_pairs:
        target_message_id = message_pairs[message_id] #message_id is real msg
        del message_pairs[message_id]
    elif message_id in message_pairs.inverse:
        target_message_id = message_pairs.inverse[message_id][0] #message_id is bot msg
        del message_pairs[target_message_id]
    else:
        return
    save_message_pairs()
    
    # Find the paired channel for the current channel
    paired_channel_id = None
    for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            # Get the target channel
            target_channel = bot.get_channel(paired_id)
            if target_channel:
                try:
                    msg = await target_channel.fetch_message(target_message_id)
                    print(f"Message({message_id}) deleted, propagating deletion to paired message({target_message_id})")
                    await msg.delete()
                except discord.NotFound:
                    print(f"Paired message({target_message_id}) not found")
            


# on_message_edit WILL ONLY REACT to messages sent AFTER the bot was started,
# it's impossible to re-cache messages messages sent before the bot was started.

# Event listener for message edits
@bot.event
async def on_message_edit(before, after):
    # Ignore edits done by the bot itself
    if before.author.bot:
        return
    
    # Find the paired channel for the current channel
    paired_channel_id = None
    paired_webhook_url = [v[0] for v in channel_pairs.values() if v[1] == before.channel.id]
    paired_webhook_url = paired_webhook_url[0]
    
    for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if before.channel.id == int(channel_id):
            paired_channel_id = paired_id		
            break
	
    # Check if the channel ID is in the paired channels dictionary
    if paired_channel_id is not None:
        # Get the target channel
        target_channel = bot.get_channel(paired_channel_id)
		
        if target_channel:
            # Fetch the mirrored message from the target channel's webhook
            async for msg in target_channel.history(limit=100):  # Adjust the limit as needed
                if (before.author.global_name == None):
                    beforeUsername = before.author.name
                else:
                    beforeUsername = before.author.global_name

                if (msg.author.global_name == None):
                    targetUsername = msg.author.name
                else:
                    targetUsername = msg.author.global_name

                if (
                    msg.content == before.content
                    and targetUsername == beforeUsername
                ):
                    # Edit the mirrored message in the target channel
                    print(f"Editing message with ID: {msg.id}")
                    try:
                        # Get the webhook and edit the message
                        webhook = discord.Webhook.from_url(paired_webhook_url, client=bot)
                        await webhook.edit_message(
                            msg.id,
                            content=after.content,
                            attachments=after.attachments,
                            embeds=after.embeds,
                        )
                        print(f"Message edited successfully: {msg.id}")
                    except discord.NotFound as e:
                        print(f"Message not found in target channel: {msg.id}")
                    except Exception as e:
                        print(f"Error editing message: {e}")
                    break
        else:
            print(f"Target channel not found: {paired_channel_id}")

@bot.event
async def on_raw_reaction_add(payload):
    # Check if reaction wasn't added by self
    if payload.member.id == bot.user.id:
        return
    
    print(f"Reaction added: {payload.emoji} by user {payload.user_id} in channel {payload.channel_id}")

    # Check if the reacted message is in a paired channel
    for channel_id, (webhook_url, target_channel_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            # Get the target channel
            target_channel = bot.get_channel(target_channel_id)
			
            # Get reaction channel
            reaction_channel = bot.get_channel(payload.channel_id)

            if target_channel:
                # Find the real message in the target channel
                async for msg in target_channel.history(limit=100):  # Adjust the limit as needed
                    reactMsg = await reaction_channel.fetch_message(payload.message_id)
                    if (reactMsg.author.global_name == None):
                        reactedUsername = reactMsg.author.name
                    else:
                        reactedUsername = reactMsg.author.global_name
                    if (msg.author.global_name == None):
                        targetUsername = msg.author.name
                    else:
                        targetUsername = msg.author.global_name
                    if (
                        msg.content == reactMsg.content
                        and targetUsername == reactedUsername
                    ):
                        real_message = msg
                        break
                else:
                    real_message = None

                if real_message:
                    print(f"Real message found with ID {real_message.id}")

                    # Loop through reactions on the real message
                    for reaction in real_message.reactions:
                        if str(reaction.emoji) == str(payload.emoji):
                            print(f"Emoji {payload.emoji} is already among the reactions.")
                            break
                    else:
                        # Add the reaction to the real message
                        await real_message.add_reaction(payload.emoji.name)
                        print(f"Reaction mirrored to real message: {payload.emoji}")
                else:
                    print("Real message not found")

@bot.event
async def on_raw_reaction_remove(payload):
    # Check if reaction wasn't added by self
    if payload.user_id == bot.user.id:
	    return
    
    print(f"Reaction removed: {payload.emoji} by user {payload.user_id} in channel {payload.channel_id}")

    # Check if the reacted message is in a paired channel
    for channel_id, (webhook_url, target_channel_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            # Get the target channel
            target_channel = bot.get_channel(target_channel_id)
            
            # Get reaction channel
            reaction_channel = bot.get_channel(payload.channel_id)

            if target_channel:
                # Find the real message in the target channel
                async for msg in target_channel.history(limit=100):  # Adjust the limit as needed
                    reactMsg = await reaction_channel.fetch_message(payload.message_id)
                    if (reactMsg.author.global_name == None):
                        reactedUsername = reactMsg.author.name
                    else:
                        reactedUsername = reactMsg.author.global_name
                    if (msg.author.global_name == None):
                        targetUsername = msg.author.name
                    else:
                        targetUsername = msg.author.global_name
                    if (
                        msg.content == reactMsg.content
                        and targetUsername == reactedUsername
                    ):
                        real_message = msg
                        break
                else:
                    real_message = None
                if real_message:
                    
                    users_reacted = ""
                    # Loop through reactions on reactMsg
                    for reaction in reactMsg.reactions:
                        if str(reaction.emoji) == str(payload.emoji):
                            # Check if there are other users (besides the bot) who have reacted to reactMsg
                            users_reacted = []
                            async for user in reaction.users():
                                users_reacted.append(user)

                    #print(users_reacted)
                    #print(len(users_reacted))
                    if len(users_reacted) > 0:  # There are other non-bot users who reacted
                        print(f"Reaction not removed from reactMsg: {payload.emoji} (Other users reacted)")
                    else:
                        # Loop through reactions on the real message
                        for reaction in real_message.reactions:
                            if str(reaction.emoji) == str(payload.emoji):
                                # Remove the reaction from the real message
                                await real_message.remove_reaction(payload.emoji, bot.user)
                                print(f"Reaction removed from real message: {payload.emoji}")
                                break
                else:
                    print("Real message not found")

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)