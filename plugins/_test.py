"""
Test commands.

This plugin provides simple commands used by the automated test
suite. They verify that the command resolver, permission system,
and reply helper work correctly.

Category: test
"""

from utils.command import command, Role, COMMANDS


PLUGIN_META = {
    "name": "test",
    "version": "1.2",
    "description": "Testing commands for the bot.",
    "category": "test",
}


@command(
    name="_ping",
    role=Role.NONE,
)
async def test_ping(bot, sender, nick, args, msg, is_room):
    """
    Test Ping command.

    Responds with "test pong". This command is primarily intended for
    automated testing and diagnostics.

    Usage
    -----
    {prefix}_ping
    """

    bot.reply(msg, "test pong")


@command(
    name="_reloadtest",
    role=Role.NONE,
)
async def reload_test(bot, sender, nick, args, msg, is_room):
    """
    Reload test command.

    Responds with a deterministic string so automated tests can
    verify that the command remains functional after plugin reload.

    This command exists solely to validate that:

    - commands are registered when the plugin loads
    - commands are removed when the plugin unloads
    - commands are registered exactly once after reload

    Usage
    -----
    {prefix}_reloadtest
    """

    dump = COMMANDS.debug_dump()
    if dump == {}:
        bot.reply(msg, "No command registered")
        return
    for name, info in dump.items():
        bot.reply(msg, f"{name} -> {info['handler']} ({info['role']})")
