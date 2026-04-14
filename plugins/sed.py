"""
SED plugin for message correction.

This plugin allows users to correct their previous messages using sed-like syntax.
It tracks the last message from each user and applies regex substitutions.
Messages are deleted after being corrected.

Commands:
    {prefix}s/<pattern>/<replacement>/<flags> - Correct last message
    {prefix}sed <pattern> <replacement> [flags] - Alternative syntax
    {prefix}sed on/off - Enable/disable sed plugin in this room (moderator only)
"""
import re
import logging
from functools import partial
from utils.command import command, Role
from plugins.rooms import JOINED_ROOMS

log = logging.getLogger(__name__)

PLUGIN_META = {
    "name": "sed",
    "version": "0.1.0",
    "description": "Message correction using sed-like syntax",
    "category": "tools",
    "Requires": ["rooms"],
}

SED_KEY = "SED"

# Store last messages: {room_jid: {nick: (message, thread_id)}, ...}
# For private messages: {sender_jid: (message, thread_id)}
LAST_MESSAGES = {}


def store_message(sender_jid, nick, room, message, thread_id):
    """Store the last message from a user."""
    if room:
        if room not in LAST_MESSAGES:
            LAST_MESSAGES[room] = {}
        LAST_MESSAGES[room][nick] = (message, thread_id)
    else:
        LAST_MESSAGES[str(sender_jid.bare)] = (message, thread_id)


def get_and_delete_message(sender_jid, nick, room):
    """Retrieve and delete the last message from a user."""
    if room:
        if room not in LAST_MESSAGES or nick not in LAST_MESSAGES[room]:
            return None, None
        msg, thread_id = LAST_MESSAGES[room][nick]
        del LAST_MESSAGES[room][nick]
        return msg, thread_id
    else:
        jid_str = str(sender_jid.bare)
        if jid_str not in LAST_MESSAGES:
            return None, None
        msg, thread_id = LAST_MESSAGES[jid_str]
        del LAST_MESSAGES[jid_str]
        return msg, thread_id


def parse_sed_command(text):
    """
    Parse sed-like command: s/pattern/replacement/flags
    Returns (pattern, replacement, flags) or (None, None, None) on error
    """
    if not text.startswith('s'):
        return None, None, None

    # Extract delimiter (usually /)
    if len(text) < 2:
        return None, None, None

    delimiter = text[1]
    parts = text[2:].split(delimiter)

    if len(parts) < 2:
        return None, None, None

    pattern = parts[0]
    replacement = parts[1]
    flags_str = parts[2] if len(parts) > 2 else ""

    return pattern, replacement, flags_str


def apply_sed(original_text, pattern, replacement, flags_str):
    """
    Apply sed substitution to text.
    Returns (new_text, num_replacements) or (None, 0) on error
    """
    try:
        # Parse flags
        re_flags = 0
        global_replace = False

        for flag in flags_str.lower():
            if flag == 'i':
                re_flags |= re.IGNORECASE
            elif flag == 'm':
                re_flags |= re.MULTILINE
            elif flag == 's':
                re_flags |= re.DOTALL
            elif flag == 'g':
                global_replace = True

        # Apply substitution
        if global_replace:
            new_text, num = re.subn(pattern, replacement, original_text, flags=re_flags)
        else:
            new_text, num = re.subn(pattern, replacement, original_text, count=1, flags=re_flags)

        return new_text, num
    except re.error as e:
        return None, 0


async def get_sed_store(bot):
    """Get the database store for sed settings."""
    return bot.db.users.plugin("sed")


