import discord
from discord.ui import Button, View
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
from requests import get
import json
import compress_json
import aiohttp
import re
import os

# Todo queue for message edit-message delete
# Todo queue for reaction add-reaction remove
# ^^^ To prevent conflicts these functions must not run at the same time
# ^^^ They currently do

# Todo add custom profile picture command
# Todo add slash command functionality
# Todo Profile command that displays real & fake user information
# Todo Add multi-bridge support so three channels can be bridged in a row (how to do without database?)

# todo: add permissions checking to get_author and warning commands

# todo: mirror thread creation and messages in threads

# todo: mirror replies

# todo: rewrite channel_pairs for loops to use if `value` in `dict` and directly reference the key value pairs instead of looping through the entire dictionary

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

# Bi-Directional Dictionary to store message channel pairs
message_channel_pairs = bidict()

# Bi-Directional Dictionary to store message message pairs
message_pairs = bidict()

# Dictionary to store reactions to messages
message_reactions = {}

# Dictionary to store channel pairs
channel_pairs = {}

# Dictionary to store members
members = {}

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

def save_data(filename, data):
    compress_json.dump(data, filename)

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

def get_original_message(message_id): # Outputs the key in a dictionary if either the key or value of that pair matches
    for key, value in message_pairs.items():
        if value == message_id or key == message_id: # Key is real message id
            channel = bot.get_channel(message_channel_pairs[str(key)])
            real_message = channel.fetch_message(key)
            return real_message
    return None  # Return None if the value is not found in the dictionary

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

def check_in():
    ip = get('https://api.ipify.org').content.decode('utf8')
    print('My public IP address is: {}'.format(ip))

def update_channel_pairs_format(channel_pairs):
    try:
        for ch1, (webhook_url, ch2) in channel_pairs.items():
            channel_pairs[str(ch1)]["webhook_url"]
            return channel_pairs, False
    except:
        print("old dict format detected, converting...")
        new_channel_pairs = {}
        for ch1, (webhook_url, ch2) in channel_pairs.items():
            new_channel_pairs[str(ch1)] = {
                "webhook_url": webhook_url,
                "paired_id": ch2
            }
        else:
            return new_channel_pairs, True


# Event listener for bot ready event
@bot.event
async def on_ready():
    global channel_pairs
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    check_in()
    
    load_data('channel_pairs.json.lzma', 'channel_pairs', {})
    # Check if channel_pairs is in the old format
    if isinstance(globals()['channel_pairs'], dict):
        # Convert to the new format
        channel_pairs, isFormatOld = update_channel_pairs_format(globals()['channel_pairs'])
        if isFormatOld:
            # If old format save the updated channel_pairs to the file
            save_data('channel_pairs.json.lzma', channel_pairs)
    
    load_data('message_pairs.json.lzma', 'message_pairs', bidict())
    load_data('message_channel_pairs.json.lzma', 'message_channel_pairs', bidict())
    load_data('message_reactions.json.lzma', 'message_reactions', {})
    load_data('members.json.lzma', 'members', {})
    cogs = []
    for cog_file in os.listdir('cogs/'):
        if cog_file.endswith('.py') and cog_file != 'slash.py':
            cog_import = 'cogs.' + cog_file.split('.')[0]
            cogs.append(cog_import)
            print(f'Found {cog_file} as cog')
    
    for cog in cogs:
        print(f'Loading {cog}')
        try:
            await bot.load_extension(cog)
        except discord.ext.commands.errors.ExtensionAlreadyLoaded:
            # Bot tried to load a cog that was already loaded.
            print(f"Tried to load a cog/extension that was already loaded ({cog})")

# Command to pair two channels
@bot.command(aliases=['pairchannels', 'pairch', 'pairchan', 'link', 'linkchans', 'linkchannels'])
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
        channel_pairs[channel1.id] = {
            "webhook_url": webhook1.url,
            "paired_id": channel2.id
        }
        
        channel_pairs[channel2.id] = {
            "webhook_url": webhook2.url,
            "paired_id": channel1.id
        }
        
        # Save the updated channel_pairs to the file
        save_data('channel_pairs.json.lzma', channel_pairs)

        await ctx.send(':white_check_mark: Webhook successfully created!')
    except discord.errors.HTTPException as e:
        if e.status == 400 and e.code == 30007:
            await ctx.send(':x: Maximum number of webhooks reached in one of the channels. You may need to delete some webhooks in that channel to proceed.')
        else:
            await ctx.send(':x: An error occurred while creating the webhook.')

