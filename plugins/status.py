"""
Bot presence and status management.

This plugin allows moderators to change the bot's XMPP presence
(online, away, do-not-disturb, etc.) and lets users view the
current presence state and status message.
"""

import logging
from utils.command import command, Role

log = logging.getLogger(__name__)

PLUGIN_META = {
    "name": "status",
    "version": "0.1.0",
    "description": "Bot presence and status management",
    "category": "info",
}


@command("status")
async def show_status(bot, sender_jid, nick, args, msg, is_room):
    """
    Display the current bot presence and status message.

    Command
    -------
    {prefix}status

    Description
    -----------
    Shows the bot's current presence state. The following states are supported:
    - online
        Normal online status
    - chat
        If you're available for chatting or searching for for talking.
    - away
        Away status indicator for 'Away From Keyboard' events.
    - xa
        'Extended Away': For longer periods of being away, like sleeping.
    - dnd
        'Do Not Disturb': If you don't want to be contacted at the moment

    And the optional status message that is broadcast to contacts
    and chatrooms.

    Example
    -------
    {prefix}status
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    show = bot.presence.status["show"]
    message = bot.presence.status["status"]

    emoji = bot.presence.emoji(show)

    if message:
        text = f"Current status {emoji} ({show}) {message}"
    else:
        text = f"Current status {emoji} ({show})"

    bot.reply(
        msg,
        text,
    )


@command("status set", role=Role.MODERATOR)
async def status_set(bot, sender_jid, nick, args, msg, is_room):
    """
    Change the bot presence and optional status message.

    Command
    -------
    {prefix}status set <show> [message]

    Description
    -----------
    Updates the presence state broadcast by the bot. Moderators
    can use this command to indicate availability or activity.

    Valid Presence States
    ---------------------
    online
    -   Default available presence.
    chat
    -   Actively available for conversation.
    away
    -   Temporarily away from the keyboard.
    xa
    -   Extended away.
    dnd
    -   Do not disturb.

    Parameters
    ----------
    show
    -   The presence state to set.
    message (optional)
    -   Additional human-readable status text.

    Examples
    --------
    {prefix}status set away
    {prefix}status set away Out for lunch
    {prefix}status set dnd Busy working
    """

    if len(args) < 1:
        bot.reply(
            msg,
            f"Usage: {bot.prefix}status set <show> [message]",
        )
        return

    show = args[0].lower()
    message = " ".join(args[1:]) if len(args) > 1 else ""

    valid_states = {"online", "chat", "away", "xa", "dnd"}

    if show not in valid_states:
        bot.reply(
            msg,
            "Invalid status. Valid values: online, chat, away, xa, dnd",
        )
        return

    bot.presence.update(show, message)

    emoji = bot.presence.emoji(show)

    if message:
        response = f"Status updated {emoji} ({show}) {message}"
    else:
        response = f"Status updated {emoji} ({show})"

    bot.reply(
        msg,
        response,
    )

    log.info(f"[STATUS] {response}")
