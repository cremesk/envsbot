"""
SED plugin for message correction.

This plugin allows users to correct their previous messages using sed-like syntax.
It tracks the last message from each user and applies regex substitutions.

Commands:
    s/<pattern>/<replacement>/<flags> - Correct last message
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

# Store last messages: {room_jid: {nick: message}, ...}
LAST_MESSAGES = {}

# Store messages by ID for reply tracking: {room_jid: {message_id: (nick, message)}, ...}
MESSAGES_BY_ID = {}

# Track which messages we've already processed to avoid duplicates
PROCESSED_STANZAS = set()


def store_message(sender_jid, nick, room, message, msg_id, stanza_id=None):
    """Store the last message from a user and by ID."""
    if room:
        if room not in LAST_MESSAGES:
            LAST_MESSAGES[room] = {}
        LAST_MESSAGES[room][nick] = message

        if room not in MESSAGES_BY_ID:
            MESSAGES_BY_ID[room] = {}

        # Store by both msg_id and stanza_id
        MESSAGES_BY_ID[room][msg_id] = (nick, message)
        if stanza_id:
            MESSAGES_BY_ID[room][stanza_id] = (nick, message)
    else:
        LAST_MESSAGES[str(sender_jid.bare)] = message
        jid_str = str(sender_jid.bare)
        if jid_str not in MESSAGES_BY_ID:
            MESSAGES_BY_ID[jid_str] = {}
        MESSAGES_BY_ID[jid_str][msg_id] = (None, message)


def get_last_message(sender_jid, nick, room):
    """Get the last message from a user."""
    if room:
        if room not in LAST_MESSAGES or nick not in LAST_MESSAGES[room]:
            return None
        return LAST_MESSAGES[room][nick]
    else:
        jid_str = str(sender_jid.bare)
        if jid_str not in LAST_MESSAGES:
            return None
        return LAST_MESSAGES[jid_str]


def get_message_by_id(room, msg_id):
    """Get a message by its ID (for reply context)."""
    if room not in MESSAGES_BY_ID:
        return None
    if msg_id not in MESSAGES_BY_ID[room]:
        return None
    return MESSAGES_BY_ID[room][msg_id][1]  # Return just the message text


def parse_sed_command(text):
    """
    Parse sed-like command: s/pattern/replacement/flags
    Returns (pattern, replacement, flags) or (None, None, None) on error
    """
    if not text.startswith('s'):
        return None, None, None

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

    Flags:
        i - case insensitive
        m - multiline
        s - dotall
        g - global replace
        l - literal mode (treat pattern as literal string, not regex)
    """
    try:
        re_flags = 0
        global_replace = False
        literal_mode = False

        for flag in flags_str.lower():
            if flag == 'i':
                re_flags |= re.IGNORECASE
            elif flag == 'm':
                re_flags |= re.MULTILINE
            elif flag == 's':
                re_flags |= re.DOTALL
            elif flag == 'g':
                global_replace = True
            elif flag == 'l':
                literal_mode = True

        if literal_mode:
            pattern = re.escape(pattern)

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


def is_sed_command(body):
    """Check if a message is a sed command (ignores reply quotes)."""
    lines = body.strip().split('\n')
    for line in lines:
        if not line.startswith('>'):
            if line.startswith('s/') and len(line) > 2:
                return True
    return False


def extract_sed_command(body):
    """Extract sed command from message body (removes reply quote if present)."""
    lines = body.strip().split('\n')
    for line in lines:
        if not line.startswith('>'):
            return line.strip()
    return body.strip()


def get_stanza_id(msg):
    """Extract the stanza_id from a message."""
    stanza_id = msg.get('stanza_id')
    if stanza_id:
        return stanza_id.get('id')
    return None


def get_reply_target(msg):
    """Get the ID of the message this is a reply to."""
    if 'reply' in msg:
        reply = msg.get('reply')
        if reply:
            return reply.get('id')
    return None


