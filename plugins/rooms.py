"""
Room management and persistence.

This plugin provides administrative commands for managing XMPP
multi-user chat rooms stored in the bot database. Administrators
can add rooms, update their configuration, remove them, view the
current list of rooms, and control whether the bot joins or leaves
rooms at runtime.

Rooms can optionally be configured with an *autojoin* flag so the
bot automatically joins them when it starts.
"""

import asyncio
import logging

from slixmpp import JID

from utils.command import command, Role

log = logging.getLogger(__name__)

PLUGIN_META = {
    "name": "rooms",
    "version": "2.4",
    "description": "Database-backed room management",
    "category": "core",
}

# joined rooms module global
JOINED_ROOMS = {}


# -------------------------------------------------
# ROOM PRIVILEGE CHECK
# -------------------------------------------------

def bot_has_privilege(room, required=("admin", "owner")):
    info = JOINED_ROOMS.get(room)
    if not info:
        return False
    return info.get("affiliation") in required


# -------------------------------------------------
# ROOM JID VALIDATION
# -------------------------------------------------

async def is_valid_muc_domain(bot, domain: str) -> bool:
    """
    Check if a domain provides a MUC service using XMPP service discovery.
    """

    try:
        info = await bot["xep_0030"].get_info(jid=domain)

        for feature in info["disco_info"]["features"]:
            if feature == "http://jabber.org/protocol/muc":
                return True

    except Exception as e:
        log.warning("[ROOMS] ⚠️ MUC discovery failed for %s: %s", domain, e)

    return False


async def is_valid_room_jid(bot, jid: str, target, mtype) -> bool:
    """
    Validate that a string looks like a proper room JID.

    Requirements
    ------------
    - must contain node@domain
    - must not contain a resource part
    """

    if "/" in jid:
        return False

    if "@" not in jid:
        return False

    node, domain = jid.split("@", 1)

    if not node or not domain:
        return False

    try:
        async with asyncio.timeout(5):
            is_valid = await is_valid_muc_domain(bot, domain)
    except TimeoutError:
        is_valid = False
    if not is_valid:
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Domain '{domain}' does not provide muc service.",
            mtype=mtype)
        return False
    return True


# -------------------------------------------------
# ROOM STATUS HELPER FUNCTIONS
# -------------------------------------------------
async def room_status_get(bot, room_jid, path=None):
    return await bot.db.rooms.status_get(room_jid, path)


async def room_status_set(bot, room_jid, path, value):
    await bot.db.rooms.status_set(room_jid, path, value)


async def room_status_delete(bot, room_jid, path):
    await bot.db.rooms.status_delete(room_jid, path)


# -------------------------------------------------
# AutoJoin Rooms function
# -------------------------------------------------

async def autojoin_rooms(bot):
    """
    Join all rooms marked with autojoin in the database.
    """
    muc = bot.plugin["xep_0045"]

    rows = await bot.db.rooms.list()
    for room_jid, nick, autojoin, status in rows:
        if not autojoin:
            continue
        log.info("[MUC] Autojoining room %s as %s", room_jid, nick)
        await muc.join_muc(
            room_jid,
            nick,
            pshow=bot.presence.status["show"],
            pstatus=bot.presence.status["status"])
        try:
            affiliation = await muc.get_jid_property(room_jid,
                                                     bot.boundjid.bare,
                                                     "affiliation")
        except Exception:
            affiliation = "unknown"

        if room_jid not in JOINED_ROOMS:
            JOINED_ROOMS[room_jid] = {
                "nick": nick,
                "autojoin": autojoin,
                "status": status,
                "affiliation": affiliation
            }
        bot.presence.joined_rooms[room_jid] = nick


# -------------------------------------------------
# ROOMS ADD
# -------------------------------------------------

