import traceback  
import discord
from discord.ext import commands
import json
import aiohttp

# Bot token and prefix
TOKEN = 'Token_here'
PREFIX = '^'

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Custom channel converter to handle errors
class CustomTextChannel(commands.TextChannelConverter):
    async def convert(self, ctx, argument):
        try:
            channel = await super().convert(ctx, argument)
            await channel.guild.fetch_channel(channel.id)  # Try to fetch the channel
            return channel
        except (commands.ChannelNotFound, discord.NotFound):
            raise commands.BadArgument(f'I\'m unable to access the channel {argument}.')

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
    with open('channel_pairs.json', 'w') as file:
        json.dump(channel_pairs, file, indent=4)
	# If you don't load_channel_pairs() after saving the new pair the new pair isn't recognized until the bot is restarted and the new pair is loaded.
    load_channel_pairs()

# Event listener for bot ready event
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    load_channel_pairs()
    print(channel_pairs)

# Command to pair two channels
@bot.command()
async def pair(ctx, channel1, channel2):
    global channel_pairs
    print(bot.activity)

    try:
        # Try to fetch both channels
        channel1 = await bot.fetch_channel(channel1)
        channel2 = await bot.fetch_channel(channel2)
    except:
        await ctx.send(f':negative_squared_cross_mark: I\'m unable to access one or both of the specified channels.')
        return

    # Check if the bot has permission to create webhooks in both guilds
    if (
        not ctx.guild.me.guild_permissions.manage_webhooks
        or not channel1.guild.me.guild_permissions.manage_webhooks
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
async def unpair(ctx, channel1: discord.TextChannel, channel2: discord.TextChannel):
    global channel_pairs

    # Check if the pair exists
    if channel1.id not in channel_pairs or channel2.id not in channel_pairs:
        await ctx.send(':negative_squared_cross_mark: This pair doesn\'t exist!')
        return

    # Delete the webhooks
    await discord.Webhook.from_url(channel_pairs[channel1.id][0], session=bot.http._HTTPClient__session).delete()
    await discord.Webhook.from_url(channel_pairs[channel2.id][0], session=bot.http._HTTPClient__session).delete()

    # Remove the pair from the dictionary
    del channel_pairs[channel1.id]
    del channel_pairs[channel2.id]
    save_channel_pairs()

    await ctx.send(':white_check_mark: Webhook pair destroyed!')

# Command to list channel pairs
@bot.command()
async def list(ctx):
    pair_list = "\n".join([f'<#{ch1}>:<#{ch2}>' for ch1, (_, ch2) in channel_pairs.items()])
    await ctx.send(pair_list)

# Help command
@bot.command()
async def help(ctx):
    help_message = '''
    **Available Commands:**
    `^pair <channel1> <channel2>` - Pair two channels
    `^unpair <channel1> <channel2>` - Unpair two channels
    `^list` - List paired channels
    `^help` - Show this message
    '''
    await ctx.send(help_message)

# Event to handle message copying
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Find the paired channel for the current channel
    paired_channel_id = None
    for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if message.channel.id == int(channel_id):
            paired_channel_id = paired_id
            break

    if paired_channel_id:
        webhook_url, _ = channel_pairs[str(paired_channel_id)]
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json={
                "content": message.content,
                "username": message.author.display_name,
                "avatar_url": message.author.display_avatar.url,
                # You can add other parameters like embeds if needed
            }) as response:
                if response.status != 204:
                    print(f"Failed to send message: {response.status}")

    await bot.process_commands(message)

# Event listener for raw message deletion events
@bot.event
async def on_raw_message_delete(payload):
    # Get the channel ID and message ID from the payload
    channel_id1 = payload.channel_id
    message_id = payload.message_id

    # Log the channel ID and message ID of the deleted message
    print(f"Message deleted in channel {channel_id1}: {message_id}")

    # Find the paired channel for the current channel
    paired_channel_id = None
    for channel_id, (webhook_url, paired_id) in channel_pairs.items():
        if payload.channel_id == int(channel_id):
            paired_channel_id = paired_id
            break
	
    # Check if the channel ID is in the paired channels dictionary
    if paired_channel_id is not None:
        # Get the target channel
        target_channel = bot.get_channel(paired_channel_id)

        if target_channel:
            print(f"Message deleted in paired channel: {message_id}")

            # Fetch the mirrored message from the target channel's webhook
            async for msg in target_channel.history(limit=100):  # Adjust the limit as needed
                if (payload.cached_message.author.global_name == None):
                    payloadUsername = payload.cached_message.author.name
                else:
                    payloadUsername = payload.cached_message.author.global_name
                #print(msg)
                if (msg.author.global_name == None):
                    targetUsername = msg.author.name
                else:
                    targetUsername = msg.author.global_name
                #print(payload)
                #print('author: ' + targetUsername + '\nContent: ' + msg.content)
                #print('authorcompare: ' + payloadUsername + '\nContentcompare: ' + payload.cached_message.content)
                if (
                    msg.content == payload.cached_message.content
                    and targetUsername == payloadUsername
                ):
                    await msg.delete()
                    print(f"Mirrored message removed from target channel: {message_id}")
                    break
            else:
                print("No mirrored message found in target channel history")
        else:
            print("Target channel not found")
    else:
        print("Message not in a paired channel")

@bot.event
async def on_raw_reaction_add(payload):
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
					
                    # Check if reaction wasn't added by self
                    if payload.member.id != bot.user.id:
                        if msg.content == reactMsg.content:
                            real_message = msg
                            break
					
                    if msg.content == reactMsg.content:
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

                    # Check if reaction wasn't added by self
                    if payload.user_id != bot.user.id:
                        if msg.content == reactMsg.content:
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