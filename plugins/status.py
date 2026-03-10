"""
Presence and status management plugin.

This plugin provides commands for displaying and modifying the
bot's XMPP presence state. The bot presence is broadcast to
contacts and chatrooms and can include both a presence type
(e.g. away or do-not-disturb) and a human-readable status message.

Admins can change the status dynamically without restarting
the bot.
"""

from command import command

PLUGIN_META = {
    "name": "status",
    "version": "1.0",
    "description": "Bot presence and status management"
}


@command("status set", admins_only=True)
async def status_set(bot, sender_jid, nick, args, msg, is_room):
    """
    Set the bot presence status.

    Command
    -------
    {prefix}status set <show> [message]

    Parameters
    ----------
    show
        Presence type. Supported values:
        - online
            Available / default presence.
        - chat
            Actively available for conversation.
        - away
            Temporarily away.
        - xa
            Extended away.
        - dnd
            Do not disturb.
    
    message (optional)
        Status text displayed alongside the presence.
    
    Examples
    --------
    {prefix}status set away
    {prefix}status set away Out for lunch
    {prefix}status set dnd Busy working
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    if len(args) < 1:

        bot.send_message(
            mto=target,
            mbody=f"Usage: {bot.prefix}setstatus <show> [message]",
            mtype=mtype
        )
        return

    show = args[0].lower()
    message = " ".join(args[1:]) if len(args) > 1 else ""

    valid_states = {"online", "chat", "away", "xa", "dnd"}

    if show not in valid_states:

        bot.send_message(
            mto=target,
            mbody="Invalid status. Valid values: online, chat, away, xa, dnd",
            mtype=mtype
        )
        return

    bot.presence.update(show, message)

    emoji = bot.presence.emoji(show)

    if message:
        response = f"Status updated {emoji} ({show}) {message}"
    else:
        response = f"Status updated {emoji} ({show})"

    bot.send_message(
        mto=target,
        mbody=response,
        mtype=mtype
    )


@command("status", "s")
async def show_status(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the current bot status and message.

    Command
    -------
    {prefix}status

    Displays the presence state and optional status message
    currently broadcast by the bot.

    Example
    -------
    {prefix}status
    """
    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    show = bot.presence.status["show"]
    message = bot.presence.status["status"]

    emoji = bot.presence.emoji(show)

    bot.send_message(
        mto=target,
        mbody=f"Current status {emoji} ({show}) {message}",
        mtype=mtype
    )