@command("rooms add", role=Role.ADMIN, aliases=["room add"])
async def rooms_add(bot, sender_jid, nick, args, msg, is_room):
    """
    Add a new room configuration to the database.

    Command
    -------
    {prefix}rooms add <room_jid> <nick> [autojoin]

    Description
    -----------
    Registers a room together with the nickname the bot should use
    when joining it.

    If the optional *autojoin* flag is enabled, the bot will join
    the room automatically during startup.

    Examples
    --------
    {prefix}rooms add dev@conference.example.org BotNick
    {prefix}rooms add dev@conference.example.org BotNick true
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    if len(args) < 2:
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Usage: {bot.prefix}rooms add <room_jid> <nick> [autojoin]",
            mtype=mtype
        )
        return

    room_jid = args[0]
    room_nick = args[1]

    if not await is_valid_room_jid(bot, room_jid, target, mtype):
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Invalid room JID: {room_jid}",
            mtype=mtype
        )
        log.warning(f"[ROOMS]⚠️ Room '{room_jid}' not valid!")
        return

    autojoin = len(args) >= 3 and args[2].lower() in ("true", "1", "yes")

    await bot.db.rooms.add(room_jid, room_nick, autojoin)

    log.info("[ROOMS] ➕ Added room %s nick=%s autojoin=%s",
             room_jid, room_nick, autojoin)

    bot.send_message(
        mto=target,
        mbody=f"✅ Room added: {room_jid}",
        mtype=mtype
    )


# -------------------------------------------------
# ROOMS UPDATE
# -------------------------------------------------

@command("rooms update", role=Role.ADMIN, aliases=["room update"])
async def rooms_update(bot, sender_jid, nick, args, msg, is_room):
    """
    Update a configuration field of a stored room.

    Command
    -------
    {prefix}rooms update <room_jid> <field> <value>

    Supported fields
    ----------------
    nick
        Nickname the bot should use when joining the room.
    autojoin
        Controls whether the bot automatically joins the room
        when it starts.

        Allowed values:
        true, false, yes, no, 1, 0
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    if len(args) < 3:
        bot.send_message(
            mto=target,
            mbody=(f"⚠️ Usage: {bot.prefix}rooms update <room_jid>"
                   f" <field> <value>"),
            mtype=mtype
        )
        return

    room_jid = args[0]

    if not await is_valid_room_jid(bot, room_jid, target, mtype):
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Invalid room JID: {room_jid}",
            mtype=mtype
        )
        log.warning(f"[ROOMS]⚠️Room '{room_jid}' not valid!")
        return

    field = args[1].lower()
    value = args[2]
    if field in ["nick", "autojoin"]:

        if field == "autojoin":
            value = value.lower() in ("true", "1", "yes")

        await bot.db.rooms.update(room_jid, **{field: value})

        log.info("[ROOMS] 🔧 Updated %s: %s=%s", room_jid, field, value)

        bot.send_message(
            mto=target,
            mbody=f"🔧 Room updated: {room_jid}",
            mtype=mtype
        )
    else:
        log.info("[ROOMS] 🔧 Update failed! Invalid field '%s'", field)

        bot.send_message(
            mto=target,
            mbody=f"🔧 Room not updated. Invalid field: '{field}'",
            mtype=mtype
        )


# -------------------------------------------------
# ROOMS DELETE
# -------------------------------------------------

@command("rooms delete", role=Role.ADMIN, aliases=["room delete"])
async def rooms_delete(bot, sender_jid, nick, args, msg, is_room):
    """
    Remove a room configuration from the database.

    Command
    -------
    {prefix}rooms delete <room_jid> [force]

    Description
    -----------
    Deletes a stored room configuration.

    If the bot is currently joined to that room it will leave it
    automatically.
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    if len(args) < 1:
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Usage: {bot.prefix}rooms delete <room_jid>",
            mtype=mtype
        )
        return

    room_jid = args[0]

    if not await is_valid_room_jid(bot, room_jid, target, mtype):
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Invalid room JID: {room_jid}",
            mtype=mtype
        )
        log.warning(f"[ROOMS]⚠️Room '{room_jid}' not valid!")
        return

    try:
        if room_jid in await bot.db.rooms.list():
            await bot.db.rooms.delete(room_jid)

        joined = room_jid in JOINED_ROOMS

        if joined:

            bot.plugin["xep_0045"].leave_muc(room_jid, bot.boundjid.user)

            del JOINED_ROOMS[room_jid]

            if room_jid in bot.presence.joined_rooms:
                del bot.presence.joined_rooms[room_jid]

            bot.presence.broadcast()

            log.info("[ROOMS] 🚶 Left room %s", room_jid)

        log.info("[ROOMS] 🗑️ Deleted room %s", room_jid)

        bot.send_message(
            mto=target,
            mbody=f"🗑️ Room removed: {room_jid}",
            mtype=mtype
        )

    except Exception:
        log.exception("[ROOMS] 🗑️ Failed to delete room %s", room_jid)

        bot.send_message(
            mto=target,
            mbody=f"🗑️ Failed remove room: {room_jid}",
            mtype=mtype
        )


# -------------------------------------------------
# ROOMS LIST
# -------------------------------------------------

@command("rooms list", role=Role.ADMIN, aliases=["room list"])
async def rooms_list(bot, sender_jid, nick, args, msg, is_room):
    """
    Show all rooms stored in the database.

    Command
    -------
    {prefix}rooms list
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    rows = await bot.db.rooms.list()

    if not rows:
        bot.send_message(mto=target, mbody="ℹ️ No rooms stored.", mtype=mtype)
        return

    header = f"{'ROOM':40} {'NICK':15} {'AUTOJOIN':8} {'JOINED':6} {'STATUS'}"
    lines = ["📋 Stored rooms", header, "-" * len(header)]

    for room_jid, nick_name, autojoin, status in rows:

        autojoin_flag = "yes" if autojoin else "no"
        joined_flag = "yes" if room_jid in bot.rooms else "no"

        lines.append(
            f"{room_jid:40} {nick_name:15} {autojoin_flag:8} {joined_flag:6}"
            f" {status}"
        )

    bot.send_message(mto=target, mbody="\n".join(lines), mtype=mtype)


