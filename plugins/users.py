"""
Users plugin.

Provides:
- User registration and management
- Last-seen tracking
- Nickname tracking per room (runtime via PluginRuntimeStore)
- Lookup by JID or nickname

Usage examples:
    {prefix}users register
    {prefix}users info <jid|nick>
    {prefix}users list
    {prefix}users update <jid> <role>
    {prefix}users delete <jid>
"""

import logging
import asyncio
from datetime import datetime, timezone
from slixmpp import JID

from utils.config import config
from utils.command import command, Role, role_from_int

log = logging.getLogger(__name__)

MAX_ROOM_NICKS = config.get("users", {}).get("max_room_nicks", 5)

PLUGIN_META = {
    "name": "users",
    "version": "2.6.0",
    "description": "User management with caching, nick lookup and logging",
    "category": "core",
    "requires": ["rooms"],
}


# ---------------------------------------------------------------------------
# ON_LOAD setup function
# ---------------------------------------------------------------------------

async def on_load(bot):
    """
    Initialize plugin and register MUC handlers.
    """
    # --- initialize _nick_index on UserManager
    store = bot.db.users.plugin("users")
    bot.db.users._nick_index = await store.get_global("_nick_index", {})
    if bot.db.users._nick_index is None:
        bot.db.users._nick_index = {}

    async def on_muc_presence(pres):
        if pres["type"] not in ("available", "unavailable"):
            return

        try:
            room = pres["muc"]["room"]
            nick = pres["muc"]["nick"]
        except KeyError:
            return

        # Check for real jid
        real_jid = pres["muc"].get("jid")

        # Return if no real JID
        if real_jid:
            real_jid = str(real_jid.bare)
        else:
            return

        # Filter our own messages
        bare_jid = str(JID(real_jid).bare)
        if bare_jid == bot.boundjid.bare:
            return

        if pres["type"] == "unavailable":
            await update_last_seen(bot, real_jid)
            return

        await asyncio.gather(
            track_room_nick(bot, real_jid, room, nick),
            update_last_seen(bot, real_jid),
        )

    async def on_groupchat_message(msg):
        try:
            room = msg["muc"]["room"]
            nick = msg["muc"]["nick"]
        except KeyError:
            return

        # Check Room Affiliation
        rooms_plugin = bot.plugins.plugins.get("rooms")
        if not rooms_plugin:
            return
        if not rooms_plugin.bot_has_privilege(room):
            return

        # Check for real JID
        muc = bot.plugin.get("xep_0045", None)
        real_jid = None
        if muc:
            try:
                real_jid = muc.get_jid_property(room, nick, "jid")
            except Exception:
                real_jid = None

        # Filter our own messages
        if not real_jid:
            return
        bare_jid = str(JID(real_jid).bare)
        if bare_jid == bot.boundjid.bare:
            return

        await update_last_seen(bot, real_jid)

    bot.add_event_handler("groupchat_presence", on_muc_presence)
    bot.add_event_handler("groupchat_message", on_groupchat_message)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

async def find_users_by_nick_safe(bot, nick: str):
    """
    Find users by nick using cache and fallback scan.
    """
    index = bot.db.users._nick_index
    return sorted(list(index.get(nick, [])))


async def _send_user_info(bot, msg, user: dict):
    """
    Format and send user info.

    Includes:
    - JID
    - nickname
    - role
    - creation date
    - last seen
    """
    try:
        role = role_from_int(user["role"])

        created = user.get("created_at") or user.get("created")
        last_seen = user.get("last_seen")

        lines = [
            "👤 User Info:",
            f"- JID: {user['jid']}",
            f"- Nickname: {user.get('nickname') or '—'}",
            f"- Role: {role.name.lower()}",
        ]

        if created:
            lines.append(f"- Created: {created}")

        if last_seen:
            lines.append(f"- Last seen: {last_seen}")

        log.debug(f"[USERS] 📄 Sending user info: {user['jid']}")
        bot.reply(msg, "\n".join(lines))

    except Exception:
        log.exception("[USERS] ❌ Failed to format user info")
        bot.reply(msg, "⚠️ Failed to format user info.")


