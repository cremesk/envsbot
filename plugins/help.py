"""
📚 Help system for the bot.

This plugin provides dynamic help for:
• Plugins
• Commands
• Multi-word commands

Usage
-----
General help:
  {prefix}help
Plugin help:
  {prefix}help <plugin>
Command help:
  {prefix}help {prefix}<command>

Examples:
  {prefix}help rooms
  {prefix}help {prefix}join
  {prefix}help {prefix}status set

Notes
-----
• Help is only available via private chat to prevent spam.
• Commands are filtered by user role.
• Plugins always display their full docstring.
• Command help displays the full command docstring.
"""

import logging

from utils.command import command, resolve_command, check_permission, Role
from utils.config import config

log = logging.getLogger(__name__)

PLUGIN_META = {
    "name": "help",
    "version": "2.0",
    "description": "Dynamic help for plugins and commands.",
    "category": "core",
}


# --------------------------------------------------
# DOCSTRING HELPERS
# --------------------------------------------------

def _first_line(doc):
    if not doc:
        return ""
    return doc.strip().splitlines()[0]


def _clean_doc(doc, prefix):
    if not doc:
        return ""

    lines = []

    for line in doc.strip().splitlines():
        lines.append(line.replace("{prefix}", prefix).rstrip())

    return "\n".join(lines)


# --------------------------------------------------
# QUERY EXTRACTION
# --------------------------------------------------

def _extract_query(msg, prefix):
    """
    Extract raw help query from message body.

    This avoids command token normalization so that
    multi-word commands like "status set" work correctly.
    """

    body = msg["body"].strip()

    if not body.startswith(prefix):
        return ""

    body = body[len(prefix):].strip()

    if not body.lower().startswith("help"):
        return ""

    return body[4:].strip()


# --------------------------------------------------
# COMMAND DISCOVERY
# --------------------------------------------------

def _commands_for_plugin(bot, plugin_name, user_role):
    """
    Dynamically collect commands belonging to a plugin.

    This is hot-reload safe because it reads the live
    command registry every time.
    """

    seen = set()
    commands = []

    for name, owner in bot.plugins.command_owner.items():

        if owner != plugin_name:
            continue

        cmd_obj, _ = resolve_command(name)

        if not cmd_obj:
            continue

        # avoid duplicates caused by aliases
        if cmd_obj.name in seen:
            continue

        seen.add(cmd_obj.name)

        if not check_permission(user_role, cmd_obj):
            continue

        commands.append(cmd_obj)

    commands.sort(key=lambda c: c.name)

    return commands


# --------------------------------------------------
# COMMAND FORMATTER
# --------------------------------------------------

def _format_command(cmd_obj, prefix):
    """
    Format command entry for plugin help.
    """

    name = cmd_obj.name
    role = str(cmd_obj.role)
    aliases = cmd_obj.aliases or []

    desc = _first_line(cmd_obj.handler.__doc__)

    alias_text = f" ({', '.join(prefix + a
                                for a in aliases)})" if aliases else ""

    return f"{prefix}{name}{alias_text} [{role}] - {desc}"


# --------------------------------------------------
# HELP COMMAND
# --------------------------------------------------

@command("help", aliases=["h"])
async def cmd_help(bot, sender_jid, nick, args, msg, is_room):
    """
    Show help.

    Usage:
      {prefix}help
      {prefix}help <plugin>
      {prefix}help {prefix}<command>
    """

    prefix = config.get("prefix", ",")

    if is_room:
        bot.reply(msg, "ℹ️ Help is only available via private message.")
        return

    query = " ".join(args).strip()

    user_role = await bot.get_user_role(sender_jid)

    pm = bot.plugins

    # --------------------------------------------------
    # GENERAL HELP
    # --------------------------------------------------

    if not query:

        lines = ["📦 Available plugins", ""]

        for name, module in sorted(pm.plugins.items()):

            # hide internal plugins for non-admin users
            if name.startswith("_") and user_role > Role.ADMIN:
                continue

            doc = _first_line(module.__doc__)
            lines.append(f"• {name} — {doc}")

        lines.append("")
        lines.append(f"Use {prefix}help <plugin> for plugin help.")
        lines.append(f"Use {prefix}help {prefix}<command> for command help.")

        bot.reply(msg, lines)
        return

    # --------------------------------------------------
    # COMMAND HELP
    # --------------------------------------------------

    if query.startswith(prefix):

        cmd_text = query[len(prefix):].strip()

        cmd_obj, _ = resolve_command(cmd_text)

        if not cmd_obj:
            bot.reply(msg, "⚠️ Unknown command.")
            return

        if not check_permission(user_role, cmd_obj):
            bot.reply(msg, "⛔ You do not have permission to use this command.")
            return

        doc = _clean_doc(cmd_obj.handler.__doc__, prefix)

        lines = [
            f"📖 Command: {prefix}{cmd_obj.name}",
            ""
        ]

        if doc:
            lines.append(doc)

        bot.reply(msg, lines)
        return

    # --------------------------------------------------
    # PLUGIN HELP
    # --------------------------------------------------

    plugin = query.lower()

    # hide internal plugins for non-admin users
    if plugin.startswith("_") and user_role > Role.ADMIN:
        bot.reply(msg, "⚠️ Unknown plugin.")
        return

    if plugin not in pm.plugins:
        bot.reply(msg, "⚠️ Unknown plugin.")
        return

    module = pm.plugins[plugin]

    lines = [
        f"📦 Plugin: {plugin}",
        ""
    ]

    module_doc = _clean_doc(module.__doc__, prefix)

    if module_doc:
        lines.append(module_doc)
        lines.append("")

    lines.append("Commands:")

    commands = _commands_for_plugin(bot, plugin, user_role)

    if not commands:
        lines.append("No commands available for your role.")
    else:
        for cmd in commands:
            lines.append(_format_command(cmd, prefix))

    bot.reply(msg, lines)
