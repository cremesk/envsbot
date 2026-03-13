"""
Help plugin.

Plugin help:
  ,help <plugin>

Command help:
  ,help ,command
"""

from command import command, resolve_command


PLUGIN_META = {
    "name": "help",
    "version": "1.1",
    "description": "Show help for plugins and commands.",
    "category": "core",
}


def _first_line(doc):
    if not doc:
        return ""
    return doc.strip().split("\n")[0]


def _clean_doc(doc, prefix):
    if not doc:
        return ""

    lines = []
    for line in doc.strip().splitlines():
        line = line.replace("{prefix}", prefix)
        lines.append(line.strip())

    return "\n".join(lines)


def _commands_for_plugin(bot, plugin_name):
    cmds = []

    for cmd, owner in bot.plugins.command_owner.items():
        if owner == plugin_name:
            fn = bot.commands.get(cmd)
            if not fn:
                continue

            doc = _first_line(fn.__doc__)
            cmds.append((cmd, doc))

    return sorted(cmds)


def _extract_query(msg, prefix):
    """
    Extract raw text after ',help' from the message.

    This avoids command token normalization.
    """

    body = msg["body"].strip()

    if not body.startswith(prefix):
        return ""

    body = body[len(prefix):].strip()

    if not body.lower().startswith("help"):
        return ""

    body = body[4:].strip()

    return body


@command("help", aliases=["h"])
async def cmd_help(bot, sender_jid, nick, args, msg, is_room):
    """
    Show help.

    Usage:
      {prefix}help
      {prefix}help <plugin>
      {prefix}help {prefix}<command>
    """

    prefix = bot.config.get("prefix", ",")
    pm = bot.plugins
    lines = []

    query = _extract_query(msg, prefix)

    # --------------------------------------------------
    # GENERAL HELP
    # --------------------------------------------------

    if not query:
        lines.append("📦 Available plugins:")
        lines.append("")

        for name, module in sorted(pm.plugins.items()):
            doc = _first_line(module.__doc__)
            lines.append(f"• {name} — {doc}")

        lines.append("")
        lines.append(f"Use {prefix}help <plugin> for plugin help.")
        lines.append(
            f"Use {prefix}help {prefix}<command> for command help."
        )

        bot.reply(msg, "\n".join(lines))
        return

    # --------------------------------------------------
    # COMMAND HELP
    # --------------------------------------------------

    if query.startswith(prefix):
        cmd_text = query[len(prefix):].strip()

        cmd_obj, _ = resolve_command(cmd_text)

        if not cmd_obj:
            bot.reply(msg, f"⚠️ Unknown command: {query}")
            return

        fn = cmd_obj.handler
        doc = _clean_doc(fn.__doc__, prefix)

        lines.append(f"📖 Command: {prefix}{cmd_obj.name}")
        lines.append("")

        if doc:
            lines.append(doc)

        bot.reply(msg, "\n".join(lines))
        return

    # --------------------------------------------------
    # PLUGIN HELP
    # --------------------------------------------------

    plugin = query.lower()

    if plugin not in pm.plugins:
        bot.reply(msg, f"⚠️ Unknown plugin: {query}")
        return

    module = pm.plugins[plugin]

    lines.append(f"📦 Plugin: {plugin}")
    lines.append("")

    module_doc = _clean_doc(module.__doc__, prefix)

    if module_doc:
        lines.append(module_doc)
        lines.append("")

    cmds = _commands_for_plugin(bot, plugin)

    if cmds:
        lines.append("Commands:")
        for name, doc in cmds:
            lines.append(f"  {prefix}{name} — {doc}")

    bot.reply(msg, "\n".join(lines))
