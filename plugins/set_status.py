from command import command


@command("setstatus", "ss", owner_only=True)
async def set_status(bot, sender_jid, nick, args, msg, is_room):
    """
    Set the bot presence status.

    Usage
    -----
    {prefix}setstatus <show> [message]

    Parameters
    ----------
    show
        Presence type. Supported values:
        online, chat, away, xa, dnd

    message (optional)
        Status text displayed by the bot.

    Examples
    --------
    {prefix}setstatus away
    {prefix}setstatus away Out for lunch
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    if len(args) < 1:

        bot.send_message(
            mto=target,
            mbody="Usage: {prefix}setstatus <show> [message]".replace(
                "{prefix}", bot.prefix
            ),
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


def register(bot):
    """
    Plugin registration hook.

    Commands are registered automatically via the decorator
    system implemented in bot.py.
    """
    pass