# Command to unpair two channels
@bot.command(aliases=['unpairch', 'unpairchan', 'unlink', 'unlinkchans', 'unlinkchannels'])
@has_create_webhook_permission()
async def unpair(ctx, channel1str, channel2str):
    global channel_pairs

    # Fix bug: Only remove this pair, if channel1 or 2 are linked to other non-specified channels, preserve those connections
    channel1 = await get_channel_from_input(channel1str)
    channel2 = await get_channel_from_input(channel2str)

    # Check if the channels exist
    fetched_channels = []

    if channel1 is None:
        fetched_channels.append(channel1str)
    if channel2 is None:
        fetched_channels.append(channel2str)

    if fetched_channels:
        await ctx.send(f':negative_squared_cross_mark: I\'m unable to access the channel(s) listed: {", ".join(fetched_channels)}')
        return

    # Check if the pairing exists
    missing_pair = []

    if str(channel1.id) not in channel_pairs:
        missing_pair.append(channel1.mention)
    if str(channel2.id) not in channel_pairs:
        missing_pair.append(channel2.mention)

    if missing_pair:
        await ctx.send(f':negative_squared_cross_mark: The channel(s) listed aren\'t paired: {", ".join(missing_pair)}')
        return

    # Delete the webhooks
    await discord.Webhook.from_url(channel_pairs[str(channel1.id)]["webhook_url"], session=bot.http._HTTPClient__session).delete()
    await discord.Webhook.from_url(channel_pairs[str(channel2.id)]["webhook_url"], session=bot.http._HTTPClient__session).delete()

    # Remove the pair from the dictionary
    del channel_pairs[str(channel1.id)]
    del channel_pairs[str(channel2.id)]

    # Save the updated channel_pairs to the file
    save_data('channel_pairs.json.lzma', channel_pairs)

    await ctx.send(':white_check_mark: Webhook pair destroyed!')

# Command to list channel pairs
@bot.command(aliases=['listpairs', 'listchans', 'listchannels', 'viewpairs', 'viewchans', 'viewchannels'])
@has_create_webhook_permission()
async def list(ctx):
    processed_channels = set()  # Create a set to keep track of processed channel IDs
    pair_list = []

    for channel_id, data in channel_pairs.items(): #for ch1, (webhook_url, ch2) in channel_pairs.items():
        # Check if the channel ID has already been processed
        ch1 = int(channel_id)
        ch2 = int(data["paired_id"])
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
@bot.command(aliases=['nick', 'setnick', 'setnickname', 'changename']) # Todo add nickname removal option & ability to set nickname FOR users if you have set_nickname permission.
async def nickname(ctx, *, args=None):
    global members
    if args:
        # User provided arguments, attempt to set a nickname
        user = await get_user_from_input(args)
        if user is None:
            if str(ctx.author.id) in members and "nickname" in members[str(ctx.author.id)]: # If nickname already exists
                del members[str(ctx.author.id)]["nickname"] # Delete old nickname
            elif str(ctx.author.id) not in members:
                members[str(ctx.author.id)] = {}
            # Check for duplicate nickname
            for user_id, user_data in members.items():
                if 'nickname' not in user_data:
                    continue
                if user_data['nickname'] == args:
                    await ctx.send(embed=discord.Embed(description="That nickname is already in use by another user."))
                    break
            else: # Else is only activated if a break statement is never encountered during the for loop
                # User is setting their own nickname
                members[str(ctx.author.id)]["nickname"] = args
                save_data('members.json.lzma', members)
                await ctx.send(embed=discord.Embed(description=f"Your nickname has been set to: {args}"))
                return
            return
        user_id = str(user.id)
        if str(user_id) in members and 'nickname' in members[str(user_id)]:
            # Displaying another user's nickname
            await ctx.send(embed=discord.Embed(description=f"{user.display_name}'s nickname is: {members[str(user_id)]['nickname']}"))
        else:
            # User not found in nicknames dictionary
            await ctx.send(embed=discord.Embed(description="No nickname is set for this user."))
    else:
        # No arguments provided, display the sender's own nickname
        user_id = str(ctx.author.id)
        if str(user_id) in members and 'nickname' in members[str(user_id)]:
            await ctx.send(embed=discord.Embed(description=f"Your nickname is: {members[str(user_id)]['nickname']}"))
        else:
            await ctx.send(embed=discord.Embed(description="No nickname is set for you."))