# -------------------------------------------------
# ROOMS JOIN
# -------------------------------------------------

@command("rooms join", role=Role.ADMIN, aliases=["room join"])
async def rooms_join(bot, sender_jid, nick, args, msg, is_room):
    """
    Join a room immediately, add it to JOINED ROOMS and DB.

    Command
    -------
    {prefix}rooms join <room_jid> [nick]
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    if len(args) < 1:
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Usage: {bot.prefix}rooms join <room_jid> [nick]",
            mtype=mtype
        )
        return

    room_jid = args[0]

    if not await is_valid_room_jid(bot, room_jid, target, mtype):
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Invalid room JID: {room_jid}",
            mtype=mtype
        )
        log.warning(f"[ROOMS]⚠️Room '{room_jid}' not valid!")
        return

    if len(args) >= 2:
        room_nick = args[1]
    else:
        room = await bot.db.rooms.get(room_jid)
        room_nick = room[1] if room else bot.boundjid.user

    try:
        muc = bot.plugin["xep_0045"]

        await muc.join_muc(room_jid, room_nick)
        affiliation = await muc.get_jid_property(room_jid, bot.boundjid.bare,
                                                 "affiliation")

        if room_jid not in JOINED_ROOMS:
            JOINED_ROOMS[room_jid] = {
                "nick": room_nick,
                "autojoin": False,
                "status": None,
                "affiliation": affiliation
            }

        bot.presence.joined_rooms[room_jid] = room_nick
        bot.presence.broadcast()

        await bot.db.rooms.add(room_jid, room_nick, False)

        log.info("[ROOMS] 🚪 Joined room %s nick=%s", room_jid, room_nick)

        bot.send_message(
            mto=target,
            mbody=f"🚪 Joined room: {room_jid}",
            mtype=mtype
        )
    except Exception:
        log.exception("[ROOMS] 🚪 Joining room %s nick=%s FAILED!",
                      room_jid, room_nick)
        bot.send_message(
            mto=target,
            mbody=f"🚪 Joining room FAILED: {room_jid}",
            mtype=mtype
        )


# -------------------------------------------------
# ROOMS LEAVE
# -------------------------------------------------

@command("rooms leave", role=Role.ADMIN, aliases=["room leave"])
async def rooms_leave(bot, sender_jid, nick, args, msg, is_room):
    """
    Leave a joined room.

    Command
    -------
    {prefix}rooms leave <room_jid>
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    if len(args) < 1:
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Usage: {bot.prefix}rooms leave <room_jid>",
            mtype=mtype
        )
        return

    room_jid = args[0]

    if not await is_valid_room_jid(bot, room_jid, target, mtype):
        bot.send_message(
            mto=target,
            mbody=f"⚠️ Invalid room JID: {room_jid}",
            mtype=mtype
        )
        log.warning(f"[ROOMS]⚠️Room '{room_jid}' not valid!")
        return

    try:
        muc = bot.plugin["xep_0045"]
        muc.leave_muc(room_jid, bot.boundjid.user)

        if room_jid in JOINED_ROOMS:
            del JOINED_ROOMS[room_jid]

        if room_jid in bot.presence.joined_rooms:
            del bot.presence.joined_rooms[room_jid]

        bot.presence.broadcast()

        log.info("[ROOMS] 🚶 Left room %s", room_jid)

        bot.send_message(
            mto=target,
            mbody=f"🚶 Left room: {room_jid}",
            mtype=mtype
        )

    except Exception:
        log.exception("[ROOMS] 🚶 Failed to leave room %s", room_jid)

        bot.send_message(
            mto=target,
            mbody=f"🚶 Failed to leave rooom: {room_jid}",
            mtype=mtype
        )


