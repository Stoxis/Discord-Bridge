Introducing the **Discord Bridge Bot** – Your Ultimate Channel Pairing Companion

# **Discord Bridge Bot**

The Discord Bridge Bot is a versatile and user-friendly Python bot that streamlines the process of mirroring messages and reactions between two Discord text channels. Whether you're looking to keep multiple channels synchronized for important announcements, collaboration, or any other purpose, this bot simplifies the task, enhancing your server's communication and organization.

With the Discord Channel Bridge Bot, you can effortlessly pair and manage text channels within your server. This utility bot provides an intuitive way to establish channel connections, ensuring that messages sent in one channel are automatically mirrored in the other. It's the perfect solution for maintaining cohesion within your server, whether you need to keep public channels in sync or create discreet communication bridges for specific purposes.

**Features:**

-   **Channel Pairing:** Easily pair two Discord text channels from the same or different servers, allowing messages to be mirrored between them.

-   **Channel Unpairing:** Easily unpair previously linked channels to discontinue message mirroring, the webhooks used by the bot will be automatically deleted.
    
-   **Reaction Mirroring:** Mirror reactions added or removed from messages in one channel to the paired channel, ensuring both channels have consistent reactions.
    
-   **Message Deletion Handling:** When a message is deleted in one channel, the bot automatically removes its mirrored counterpart in the paired channel.
    
-   **Simple Commands:** The bot provides a simple and intuitive set of commands, including `^pair`, `^unpair`, `^list`, and `^help`.
    
-   **Customizable Webhooks:** Webhooks are used for mirroring messages, and the bot automatically creates them as needed.
    

**Getting Started:**

To get started with the Discord Bridge Bot, invite it to your server(s) and ensure that it has the required permissions. Use the `^pair` command to establish channel pairs, and `^list` to view your paired channels. Refer to `^help` for a full list of available commands.
    

**Requirements:**

-   discord.py library
-   aiohttp library

**Installation and Usage:**

Clone this repository, run `pip install requirements.txt`, set up your bot token, and run the bot.

**Acknowledgments:**

We would like to thank the Discord community and developers for their support and contributions to the project. Your feedback and suggestions help make this bot even better!

**Contributing:**

Contributions and feature requests are welcome! Feel free to submit issues or pull requests to help improve the Discord Channel Mirror Bot.

**License:**

This project is licensed under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).