# ---------------------------------------------------------------------------
# RUNTIME
# ---------------------------------------------------------------------------

async def track_room_nick(bot, real_jid: str, room: str, nick: str):
    """
    Track nickname history per room using PluginRuntimeStore
    and maintain a global nick index for O(1) lookup.
    """
    um = bot.db.users
    if await um.get(real_jid) is None:
        await um.create(real_jid, nick)

    store = um.plugin("users")

    # --- load current state ---
    roomnicks = await store.get(real_jid, "roomnicks") or {}

    nicks = roomnicks.get(room, [])

    # no-op if already most recent
    if nicks and nicks[0] == nick:
        return

    # reorder / insert nick
    if nick in nicks:
        nicks.remove(nick)

    nicks.insert(0, nick)
    roomnicks[room] = nicks[:MAX_ROOM_NICKS]

    await store.set(real_jid, "roomnicks", roomnicks)

    # collect all current nicks for this user
    new_nicks = [n for nicks in roomnicks.values() for n in nicks]
    new_nicks = list(dict.fromkeys(new_nicks))

    # --- maintain global index ---
    async with um._nick_index_lock:
        index = um._nick_index

        # 1. remove jid from all mappings
        for n, jids in list(index.items()):
            if real_jid in jids:
                filtered = [j for j in jids if j != real_jid]
                if filtered:
                    index[n] = filtered
                else:
                    del index[n]

        # 2. add jid to current nick set
        for n in new_nicks:
            jids = index.setdefault(n, [])
            if real_jid not in jids:
                jids.append(real_jid)

    log.debug(f"[USERS] 📝 Nick tracked: {real_jid} -> {room} = {nick}")


async def update_last_seen(bot, real_jid: str):
    """
    Update last_seen timestamp.
    """
    now = datetime.now(timezone.utc)

    try:
        user = await bot.db.users.get(real_jid)

        if user and user.get("last_seen"):
            try:
                last_seen = datetime.fromisoformat(user["last_seen"])
                if (now - last_seen).total_seconds() < 60:
                    return
            except Exception:
                pass

        await bot.db.users.update_last_seen(real_jid)

        log.debug(f"[USERS] ⏱️ Updated last_seen: {real_jid}")

    except Exception:
        log.exception(f"[USERS] ❌ Failed to update last_seen for {real_jid}")


# ---------------------------------------------------------------------------
# COMMANDS
# ---------------------------------------------------------------------------