# -------------------------------------------------
# ROOMS SYNC
# -------------------------------------------------

@command("rooms sync", role=Role.ADMIN, aliases=["room sync"])
async def rooms_sync(bot, sender_jid, nick, args, msg, is_room):
    """
    Synchronize runtime rooms with database configuration.

    Command
    -------
    {prefix}rooms sync

    Description
    -----------
    Ensures that the bot's current room membership matches the
    configuration stored in the database.

    Actions performed
    -----------------
    • Leaves rooms joined by the bot but not stored in the database
    • Joins rooms that are configured with autojoin=true
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    try:
        rows = await bot.db.rooms.list()
        db_rooms = {r[0]: r for r in rows}
    except Exception:
        log.exception("[ROOMS] 🔄 Failed to get rooms from DB")

        bot.send_message(
            mto=target,
            mbody="🔄 Failed to get rooms from DB",
            mtype=mtype
        )
        return

    left = []
    joined = []

    muc = bot.plugin["xep_0045"]
    for room in JOINED_ROOMS:
        if room not in db_rooms:

            muc.leave_muc(room, bot.boundjid.user)

            del JOINED_ROOMS[room]

            if room in bot.presence.joined_rooms:
                del bot.presence.joined_rooms[room]

            left.append(room)

    for room_jid, nick_name, autojoin, status in rows:

        if autojoin and room_jid not in JOINED_ROOMS:

            muc = bot.plugin["xep_0045"]
            await muc.join_muc(room_jid, nick_name,
                               pshow=bot.presence.status['show'],
                               pstatus=bot.presence.status['status'])

            affiliation = muc.get_jid_property(room_jid,
                                               bot.boundjid.bare,
                                               "affiliation")
            JOINED_ROOMS[room_jid] = {
                "nick": nick_name,
                "autojoin": autojoin,
                "status": status,
                "affiliation": affiliation
            }
            bot.presence.joined_rooms[room_jid] = nick_name

            joined.append(room_jid)

    bot.presence.broadcast()

    log.info("[ROOMS] 🔄 Synchronization complete: joined=%d left=%d",
             len(joined), len(left))

    lines = ["🔄 Room synchronization complete"]

    if joined:
        lines.append("🚪 Joined:")
        lines.extend(joined)

    if left:
        lines.append("🚶 Left:")
        lines.extend(left)

    if not joined and not left:
        lines.append("ℹ️ No changes required.")

    bot.send_message(
        mto=target,
        mbody="\n".join(lines),
        mtype=mtype
    )


# -------------------------------------------------
# Rooms on_load function (Module autoloadind)
# -------------------------------------------------

async def on_load(bot):
    await autojoin_rooms(bot)

    async def on_muc_presence(pres):
        try:
            room = pres["muc"]["room"]
            nick = pres["muc"]["nick"]
        except KeyError:
            return

        # Only care about OUR OWN presence
        muc = bot.plugin.get("xep_0045", None)
        real_jid = None
        if muc:
            try:
                real_jid = muc.get_jid_property(room, nick, "jid")
            except Exception:
                pass
        if not real_jid:
            return
        if str(JID(real_jid).bare) != bot.boundjid.bare:
            return

        try:
            affiliation = muc.get_id_property(room, bot.boundjid.bare,
                                              "affiliation")
        except Exception:
            return

        if room in JOINED_ROOMS:
            old = JOINED_ROOMS[room].get("affiliation")
            if old != affiliation:
                JOINED_ROOMS[room]["affiliation"] = affiliation
                log.info(
                    "[ROOMS] 🔄 Affiliation updated: %s -> %s (%s)",
                    old, affiliation, room
                )

    bot.add_event_handler("groupchat_presence", on_muc_presence)
