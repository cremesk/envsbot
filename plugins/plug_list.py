"""
Plugins Plugin

Provides commands to list currently loaded plugins and plugins that are
available but not loaded.

Commands
--------
plugins
    Show loaded and available plugins.
"""

import logging
from command import command

log = logging.getLogger(__name__)


PLUGIN_META = {
    "name": "plugins",
    "version": "1.0",
    "description": "List loaded and available plugins"
}


@command("plugins", owner_only=True)
async def list_plugins(bot, sender, nick, args, msg, is_room):
    """
    List all loaded plugins and available plugins.

    Usage
    -----
    {prefix}plugins

    Examples
    --------
    {prefix}plugins
    """

    log.info("[PLUGIN] Plugin list requested by %s", sender)

    loaded = sorted(bot.plugins.plugins.keys())
    discovered = sorted(bot.plugins.discover())

    not_loaded = sorted(set(discovered) - set(loaded))

    lines = []

    # Loaded plugins
    if loaded:
        lines.append("Loaded plugins:")
        lines.append(", ".join(loaded))
    else:
        lines.append("Loaded plugins: none")

    # Available but not loaded
    if not_loaded:
        lines.append("")
        lines.append("Available plugins:")
        lines.append(", ".join(not_loaded))

    bot.reply(msg, lines)