async def process_sed_correction(bot, sender_jid, nick, msg, is_room, pattern, replacement, flags_str):
    """Process a sed correction."""
    room = msg['from'].bare if is_room else None

    # Check if this is a reply to a specific message
    reply_target_id = get_reply_target(msg)

    # Try to get the message from reply context first
    last_msg = None
    if is_room and reply_target_id:
        last_msg = get_message_by_id(room, reply_target_id)

    # If no reply context, get the last message from this user
    if not last_msg:
        last_msg = get_last_message(sender_jid, nick, room)

    if not last_msg:
        bot.reply(msg, "❌ No previous message found to correct.")
        return

    try:
        new_msg, num_replacements = apply_sed(last_msg, pattern, replacement, flags_str)
    except Exception as e:
        bot.reply(msg, f"❌ Error applying sed: {e}")
        return

    if new_msg is None:
        bot.reply(msg, f"❌ Regex error. Check your pattern: {pattern}")
        return

    if num_replacements == 0:
        bot.reply(msg, f"❌ Pattern '{pattern}' not found in last message.")
        return

    if is_room:
        response = f"**{nick}**: {new_msg}"
    else:
        response = new_msg

    bot.reply(msg, response, mention=False)


@command("sed", role=Role.USER)
async def cmd_sed_handler(bot, sender_jid, nick, args, msg, is_room):
    """
    Handle sed corrections or enable/disable sed in a room.

    If used in a MUC PM with on/off argument: configure the room setting
    If used with a sed pattern: apply the correction

    Usage:
        {prefix}sed on|off              - Enable/disable sed (MUC PM, moderator only)
        {prefix}sed <pattern> <replacement> [flags] - Apply correction

    Examples:
        {prefix}sed hello hi
        {prefix}sed test prod g
        {prefix}sed -- xxx l
        {prefix}sed ERROR Error i
    """
    if (
        msg.get("type") in ("chat", "normal")
        and hasattr(msg["from"], "bare")
        and "@" in str(msg["from"].bare)
        and args and args[0] in ("on", "off")
    ):
        room = msg["from"].bare

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

    if not args or len(args) < 2:
        bot.reply(msg, "❌ Usage: {prefix}sed <pattern> <replacement> [flags]")
        return

    pattern = args[0]
    replacement = args[1]
    flags_str = args[2] if len(args) > 2 else ""

    await process_sed_correction(bot, sender_jid, nick, msg, is_room, pattern, replacement, flags_str)


async def on_message(bot, msg):
    """Track messages and handle sed commands."""
    try:
        body = msg.get("body", "").strip()

        if not body:
            return

        if msg.get("from") == bot.boundjid:
            return

        stanza_obj_id = id(msg)
        if stanza_obj_id in PROCESSED_STANZAS:
            return

        PROCESSED_STANZAS.add(stanza_obj_id)
        if len(PROCESSED_STANZAS) > 1000:
            PROCESSED_STANZAS.clear()

        is_room = msg.get("type") == "groupchat"
        sender_jid = msg["from"]
        nick = msg.get("mucnick") if is_room else None
        room = sender_jid.bare if is_room else None
        msg_id = msg.get("id")
        stanza_id = get_stanza_id(msg)

        if is_room:
            store = await get_sed_store(bot)
            enabled_rooms = await store.get_global(SED_KEY, default={})
            if room not in enabled_rooms:
                return

            if bot.presence.joined_rooms.get(room) == nick:
                return

        if is_sed_command(body):
            sed_cmd = extract_sed_command(body)
            pattern, replacement, flags_str = parse_sed_command(sed_cmd)

            if pattern is not None:
                await process_sed_correction(bot, sender_jid, nick, msg, is_room, pattern, replacement, flags_str)

            return

        if is_room:
            store_message(sender_jid, nick, room, body, msg_id, stanza_id)
        else:
            store_message(sender_jid, None, None, body, msg_id)
    except Exception as e:
        log.exception("[SED] Error in on_message: %s", e)


async def on_load(bot):
    """Register the message event handler."""
    bot.bot_plugins.register_event(
        "sed",
        "groupchat_message",
        partial(on_message, bot)
    )
