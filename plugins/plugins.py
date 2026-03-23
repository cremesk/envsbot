"""
Plugin management commands.

This plugin exposes administrative commands for managing plugins at runtime,
like loading, unloading, reloading and listing plugins.

All commands rely on the async PluginManager API.
"""

import logging
from utils.command import command, Role

log = logging.getLogger(__name__)


PLUGIN_META = {
    "name": "plugins",
    "version": "0.1.0",
    "description": "Runtime plugin management",
    "category": "core",
}


@command("plugin list", role=Role.ADMIN, aliases=["plugins list"])
async def plugin_list(bot, sender, nick, args, msg, is_room):
    """
    List all plugins grouped by category.

    Shows both loaded and available (not loaded) plugins.

    Usage:
        {prefilx}plugins list
    """
    categories = await bot.plugins.list_detailed()

    lines = ["Plugin status"]

    for category in sorted(categories):
        block = categories[category]

        lines.append("")
        lines.append(f"[{category.upper()}]")

        for name in sorted(block["loaded"]):
            lines.append(f"  [loaded] {name}")

        for name in sorted(block["available"]):
            lines.append(f"  [not loaded] {name}")

    bot.reply(msg, "\n".join(lines))


@command("plugin info", role=Role.ADMIN, aliases=["plugins info"])
async def plugin_info(bot, sender, nick, args, msg, is_room):
    """
    Shows metadata of a plugin, like name, version, description and requires.

    Usage:
        {prefix}plugin info <plugin>
    """
    if not args:
        bot.reply(msg, "Usage: plugin info <plugin>")
        return

    name = args[0].lower()
    meta = await bot.plugins.get_plugin_info(name)

    if not meta:
        bot.reply(msg, f"Plugin '{name}' not found.")
        return

    lines = [
        f"Plugin: {meta.get('name', name)}",
        f"Version: {meta.get('version', 'unknown')}",
        f"Category: {meta.get('category', 'other')}",
        f"Description: {meta.get('description', 'no description')}",
    ]

    if meta.get("requires"):
        lines.append("Requires: " + ", ".join(meta["requires"]))

    bot.reply(msg, "\n".join(lines))


@command("plugin load", role=Role.ADMIN, aliases=["plugins load"])
async def plugin_load(bot, sender, nick, args, msg, is_room):
    """
    Load a plugin or all plugins. Only if it's not already loaded.

    Usage:
        {prefix}plugin load <plugin>
        {prefix}plugin load all
    """
    if not args:
        bot.reply(msg, "Usage: plugin load <plugin|all>")
        return

    target = args[0].lower()

    if target == "all":
        for name in bot.plugins.available():
            await bot.plugins.load(name)
        bot.reply(msg, "All plugins loaded.")
        return

    await bot.plugins.load(target)
    bot.reply(msg, f"Plugin '{target}' loaded.")


@command("plugin unload", role=Role.ADMIN, aliases=["plugins unload"])
async def plugin_unload(bot, sender, nick, args, msg, is_room):
    """
    Unload a plugin.

    Usage:
        {prefix}plugin unload <plugin>
    """
    if not args:
        bot.reply(msg, "Usage: plugin unload <plugin>")
        return

    name = args[0].lower()

    if name == "plugins":
        bot.reply(msg, "Cannot unload plugin manager.")
        return

    success = await bot.plugins.unload(name)

    if success:
        bot.reply(msg, f"Plugin '{name}' unloaded.")
    else:
        bot.reply(msg, f"Plugin '{name}' is not loaded.")


@command("plugin reload", role=Role.ADMIN, aliases=["plugins reload"])
async def plugin_reload(bot, sender, nick, args, msg, is_room):
    """
    Reload a plugin or all plugins, that are currently loaded.

    Usage:
        {prefix}plugin reload <plugin>
        {prefix}plugin reload all
    """
    if not args:
        bot.reply(msg, "Usage: plugin reload <plugin|all>")
        return

    target = args[0].lower()

    if target == "all":
        for name in bot.plugins.list():
            if name != "plugins":
                await bot.plugins.reload(name)

        await bot.plugins.reload("plugins")
        bot.reply(msg, "All plugins reloaded.")
        return

    await bot.plugins.reload(target)
    bot.reply(msg, f"Plugin '{target}' reloaded.")