@bot.command(aliases=['getauth', 'getauthor', 'author'])
@has_permissions(manage_messages=True) # Todo: use the message_channel_pairs command to get the channel
async def get_author(ctx, message_id=None):
    if message_id is None:
        await ctx.send("Please provide a message ID.")
        return
    try:
        message_id = int(message_id)
    except:
        await ctx.send("Message IDs should only contain numbers, please provide a valid message ID.")
        return
    # Check if the provided message_id exists in the message_pairs dictionary
    original_id = None  # Store the original message_id
    isOriginal = False
    for original, paired in message_pairs.items():
        if str(paired) == str(message_id):
            # Found a matching pair, use the original message_id
            original_id = original
            break
        elif str(original) == str(message_id):
            # original_id = original
            isOriginal = True
            break
    if isOriginal:
        await ctx.send("You provided the message ID of the original author.")
        return
    if original_id is not None:
        # Iterate through guilds and text channels to find the message
        for guild in bot.guilds:
            for channel in guild.text_channels:
                try:
                    message = await channel.fetch_message(original_id)
                    if message:
                        author_id_msg = await ctx.send(f"Message author id: {message.author.id}")
                        await ctx.message.delete(delay=30)
                        await author_id_msg.delete(delay=30)
                        return  # Exit the loop if message is found
                except discord.NotFound:
                    continue  # Continue searching if message is not found

        # If the loop finishes and the message is still not found, send a message
        await ctx.send("Paired message exists within json but not on Discord (tell bot owner this!)")
    else:
        await ctx.send("Paired message not found")
    
# Help command
@bot.command(aliases=['helpme', 'commands', 'cmds', 'info'])
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
        name="^nickname <user_mention|user_id|nickname_here|nothing>",
        value="Set or display a nickname for yourself or another user",
        inline=False
    )
    
    embed.add_field(
        name="^get_author <paired_message_id>",
        value="Get the real author of a message with the message ID (useful for warns)",
        inline=False
    )

    embed.add_field(
        name="^help",
        value="Show this message",
        inline=False
    )
    
    embed.add_field(
        name="^purge <amount>",
        value="Deletes a specified number of messages in the current and paired channel",
        inline=False
    )
    
    embed.add_field(
        name="^warn <user_mention|user_id|paired_message_id> <reason>",
        value="Warn a user with a reason",
        inline=False
    )
    
    embed.add_field(
        name="^warns <user_mention|user_id|paired_message_id>",
        value="See all the warns a user has",
        inline=False
    )
    
    embed.add_field(
        name="^remove_warn <user_mention|user_id|paired_message_id> <warn_number>",
        value="Remove a specific warn from a user",
        inline=False
    )
    
    embed.add_field(
        name="^edit_warn <user_mention|user_id|paired_message_id> <warn_number>",
        value="Edit a specific warn from a user",
        inline=False
    )

    await ctx.send(embed=embed)

async def create_mirrored_message_embed(message):
    global members
    if str(message.author.id) in members and 'nickname' in members[str(message.author.id)]: # Nickname exists
        username = members[str(message.author.id)]['nickname'] # Use nickname
    else: # Nickanme doesn't exist
        username = message.author.display_name # Use display_name
    # Create an empty embed
    embed = discord.Embed()

    # Set the title of the embed to match the message content
    embed.description = " "

    # Set the color of the embed (hex color code)
    embed.color = 0x00FFFF

    # Set the footer of the embed to display the author's name
    embed.set_footer(
        text=f"{username}: {message.content}",
        icon_url=message.author.display_avatar.url,
    )

    # Create a view to add the button component
    view = discord.ui.View()
    # Add a button component for "Jump to Original Message"
    view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="ᴶᵘᵐᵖ ᵗᵒ ᴿᵉᵖˡʸ", url=f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"))

    return embed, view


