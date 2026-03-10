"""
Load Plugin

Provides commands to load bot plugins at runtime without restarting
the bot.

Commands
--------
load <plugin>
    Load a specific plugin.

load all
    Load all available plugins that are not currently loaded.

Notes
-----
Only bot owners/admins can use this command.
"""

import logging
from command import command

log = logging.getLogger(__name__)


PLUGIN_META = {
    "name": "load",
    "version": "1.0",
    "description": "Load plugins at runtime"
}


@command("load", owner_only=True)
async def load_plugin(bot, sender, nick, args, msg, is_room):
    """
    Load one plugin or all available plugins.

    Usage
    -----
    {prefix}load <plugin>
        Load a specific plugin.

    {prefix}load all
        Load all available plugins that are not currently loaded.

    Examples
    --------
    {prefix}load help
    {prefix}load status
    {prefix}load all
    """

    if not args:
        bot.reply(msg, f"Usage: {bot.prefix}load <plugin|all>")
        return

    target = args[0].lower()

    log.info("[PLUGIN] Load command requested by %s: %s", sender, target)

    # Load ALL plugins
    if target == "all":
        discovered = set(bot.plugins.discover())
        loaded = set(bot.plugins.plugins.keys())
        to_load = sorted(discovered - loaded)
        if not to_load:
            bot.reply(msg, "All plugins are already loaded.")
            return
        success = []
        failed = []

        for name in to_load:
            try:
                log.info("[PLUGIN] Loading plugin: %s", name)
                bot.plugins.load(name)
                success.append(name)
            except Exception as e:
                log.exception("[PLUGIN] ❌Failed to load plugin: %s", name)
                failed.append(f"{name} ({e})")

        message = []
        if success:
            message.append("Loaded: " + ", ".join(success))
        if failed:
            message.append("Failed: " + ", ".join(failed))
        bot.reply(msg, "\n".join(message))
        log.info(f"[PLUGIN] {"\n".join(message)}")
        return

    # Load ONE plugin
    plugin = target

    if plugin in bot.plugins.plugins:
        bot.reply(msg, f"Plugin '{plugin}' is already loaded.")
        log.warning("[PLUGIN] ⚠ Plugin already loaded: %s", plugin)
        return

    try:
        log.info("Loading plugin: %s", plugin)
        bot.plugins.load(plugin)
        bot.reply(msg, f"Plugin '{plugin}' loaded.")
    except Exception as e:
        log.exception("[PLUGIN] ❌Failed to load plugin: %s", plugin)
        bot.reply(msg, f"❌Load failed: {e}")
