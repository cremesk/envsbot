from command import command


@command("status", "s")
async def show_status(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the current bot status.

    Usage
    -----
    {prefix}status

    Displays the presence state and status message
    currently broadcast by the bot.
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


def register(bot):
    """
    Plugin registration hook.

    Commands are registered automatically via the decorator
    system in bot.py.
    """
    pass