@command("sed", "s", role=Role.USER)
async def cmd_sed_handler(bot, sender_jid, nick, args, msg, is_room):
    """
    Handle sed corrections or enable/disable sed in a room.

    If used in a MUC PM with on/off argument: configure the room setting
    If used with a sed pattern: apply the correction

    Usage:
        {prefix}sed on|off              - Enable/disable sed (MUC PM, moderator only)
        {prefix}s/<pattern>/<replacement>/<flags> - Correct last message
        {prefix}sed <pattern> <replacement> [flags] - Alternative syntax

    Examples:
        {prefix}s/hello/hi/
        {prefix}s/test/prod/g
        {prefix}sed ERROR Error i
    """
    # Check if this is a moderator trying to enable/disable in a MUC PM
    if (
        msg.get("type") in ("chat", "normal")
        and hasattr(msg["from"], "bare")
        and "@" in str(msg["from"].bare)
        and args and args[0] in ("on", "off")
    ):
        room = msg["from"].bare

        # Only allow in joined rooms
        if room not in JOINED_ROOMS:
            bot.reply(
                msg,
                "This room is not a joined room. SED can only be "
                "enabled or disabled for joined rooms."
            )
            return

        store = await get_sed_store(bot)
        enabled_rooms = await store.get_global(SED_KEY, default={})

        if args[0] == "on":
            enabled_rooms[room] = True
            await store.set_global(SED_KEY, enabled_rooms)
            bot.reply(msg, "✅ SED corrections enabled in this room.")
        else:
            if room in enabled_rooms:
                del enabled_rooms[room]
                await store.set_global(SED_KEY, enabled_rooms)
            bot.reply(msg, "🛑 SED corrections disabled in this room.")
        return

    # Handle sed correction
    # Short form: s/pattern/replacement/flags
    if msg.get("body", "").strip().startswith(bot.prefix + "s/"):
        if not args or len(args) < 1:
            bot.reply(msg, "❌ Usage: {prefix}s/<pattern>/<replacement>/<flags>")
            return

        sed_cmd = args[0]
        pattern, replacement, flags_str = parse_sed_command(sed_cmd)

        if pattern is None:
            bot.reply(msg, "❌ Invalid sed syntax. Use: s/<pattern>/<replacement>/<flags>")
            return
    else:
        # Long form: sed pattern replacement [flags]
        if not args or len(args) < 2:
            bot.reply(msg, "❌ Usage: {prefix}sed <pattern> <replacement> [flags]")
            return

        pattern = args[0]
        replacement = args[1]
        flags_str = args[2] if len(args) > 2 else ""

    # Get and delete last message
    room = msg['from'].bare if is_room else None
    last_msg, thread_id = get_and_delete_message(sender_jid, nick, room)

    if not last_msg:
        bot.reply(msg, "❌ No previous message found to correct.")
        return

    # Apply sed
    new_msg, num_replacements = apply_sed(last_msg, pattern, replacement, flags_str)

    if new_msg is None:
        bot.reply(msg, f"❌ Regex error. Check your pattern: {pattern}")
        return

    if num_replacements == 0:
        bot.reply(msg, f"❌ Pattern '{pattern}' not found in last message.")
        return

    # Format response
    if is_room:
        response = f"**{nick}** meant to say:\n\n{new_msg}"
    else:
        response = f"You meant to say:\n\n{new_msg}"

    bot.reply(msg, response, mention=False)


async def on_message(bot, msg):
    """Track messages for sed correction (only if enabled for the room)."""
    try:
        body = msg.get("body", "").strip()

        # Don't track empty or command messages
        if not body or body.startswith(bot.prefix):
            return

        is_room = msg.get("type") == "groupchat"
        sender_jid = msg["from"]

        if is_room:
            room = sender_jid.bare
            nick = msg.get("mucnick")

            # Check if sed is enabled for this room
            store = await get_sed_store(bot)
            enabled_rooms = await store.get_global(SED_KEY, default={})
            if room not in enabled_rooms:
                return

            # Don't track bot's own messages
            if bot.presence.joined_rooms.get(room) == nick:
                return

            thread_id = msg.get("thread") or msg.get("id")
            store_message(sender_jid, nick, room, body, thread_id)
        else:
            # Always track direct messages
            thread_id = msg.get("thread") or msg.get("id")
            store_message(sender_jid, None, None, body, thread_id)
    except Exception as e:
        log.exception("[SED] Error tracking message: %s", e)


async def on_load(bot):
    """Register the message event handler."""
    bot.bot_plugins.register_event(
        "sed",
        "groupchat_message",
        partial(on_message, bot)
    )
    bot.bot_plugins.register_event(
        "sed",
        "message",
        partial(on_message, bot)