@command("users register", role=Role.NONE, aliases=["user register", "register"])
async def users_register(bot, sender, nick, args, msg, is_room):
    """
    Register yourself.

    Usage:
        {prefix}users register
    """
    try:
        jid = None
        nickname = nick

        muc_data = msg.get("muc")
        msg_type = msg.get("type")
        to_obj = msg.get("to")

        to_jid = str(to_obj.bare) if to_obj else None
        bot_jid = str(bot.boundjid.bare)

        # ---------------------------------------------------------
        # 1. Message from groupchat (MUC room)
        # ---------------------------------------------------------
        if is_room:
            room = muc_data.get("room") if muc_data else None
            muc_nick = muc_data.get("nick") if muc_data else None

            if not room or not muc_nick:
                log.info(
                    f"[USERS][REGISTER] ❌ Incomplete MUC room data "
                    f"(room={room}, nick={muc_nick}, sender={sender})"
                )
                bot.reply(msg, "❌ Could not resolve your identity.")
                return

            muc = bot.plugin.get("xep_0045", None)
            real_jid = None

            if muc:
                try:
                    real_jid = muc.get_jid_property(room, muc_nick, "jid")
                except Exception:
                    real_jid = None

            if not real_jid:
                log.info(
                    f"[USERS][REGISTER] ❌ No real JID in room "
                    f"(room={room}, nick={muc_nick})"
                )
                bot.reply(
                    msg,
                    "❌ Cannot determine your real JID (room may be anonymous)."
                )
                return

            jid = str(JID(real_jid).bare)
            nickname = muc_nick

        # ---------------------------------------------------------
        # 2. Message from MUC direct message (PM)
        # ---------------------------------------------------------
        elif muc_data and msg_type == "chat":
            room = muc_data.get("room")
            muc_nick = muc_data.get("nick")

            if not room or not muc_nick:
                log.info(
                    f"[USERS][REGISTER] ❌ Incomplete MUC PM data "
                    f"(room={room}, nick={muc_nick}, sender={sender})"
                )
                bot.reply(msg, "❌ Could not resolve your identity.")
                return

            muc = bot.plugin.get("xep_0045", None)
            real_jid = None

            if muc:
                try:
                    real_jid = muc.get_jid_property(room, muc_nick, "jid")
                except Exception:
                    real_jid = None

            if not real_jid:
                log.info(
                    f"[USERS][REGISTER] ❌ No real JID in MUC PM "
                    f"(room={room}, nick={muc_nick})"
                )
                bot.reply(
                    msg,
                    "❌ Cannot determine your real JID (room may be anonymous)."
                )
                return

            jid = str(JID(real_jid).bare)
            nickname = muc_nick

        # ---------------------------------------------------------
        # 3. Direct message to bot JID ONLY (chat + normal)
        # ---------------------------------------------------------
        elif msg_type in ("chat", "normal") and to_jid == bot_jid:
            jid = str(JID(sender).bare)

        # ---------------------------------------------------------
        # Invalid context
        # ---------------------------------------------------------
        else:
            log.info(
                f"[USERS][REGISTER] ❌ Invalid context "
                f"(type={msg_type}, to={to_jid}, sender={sender})"
            )
            bot.reply(
                msg,
                "❌ This command can only be used in MUCs, MUC private messages, or direct messages to the bot."
            )
            return

        # ---------------------------------------------------------
        # Registration logic
        # ---------------------------------------------------------
        um = bot.db.users

        existing = await um.get(jid)

        if existing:
            bot.reply(msg, "ℹ️ You are already registered.")
            return

        await um.create(jid, nickname)

        bot.reply(msg, "✅ You are now registered.")
        log.info(f"[USERS][REGISTER] ✅ Registered: {jid}")

    except Exception:
        log.exception("[USERS][REGISTER] ❌ register failed")
        bot.reply(msg, "❌ Registration failed.")

@command("users info", role=Role.ADMIN, aliases=["user info"])
async def users_info(bot, sender, nick, args, msg, is_room):
    """
    Show user info by JID or nickname.

    Usage:
        {prefix}users info <jid|nick>
    """
    try:
        if not args:
            log.warning("[USERS] ⚠️ users info without args")
            bot.reply(msg, f"⚠️ Usage: {config.prefix}users info <jid|nick>")
            return

        query = args[0]
        um = bot.db.users

        try:
            jid_query = str(JID(query).bare)
            user = await um.get(jid_query)
        except Exception:
            user = None

        if user:
            log.info(f"[USERS] 🔎 Info lookup by JID: {jid_query}")
            await _send_user_info(bot, msg, user)
            return

        jids = await find_users_by_nick_safe(bot, query)

        if not jids:
            log.warning(f"[USERS] ⚠️ No users found for nick: {query}")
            bot.reply(msg, f"⚠️ No users found for nick: {query}")
            return

        if len(jids) > 1:
            log.info(f"[USERS] 🔎 Multiple users for nick: {query}")
            lines = [f"🔎 Multiple users found for '{query}':"]
            for jid in jids:
                lines.append(f"- {jid}")
            bot.reply(msg, "\n".join(lines))
            return

        jid = next(iter(jids))
        user = await um.get(jid)

        if user is None:
            log.info(f"[USERS][INFO] ❌ Unregistered user (jid={jid})")
            bot.reply(msg, "❌ User is not registered.")
            return

        log.info(f"[USERS] 🔎 Info lookup by nick: {query} -> {jid}")
        await _send_user_info(bot, msg, user)

    except Exception:
        log.exception("[USERS] ❌ users info failed")
        bot.reply(msg, "⚠️ Failed to fetch user info.")


