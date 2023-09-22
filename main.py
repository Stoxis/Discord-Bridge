import traceback  
import discord
from discord.ext import commands
import json
import aiohttp
import re

# Todo queue for message edit-message delete
# Todo queue for reaction add-reaction remove
# ^^^ To prevent conflicts these functions must not run at the same time
# ^^^ They currently do

# Todo display message reacts under message (Draglox suggestion)
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

async def get_user_from_input(input_str):
    # Regular expression pattern to match user mentions and IDs
    user_pattern = re.compile(r'<@!?(\d+)>|(\d+)')

    # Try to find a match in the input string
    match = user_pattern.match(input_str)

    if match:
        # Check if a user mention (<@user_id> or <@!user_id>) was found
        if match.group(1):
            user_id = int(match.group(1))
        else:
            # Use the numeric ID if no mention was found
            user_id = int(match.group(2))
        
        try:
            # Get the user object
            user = await bot.fetch_user(user_id)
        except:
            return None
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

# Dictionary to store nicknames
nicknames = {}

# Load nicknames from a file on bot startup
def load_nicknames():
    global nicknames
    try:
        with open('nicknames.json', 'r') as file:
            nicknames = json.load(file)
    except FileNotFoundError:
        nicknames = {}

# Save nicknames to a file
def save_nicknames():
    with open('nicknames.json', 'w') as file:
        json.dump(nicknames, file, indent=4)

# Event listener for bot ready event
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    load_channel_pairs()
    load_message_pairs()
    load_nicknames()

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

