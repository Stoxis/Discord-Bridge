**Discord Bridge Bot**

The Discord Bridge Bot is a versatile and easy-to-use Python bot designed to help you mirror messages and reactions between two Discord text channels. Whether you want to keep multiple channels in sync for announcements, collaborations, or any other purpose, this bot simplifies the process for you.

**Features:**

-   **Channel Pairing:** Easily pair two Discord text channels from the same or different servers, allowing messages to be mirrored between them.
    
-   **Reaction Mirroring:** Mirror reactions added or removed from messages in one channel to the paired channel, ensuring both channels have consistent reactions.
    
-   **Message Deletion Handling:** When a message is deleted in one channel, the bot automatically removes its mirrored counterpart in the paired channel.
    
-   **Simple Commands:** The bot offers simple and intuitive commands to pair and unpair channels, list paired channels, and more.
    
-   **Customizable Webhooks:** Webhooks are used for mirroring messages, and the bot automatically creates them as needed.
    

**Getting Started:**

1.  Invite the Discord Channel Mirror Bot to your server.
    
2.  Use the `^pair` command to pair the channels you want to mirror.
    
3.  Enjoy seamless message and reaction mirroring between the paired channels.
    

**Requirements:**

-   discord.py library
-   aiohttp library

**Installation and Usage:**

Clone this repository, run `pip install requirements.txt`, set up your bot token, and run the bot.

**Contributing:**

Contributions and feature requests are welcome! Feel free to submit issues or pull requests to help improve the Discord Channel Mirror Bot.

**License:**

This project is licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).
