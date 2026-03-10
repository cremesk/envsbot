"""
Reload Plugin

Provides a command to reload bot plugins at runtime without restarting
the bot.

Commands
--------
reload <plugin>
    Reload a single plugin.

reload all
    Reload all currently loaded plugins.

Notes
-----
Only bot owners/admins can use this command. When reloading all plugins,
the reload plugin itself is reloaded last to avoid interrupting the
running command.
"""

import logging
from command import command


PLUGIN_META = {
    "name": "reload",
    "version": "1.0",
    "description": "Reload plugins without restarting the bot"
}

log = logging.getLogger(__name__)


@command("reload", owner_only=True)
async def reload_plugin(bot, sender, nick, args, msg, is_room):
    """
    Reload one plugin or all plugins.

    Usage
    -----
    {prefix}reload <plugin>
        Reload a specific plugin.

    {prefix}reload all
        Reload all currently loaded plugins.

    Examples
    --------
    {prefix}reload help
    {prefix}reload status
    {prefix}reload all
    """

    if not args:
        bot.reply(msg, f"Usage: {bot.prefix}reload <plugin|all>")
        return

    target = args[0].lower()

    log.info("[PLUGIN] Reload command requested by %s: %s", sender, target)

    # Reload ALL plugins
    if target == "all":
        plugins = list(bot.plugins.plugins.keys())

        success = []
        failed = []

        for name in plugins:
            if name == "reload":
                continue
            try:
                log.info("[PLUGIN] Reloading plugin: %s", name)
                bot.plugins.reload(name)
                success.append(name)
            except Exception as e:
                log.exception("[PLUGIN] ❌Failed to reload plugin: %s", name)
                failed.append(f"{name} ({e})")

        # Reload this plugin last
        try:
            log.info("[PLUGIN] Reloading plugin: reload")
            bot.plugins.reload("reload")
            success.append("reload")
        except Exception as e:
            log.exception("[PLUGIN] ❌Failed to reload plugin: reload")
            failed.append(f"reload ({e})")

        message = []
        if success:
            message.append("Reloaded: " + ", ".join(success))
        if failed:
            message.append("Failed: " + ", ".join(failed))
        log.info(f"[PLUGIN] Reload: {"\n".join(message)}")
        bot.reply(msg, "\n".join(message))
        return

    # Reload ONE plugin
    plugin = target

    if plugin not in bot.plugins.plugins:
        available = ", ".join(sorted(bot.plugins.plugins.keys()))
        bot.reply(msg, f"❌Plugin '{plugin}' not found. Available: {available}")
        log.warning("[PLUGIN] ⚠ Reload requested for unknown plugin: %s", plugin)
        return

    try:
        log.info("[PLUGIN] Reloading plugin: %s", plugin)
        bot.plugins.reload(plugin)
        bot.reply(msg, f"Plugin '{plugin}' reloaded.")

    except Exception as e:
        log.exception("[PLUGIN] ❌Reload failed for plugin: %s", plugin)
        bot.reply(msg, f"❌Reload failed: {e}")