# Command to set or display a nickname
@bot.command()
async def nickname(ctx, *, args=None):
    global nicknames
    if args:
        # User provided arguments, attempt to set a nickname
        user = await get_user_from_input(args)
        if user is None:
            if str(ctx.author.id) in nicknames: # If nickname already exists
                del nicknames[str(ctx.author.id)] # Delete old nickname
            # User is setting their own nickname
            nicknames[str(ctx.author.id)] = args
            save_nicknames()
            await ctx.send(embed=discord.Embed(description=f"Your nickname has been set to: {args}"))
            return
        user_id = str(user.id)

        if user_id in nicknames:
            # Displaying another user's nickname
            await ctx.send(embed=discord.Embed(description=f"{user.display_name}'s nickname is: {nicknames[user_id]}"))
        else:
            # User not found in nicknames dictionary
            await ctx.send(embed=discord.Embed(description="No nickname is set for this user."))
    else:
        # No arguments provided, display the sender's own nickname
        user_id = str(ctx.author.id)
        if user_id in nicknames:
            await ctx.send(embed=discord.Embed(description=f"Your nickname is: {nicknames[user_id]}"))
        else:
            await ctx.send(embed=discord.Embed(description="No nickname is set for you."))

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

    embed.add_field(
        name="^nickname <user_mention|user_id|nickname_here|nothing>",
        value="Set or display a nickname for yourself or another user",
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
        global nicknames
        if str(message.author.id) in nicknames: # Nickname exists
            username = nicknames[str(message.author.id)] # Use nickname
        else: # Nickanme doesn't exist
            username = message.author.display_name # Use display_name
        webhook_url, _ = channel_pairs[str(paired_channel_id)]
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            response = await webhook.send(username=username,content=message.content,avatar_url=message.author.display_avatar.url, wait=True)
            message_pairs[str(message.id)] = response.id
            save_message_pairs()

    await bot.process_commands(message)

# Event listener for raw message deletion events
@bot.event
async def on_raw_message_delete(payload):
    global message_pairs
    # Check if the message ID is in the message_pairs dictionary
    message_id = payload.message_id
    if str(message_id) in message_pairs:
        target_message_id = message_pairs[str(message_id)] #message_id is real msg
        del message_pairs[str(message_id)]
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
                    target_message = await target_channel.fetch_message(target_message_id)
                    print(f"Message({message_id}) deleted, propagating deletion to paired message({target_message_id})")
                    await target_message.delete()
                except discord.NotFound:
                    print(f"Paired message({target_message_id}) not found")

# Event listener for message edits
@bot.event
async def on_raw_message_edit(payload):
    # Check if the message ID is in the message_pairs dictionary
    message_id = payload.message_id
    if str(message_id) in message_pairs:
        target_message_id = message_pairs[str(message_id)] #message_id is real msg
    elif message_id in message_pairs.inverse:
        return
        #target_message_id = message_pairs.inverse[message_id][0] #message_id is bot msg (technically impossible because you can't edit the bot message)
    else:
        return
    # Find the paired channel for the current channel
    paired_channel_id = None
    paired_webhook_url = [v[0] for v in channel_pairs.values() if v[1] == payload.channel_id]
    paired_webhook_url = paired_webhook_url[0]

    # Check if the channel ID is in the paired channels dictionary
    for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            paired_channel_id = paired_id
            if paired_id is not None:
                # Get the target channel
                target_channel = bot.get_channel(paired_channel_id)
            
                if target_channel:
                    # Edit the mirrored message in the target channel
                    print(f"Message edited with ID: {message_id}")
                    try:
                        # Get the webhook and edit the message
                        webhook = discord.Webhook.from_url(paired_webhook_url, client=bot)
                        await webhook.edit_message(
                            target_message_id,
                            content=payload.data['content'],
                            attachments=payload.data['attachments'],
                            embeds=payload.data['embeds'],
                        )
                        print(f"Mirrored message edited successfully: {target_message_id}")
                    except discord.NotFound as e:
                        print(f"Mirrored message not found in target channel: {target_message_id}")
                    except Exception as e:
                        print(f"Error editing message: {e}")
                        
# Event listener for added reactions
@bot.event
async def on_raw_reaction_add(payload):
    # Check if reaction wasn't added by self
    if payload.member.id == bot.user.id:
        return
    global message_pairs
    print(f"Reaction added: {payload.emoji} by user {payload.user_id} in channel {payload.channel_id}")
    #print(message_pairs)

    # Check if the reacted message ID is in the message_pairs dictionary
    reacted_message_id = payload.message_id
    if str(reacted_message_id) in message_pairs:
        target_message_id = message_pairs[str(reacted_message_id)] #reacted_message_id is real msg
    elif reacted_message_id in message_pairs.inverse:
        target_message_id = message_pairs.inverse[int(reacted_message_id)][0] #reacted_message_id is bot msg
    else:
        return
    
    print(f"Reaction added: {payload.emoji} by user {payload.user_id} to message {reacted_message_id} in channel {payload.channel_id}")

    # Check if the target message is in a paired channel
    for channel_id, (webhook_url, target_channel_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            # Get the target channel
            target_channel = bot.get_channel(target_channel_id)

            if target_channel:
                try:
                    # Find the paired message in the target channel by ID
                    target_message = await target_channel.fetch_message(target_message_id)

                    if target_message:
                        # Loop through reactions on the paired message
                        for reaction in target_message.reactions:
                            if str(reaction.emoji) == str(payload.emoji):
                                print(f"Emoji {payload.emoji} is already among the reactions.")
                                break
                        else:
                            # Add the reaction to the real message
                            await target_message.add_reaction(payload.emoji.name)
                            print(f"Reaction: {payload.emoji} mirrored to paired message: {target_message_id}")
                    else:
                        print("Paired message not found")
                except discord.NotFound:
                    print(f"Paired message with ID {target_message_id} not found in target channel")
                except Exception as e:
                    print(f"Error handling reaction: {e}")

# Event listener for removed reactions
@bot.event
async def on_raw_reaction_remove(payload):
    # Check if reaction wasn't added by self
    if payload.user_id == bot.user.id:
        return

    print(f"Reaction removed: {payload.emoji} by user {payload.user_id} in channel {payload.channel_id}")

    # Check if the reacted message ID is in the message_pairs dictionary
    reacted_message_id = payload.message_id
    if str(reacted_message_id) in message_pairs:
        target_message_id = message_pairs[str(reacted_message_id)]  # reacted_message_id is real msg
    elif reacted_message_id in message_pairs.inverse:
        target_message_id = message_pairs.inverse[int(reacted_message_id)][0]  # reacted_message_id is bot msg
    else:
        return
        
    # Get reaction channel
    reaction_channel = bot.get_channel(payload.channel_id)
        
    users_reacted = [] 
    reactMsg = await reaction_channel.fetch_message(payload.message_id)
    # Loop through reactions on payload.message_id
    for reaction in reactMsg.reactions:
        if str(reaction.emoji) == str(payload.emoji):
            # Check if there are other users (besides the bot) who have reacted to original Msg (this prevents removing the reaction when it's still being used under a message)
            async for user in reaction.users():
                if user.id != bot.user.id:
                    users_reacted.append(user)
    
    # Check if the target message is in a paired channel
    for channel_id, (webhook_url, target_channel_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            # Get the target channel
            target_channel = bot.get_channel(target_channel_id)

            if target_channel:
                try:
                    # Find the paired message in the target channel by ID
                    target_message = await target_channel.fetch_message(target_message_id)

                    if target_message:
                        if len(users_reacted) == 0:
                            # Remove the reaction from the real message
                            await target_message.remove_reaction(payload.emoji, bot.user)
                            print(f"Reaction removed from paired message: {payload.emoji}")
                        else:
                            print(f"Reaction not removed from paired message: {payload.emoji} (Other users reacted)")
                    else:
                        print("Paired message not found")
                except discord.NotFound:
                    print(f"Paired message with ID {target_message_id} not found in target channel")
                except Exception as e:
                    print(f"Error handling reaction removal: {e}")

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)