# Event to handle message copying
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.reference:
        print(message.reference)
    # Find the paired channel for the current channel
    for channel_id, data in channel_pairs.items(): #for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if message.channel.id == int(channel_id):
            paired_id = data['paired_id']
            webhook_url = data['webhook_url']
            global message_pairs
            global message_channel_pairs
            global members
            if str(message.author.id) in members and 'nickname' in members[str(message.author.id)]: # Nickname exists
                username = members[str(message.author.id)]['nickname'] # Use nickname
            else: # Nickanme doesn't exist
                username = message.author.display_name # Use display_name
            webhook_url = channel_pairs[str(paired_id)]["webhook_url"]
            async with aiohttp.ClientSession() as session:
                if message.reference:
                    embeds = []
                    view = None
                    if str(message.reference.message_id) in message_pairs: # Get the opposite message id since the reply will be in the paired channel
                        target_message_id = message_pairs[str(message.reference.message_id)] #message.reference.message_id is real msg
                    elif int(message.reference.message_id) in message_pairs.inverse:
                        target_message_id = message_pairs.inverse[int(message.reference.message_id)][0] #message.reference.message_id is bot msg
                    else:
                        target_message_id = None
                    if target_message_id:
                        channel = bot.get_channel(message_channel_pairs[str(target_message_id)])
                        reference_message = await channel.fetch_message(target_message_id)
                        embed, view = await create_mirrored_message_embed(reference_message)
                        embeds.append(embed)
                        print(embed)
                else:
                    embeds = [] 
                    view = None
                files = []
                for attachment in message.attachments:
                    file = await attachment.to_file(use_cached=True, spoiler=attachment.is_spoiler())
                    files.append(file)
                webhook = discord.Webhook.from_url(webhook_url, session=session)
                webhook = await bot.fetch_webhook(webhook.id) # Todo: Change channel pairs code to save webhook.id instead of webhook url, I *really* don't want to recode it though...
                if view:
                    response = await webhook.send(username=username,content=message.content,avatar_url=message.author.display_avatar.url,files=files,embeds=embeds, view=view, wait=True)
                else:
                    response = await webhook.send(username=username,content=message.content,avatar_url=message.author.display_avatar.url,files=files,embeds=embeds, wait=True)
                message_pairs[str(message.id)] = response.id
                save_data('message_pairs.json.lzma', message_pairs)
                message_channel_pairs[str(message.id)] = message.channel.id # Real message
                message_channel_pairs[str(response.id)] = response.channel.id # Mirrored message
                save_data('message_channel_pairs.json.lzma', message_channel_pairs)
            break
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
    global message_channel_pairs
    if str(message_id) in message_channel_pairs:
        del message_channel_pairs[str(message_id)]
    save_data('message_pairs.json.lzma', message_pairs)
    save_data('message_channel_pairs.json.lzma', message_channel_pairs)
    
    # Find the paired channel for the current channel
    for channel_id, data in channel_pairs.items(): #for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            # Get the target channel
            paired_id = data['paired_id']
            target_channel = bot.get_channel(paired_id)
            if target_channel:
                try:
                    target_message = await target_channel.fetch_message(target_message_id)
                    print(f"Message({message_id}) deleted, propagating deletion to paired message({target_message_id})")
                    await target_message.delete()
                except discord.NotFound:
                    print(f"Paired message({target_message_id}) not found")

def delete_pair(m):
    global message_pairs
    global message_channel_pairs
    message_id = m.id
    if str(message_id) in message_pairs:
        del message_pairs[str(message_id)] #message_id is real msg
    elif int(message_id) in message_pairs.inverse:
        target_message_id = message_pairs.inverse[int(message_id)][0] #message_id is bot msg
        del message_pairs[target_message_id]
    if str(message_id) in message_channel_pairs:
        del message_channel_pairs[str(message_id)]
    #print(message_id)
    return True

