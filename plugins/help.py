from command import command


@command("help", "h")
def help_command(bot, sender_jid, nick, args, msg, is_room):
    """
    Show available commands or detailed help for a specific command.

    Usage
    -----
    {prefix}help
    {prefix}help command

    Without arguments:
        Lists all available commands grouped by function. Command aliases
        appear on one line together. Each line contains the command names
        with the configured prefix and the first line of the command's
        docstring.

        Admin-only commands are marked with "(admin)" and are only visible
        to bot administrators.

    With a command name as argument:
        Displays the full docstring of the specified command.

    Notes
    -----
    The command name provided as an argument must NOT include the prefix.
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    prefix = bot.prefix
    is_admin = bot.is_admin(sender_jid)

    # -------------------------------------------------
    # HELP FOR A SPECIFIC COMMAND
    # -------------------------------------------------

    if args:

        name = args[0]

        if name not in bot.commands:
            bot.send_message(
                mto=target,
                mbody=f"Unknown command: {name}",
                mtype=mtype
            )
            return

        func = bot.commands[name]

        if getattr(func, "owner_only", False) and not is_admin:
            bot.send_message(
                mto=target,
                mbody=f"Unknown command: {name}",
                mtype=mtype
            )
            return

        doc = func.__doc__ or "No help available."
        doc = doc.strip().replace("{prefix}", prefix)

        bot.send_message(
            mto=target,
            mbody=doc,
            mtype=mtype
        )

        return

    # -------------------------------------------------
    # GENERAL HELP (LIST COMMANDS)
    # -------------------------------------------------

    grouped = {}

    for name, func in bot.commands.items():

        if getattr(func, "owner_only", False) and not is_admin:
            continue

        grouped.setdefault(func, func._command_names)

    sorted_commands = sorted(
        grouped.items(),
        key=lambda item: item[0]._command_names[0]
    )

    lines = []

    for func, names in sorted_commands:

        aliases = ", ".join(f"{prefix}{n}" for n in names)

        doc = func.__doc__ or ""
        first_line = doc.strip().split("\n")[0] if doc else ""
        first_line = first_line.replace("{prefix}", prefix)

        admin_marker = ""
        if getattr(func, "owner_only", False):
            admin_marker = " (✅ admin)"

        if first_line:
            line = f"{aliases} — {first_line}{admin_marker}"
        else:
            line = f"{aliases} - {admin_marker}"

        lines.append(line)

    response = "Available commands:\n" + "\n".join(lines)

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
