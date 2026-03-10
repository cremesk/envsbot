"""
Unload Plugin

Provides a command to unload bot plugins at runtime without restarting
the bot.

Commands
--------
unload <plugin>
    Unload a currently loaded plugin.

Notes
-----
Only bot owners/admins can use this command.
Unloading a plugin removes all commands registered by that plugin.
"""

import logging
from command import command


PLUGIN_META = {
    "name": "unload",
    "version": "1.0",
    "description": "Unload plugins without restarting the bot"
}

logger = logging.getLogger(__name__)


@command("unload", owner_only=True)
async def unload_plugin(bot, sender, nick, args, msg, is_room):
    """
    Unload a plugin.

    Usage
    -----
    {prefix}unload <plugin>
        Unload a specific plugin.

    Examples
    --------
    {prefix}unload help
    {prefix}unload status
    """

    if not args:
        bot.reply(msg, f"Usage: {bot.prefix}unload <plugin>")
        return

    plugin = args[0].lower()

    logger.info("[PLUGIN] Unload command requested by %s: %s", sender, plugin)

    # Prevent unloading itself (recommended)
    if plugin == "unload":
        bot.reply(msg, "The unload plugin cannot unload itself.")
        logger.warning("[PLUGIN] ⚠ Attempt to unload unload plugin blocked.")
        return

    if plugin not in bot.plugins.plugins:
        available = ", ".join(sorted(bot.plugins.plugins.keys()))
        bot.reply(msg, f"Plugin '{plugin}' not found. Available: {available}")
        logger.warning("[PLUGIN] ⚠ Unload requested for unknown plugin: %s", plugin)
        return

    try:
        logger.info("[PLUGIN] Unloading plugin: %s", plugin)
        bot.plugins.unload(plugin)
        bot.reply(msg, f"Plugin '{plugin}' unloaded.")

    except Exception as e:
        logger.exception("[PLUGIN] ❌Failed to unload plugin: %s", plugin)
        bot.reply(msg, f"❌Unload '{plugin}' failed: {e}")