@bot.command(aliases=['purgech', 'purgechan', 'delete', 'clear', 'cleanup'])
@has_permissions(administrator=True)
async def purge(ctx, amount: int):
    if str(ctx.channel.id) not in channel_pairs:
        await ctx.send("This channel is not paired with another channel.")
        return
    global message_pairs
    global message_channel_pairs
    first = True
    for channel_id, data in channel_pairs.items(): #for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if str(ctx.channel.id) == str(channel_id):
            paired_channel = bot.get_channel(data['paired_id'])
            
            if not paired_channel:
                #await ctx.send("Paired channel not found.")
                continue
            
            if first: # Just incase there's multiple paired channels
                # Delete messages in the current channel
                deleted = await ctx.channel.purge(limit=amount + 1, check=delete_pair)  # +1 to include the purge command message itself
                first = False
            
            # Delete messages in the paired channel
            deleted_paired = await paired_channel.purge(limit=amount + 1, check=delete_pair)  # +1 to include the purge command message itself
            
            # Update message_pairs and message_channel_pairs to reflect message purge
            save_data('message_pairs.json.lzma', message_pairs)
            save_data('message_channel_pairs.json.lzma', message_channel_pairs)
            
            purge_message = await ctx.send(f"Purged {len(deleted)-1} messages in this channel and {len(deleted_paired)-1} messages in the paired channel.")
            await purge_message.delete(delay=30)
            break
    else:
        deleted = await ctx.channel.purge(limit=amount + 1)
        purge_message = await ctx.send(f"Purged {len(deleted)-1} messages.")
        await purge_message.delete(delay=30)
        

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
    paired_webhook_url = channel_pairs[str(channel_pairs[str(payload.channel_id)]["paired_id"])]["webhook_url"]

    # Check if the channel ID is in the paired channels dictionary
    for channel_id, data in channel_pairs.items(): #for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            if data['paired_id'] is not None:
                # Get the target channel
                target_channel = bot.get_channel(data['paired_id'])
            
                if target_channel:
                    # Edit the mirrored message in the target channel
                    print(f"Message edited with ID: {message_id}")
                    try:
                        # Find the paired message in the target channel by ID
                        target_message = await target_channel.fetch_message(target_message_id)
                        # Get the webhook and edit the message
                        webhook = discord.Webhook.from_url(paired_webhook_url, client=bot)
                        await webhook.edit_message(
                            target_message_id,
                            content=payload.data['content'],
                            attachments=payload.data['attachments'],
                            embeds=target_message.embeds,
                        )
                        print(f"Mirrored message edited successfully: {target_message_id}")
                        await update_message_reaction_count(target_channel, bot.get_channel(payload.channel_id), target_message_id, message_id)
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

    # Check if the reacted message ID is in the message_pairs dictionary
    reacted_message_id = payload.message_id
    if str(reacted_message_id) in message_pairs:
        target_message_id = message_pairs[str(reacted_message_id)] #reacted_message_id is real msg
        bot_message_id = target_message_id
        user_message_id = reacted_message_id
    elif reacted_message_id in message_pairs.inverse:
        target_message_id = message_pairs.inverse[int(reacted_message_id)][0] #reacted_message_id is bot msg
        bot_message_id = reacted_message_id
        user_message_id = target_message_id
    else:
        return
    emoji = str(payload.emoji)
    print(f"Reaction added: {emoji} by user {payload.user_id} to message {reacted_message_id} in channel {payload.channel_id}")

    # Check if the target message is in a paired channel 
    for channel_id, data in channel_pairs.items(): #for channel_id, (webhook_url, target_channel_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            target_channel = bot.get_channel(data["paired_id"])
            if target_channel:
                global message_reactions
                reaction_channel = bot.get_channel(payload.channel_id)
            
                if str(reacted_message_id) not in message_reactions:
                    message_reactions[str(reacted_message_id)] = {}
                    message_reactions[str(target_message_id)] = {}
            
                if emoji in message_reactions[str(reacted_message_id)]:
                    message_reactions[str(reacted_message_id)][emoji] += 1 # Count reactions from each message every single time? that way desync doesn't happen while offline???
                else:
                    message_reactions[str(reacted_message_id)][emoji] = 1
                save_data('message_reactions.json.lzma', message_reactions)
                await update_message_reaction_count(target_channel, reaction_channel, bot_message_id, user_message_id)
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
                            await target_message.add_reaction(payload.emoji)
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

    # Check if the reacted message ID is in the message_pairs dictionary
    reacted_message_id = payload.message_id
    if str(reacted_message_id) in message_pairs:
        target_message_id = message_pairs[str(reacted_message_id)]  # reacted_message_id is real msg
        bot_message_id = target_message_id
        user_message_id = reacted_message_id
    elif reacted_message_id in message_pairs.inverse:
        target_message_id = message_pairs.inverse[int(reacted_message_id)][0]  # reacted_message_id is bot msg
        bot_message_id = reacted_message_id
        user_message_id = target_message_id
    else:
        return
    print(f"Reaction removed: {payload.emoji} by user {payload.user_id} to message {reacted_message_id} in channel {payload.channel_id}")
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
    for channel_id, data in channel_pairs.items(): #for channel_id, (webhook_url, target_channel_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            # Get the target channel
            target_channel = bot.get_channel(data["paired_id"])

            if target_channel:
                global message_reactions
                
                emoji = str(payload.emoji)
            
                if str(reacted_message_id) not in message_reactions:
                    message_reactions[str(reacted_message_id)] = {}
                    message_reactions[str(target_message_id)] = {}
            
                if message_reactions[str(reacted_message_id)][emoji] <= 0:
                    message_reactions[str(reacted_message_id)][emoji] = 0
                    print("Negative reaction value!! Incorrect negative reaction count avoided!")
                elif emoji in message_reactions[str(reacted_message_id)]:
                    message_reactions[str(reacted_message_id)][emoji] -= 1
                else:
                    message_reactions[str(reacted_message_id)][emoji] = 0
                save_data('message_reactions.json.lzma', message_reactions)
                await update_message_reaction_count(target_channel, reaction_channel, bot_message_id, user_message_id)
                try:
                    # Find the paired message in the target channel by ID
                    target_message = await target_channel.fetch_message(target_message_id)

                    if target_message:
                        if len(users_reacted) == 0:
                            # Remove the reaction
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