@command("users update", role=Role.ADMIN, aliases=["user update"])
async def users_update(bot, sender, nick, args, msg, is_room):
    """
    Update a user's role.

    Usage:
        {prefix}users update <jid> <role>
    """
    try:
        if len(args) < 2:
            log.warning("[USERS] ⚠️ users update missing args")
            bot.reply(msg, f"⚠️ Usage: {config.prefix}users update <jid> <role>")
            return

        try:
            jid = str(JID(args[0]).bare)
        except Exception:
            log.warning(f"[USERS] ⚠️ Invalid JID for update: {args[0]}")
            bot.reply(msg, "⚠️ Invalid JID.")
            return

        role_input = args[1].lower()
        um = bot.db.users

        user = await um.get(jid)
        if not user:
            log.warning(f"[USERS] ⚠️ Update failed, user not found: {jid}")
            bot.reply(msg, f"⚠️ User not found: {jid}")
            return

        role_map = {r.name.lower(): r for r in Role}

        if role_input not in role_map:
            log.warning(f"[USERS] ⚠️ Invalid role: {role_input}")
            bot.reply(
                msg,
                f"⚠️ Invalid role. Available: {', '.join(role_map.keys())}",
            )
            return

        new_role = role_map[role_input]

        await um.update_user(jid, role=new_role.value)

        log.info(f"[USERS] 🔄 Role updated: {jid} -> {new_role.name.lower()}")
        bot.reply(msg, f"🔄 Updated role for {jid}: {new_role.name.lower()}")

    except Exception:
        log.exception("[USERS] ❌ users update failed")
        bot.reply(msg, "⚠️ Failed to update user.")


@command("users list", role=Role.ADMIN, aliases=["user list"])
async def users_list(bot, sender, nick, args, msg, is_room):
    """
    List all users.

    Usage:
        {prefix}users list
    """
    try:
        users = await bot.db.users.get_all_users()

        if not users:
            log.info("[USERS] ℹ️ No users in database")
            bot.reply(msg, "⚠️ No users.")
            return

        lines = ["📋 Users:"]
        for user in users:
            role = role_from_int(user["role"])
            lines.append(
                f"- {user['jid']} ({user['nickname']}) [{role.name.lower()}]"
            )

        log.info(f"[USERS] 📋 Listed {len(users)} users")
        bot.reply(msg, "\n".join(lines))

    except Exception:
        log.exception("[USERS] ❌ users list failed")
        bot.reply(msg, "⚠️ Failed to list users.")


@command("users delete", role=Role.ADMIN, aliases=["user delete"])
async def users_delete(bot, sender, nick, args, msg, is_room):
    """
    Delete a user.

    Usage:
        {prefix}users delete <jid>
    """
    try:
        if not args:
            bot.reply(msg, f"⚠️ Usage: {config.prefix}users delete <jid>")
            return

        try:
            jid = str(JID(args[0]).bare)
        except Exception:
            log.warning(f"[USERS] ⚠️ Invalid JID for delete: {args[0]}")
            bot.reply(msg, "⚠️ Invalid JID.")
            return

        um = bot.db.users
        user = await um.get(jid)
        runtime = await um.get_runtime(jid)
        profile = await um.get_profile(jid)

        if not user:
            if runtime or profile:
                log.warning(f"[USERS] ⚠️ DB inconsistent: {jid} not"
                            " found, but runtime or profile exists!"
                            " Deleting remaining runtime or profile entries!")
                bot.reply(msg, f"⚠️ DB inconsistent for: {jid}"
                               " - Deleting remaining DB rows!")
            else:
                log.warning(f"[USERS] ⚠️ Delete failed, user not found: {jid}")
                bot.reply(msg, f"⚠️ User not found: {jid}")
                return

        await um.delete(jid)

        log.info(f"[USERS] 🗑️ Deleted user: {jid}")
        bot.reply(msg, f"🗑️ Deleted: {jid}")

    except Exception:
        log.exception("[USERS] ❌ users delete failed")
        bot.reply(msg, "⚠️ Failed to delete user.")
