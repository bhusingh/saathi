# Discord setup

Create the Discord server in the Discord app before creating/inviting the bot. In the Developer Portal choose
a bot or blank application; template wording such as “what are you building?” does not change the setup.
Turn Public Bot off and enable Message Content Intent. Invite only View Channels, Send Messages, Read Message
History, Embed Links, Attach Files, and temporary Manage Channels. Never grant Administrator, Manage Server,
or Manage Roles, and never use a self-bot.

`saathi discord setup` reads the bot token and guild ID from the environment. Its first run discovers the
guild owner and fails until that numeric ID is present in `DISCORD_ALLOWED_USERS`. There is no Discord pairing
code in Hermes. Blank comma-separated entries are ignored, and an empty allowlist is rejected. On the second
run it creates configured channels and a DM, then stores channel IDs under the gitignored state directory.
Remove Manage Channels afterward and set the resulting home channel in Hermes if needed. Interactive chat
retains Hermes' configured tools, so do not add anyone except the trusted owner to the allowlist.

If Copy User ID is missing, enable Developer Mode. The bot application ID or username is not your user ID;
copy the numeric user ID or use Discord's `\@username` display trick. A bot online but ignoring DMs normally
means Message Content Intent is off or the user allowlist is missing. “No home channel is set” means
`DISCORD_HOME_CHANNEL` must be set. A voice “Opus codec not found” warning is harmless for text-only use.