async def update_message_reaction_count(target_channel, reaction_channel, bot_message_id, user_message_id):
    global message_reactions
    # Combine reaction counts for both messages
    user_emoji_counts = message_reactions.get(str(user_message_id), {})
    bot_emoji_counts = message_reactions.get(str(bot_message_id), {})

    # Create a combined emoji count dictionary
    combined_emoji_counts = {}
    for emoji, count in user_emoji_counts.items():
        combined_emoji_counts[emoji] = combined_emoji_counts.get(emoji, 0) + count

    for emoji, count in bot_emoji_counts.items():
        combined_emoji_counts[emoji] = combined_emoji_counts.get(emoji, 0) + count

    # Create a string representation of emoji counts
    emoji_count_str = " ".join([f"{count}-{emoji}" for emoji, count in combined_emoji_counts.items() if count > 1])

    # Update the content of reacted_message with the combined emoji counts
    if combined_emoji_counts:
        try:
            bot_message = await reaction_channel.fetch_message(bot_message_id)
            user_message = await target_channel.fetch_message(user_message_id)
            channel = reaction_channel
        except discord.errors.NotFound:
            bot_message = await target_channel.fetch_message(bot_message_id)
            user_message = await reaction_channel.fetch_message(user_message_id)
            channel = target_channel
        if bot_message and user_message:
            paired_webhook_url = channel_pairs[str(channel.id)]["webhook_url"]
            webhook = discord.Webhook.from_url(paired_webhook_url, client=bot)
            if emoji_count_str:
                new_content = f"{user_message.content.split('(')[0].strip()} ({emoji_count_str})"
            else:
                new_content = user_message.content  # Use the original content if emoji_count_str is empty
            await webhook.edit_message(
                int(bot_message_id),
                content=new_content,
            )

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN, reconnect=True)