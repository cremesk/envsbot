"""
Rooms management plugin.

This plugin allows administrators to manage XMPP rooms stored
in the bot database and control room presence at runtime.
"""

import logging
from command import command

log = logging.getLogger(__name__)

PLUGIN_META = {
    "name": "rooms",
    "version": "1.2",
    "description": "Database room management"
}


@command("rooms", admins_only=True)
async def rooms_command(bot, sender_jid, nick, args, msg, is_room):
    """
    Manage XMPP rooms stored in the database.

    Usage
    -----
    {prefix}rooms add <room_jid> <nick> [autojoin]
        Add a room to the database.
    {prefix}rooms update <room_jid> <field> <value>
        Update a room field.
    {prefix}rooms delete <room_jid>
        Remove a room from the database.
    {prefix}rooms list
        List all stored rooms.
    {prefix}rooms join <room_jid> [nick]
        Join a room immediately.
    {prefix}rooms leave <room_jid>
        Leave a room immediately.

    Fields
    ------
    nick
        Nickname used by the bot inside the room.
    autojoin
        Whether the bot automatically joins the room on startup.
    status
        Optional informational status text.

    Examples
    --------
    {prefix}rooms add room@conference.example.org BotNick true
    {prefix}rooms update room@conference.example.org autojoin false
    {prefix}rooms update room@conference.example.org nick ServiceBot
    {prefix}rooms delete room@conference.example.org
    {prefix}rooms join room@conference.example.org
    {prefix}rooms leave room@conference.example.org
    {prefix}rooms list
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    if not args:
        bot.send_message(
            mto=target,
            mbody="⚠️ Usage: rooms <add|update|delete|list|join|leave>",
            mtype=mtype
        )
        return

    sub = args[0].lower()

    log.info("[ROOMS] 📥 Command from %s: %s", sender_jid, args)

    # --------------------------------------------------
    # ADD
    # --------------------------------------------------

    if sub == "add":

        if len(args) < 3:
            bot.send_message(
                mto=target,
                mbody="⚠️ Usage: rooms add <room_jid> <nick> [autojoin]",
                mtype=mtype
            )
            return

        room_jid = args[1]
        room_nick = args[2]
        autojoin = False

        if len(args) >= 4:
            autojoin = args[3].lower() in ["1", "true", "yes"]

        await bot.db.rooms.add(room_jid, room_nick, autojoin=autojoin)

        log.info("[ROOMS] ➕ Added room %s nick=%s autojoin=%s",
                 room_jid, room_nick, autojoin)

        bot.send_message(
            mto=target,
            mbody=f"✅ Room added: {room_jid}",
            mtype=mtype
        )

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------

    elif sub == "update":

        if len(args) < 4:
            bot.send_message(
                mto=target,
                mbody="⚠️ Usage: rooms update <room_jid> <field> <value>",
                mtype=mtype
            )
            return

        room_jid = args[1]
        field = args[2].lower()
        value = args[3]

        if field == "autojoin":
            value = value.lower() in ["1", "true", "yes"]

        await bot.db.rooms.update(room_jid, **{field: value})

        log.info("[ROOMS] 🔧 Updated %s: %s=%s", room_jid, field, value)

        bot.send_message(
            mto=target,
            mbody=f"🔧 Room updated: {room_jid}",
            mtype=mtype
        )

    # --------------------------------------------------
    # DELETE
    # --------------------------------------------------

    elif sub == "delete":

        if len(args) < 2:
            bot.send_message(
                mto=target,
                mbody="⚠️ Usage: rooms delete <room_jid>",
                mtype=mtype
            )
            return

        room_jid = args[1]

        await bot.db.rooms.delete(room_jid)

        log.info("[ROOMS] 🗑️ Deleted room %s", room_jid)

        bot.send_message(
            mto=target,
            mbody=f"🗑️ Room removed: {room_jid}",
            mtype=mtype
        )

    # --------------------------------------------------
    # LIST
    # --------------------------------------------------

    elif sub == "list":

        rows = await bot.db.rooms.list()

        if not rows:

            log.info("[ROOMS] 📭 Room list requested but database empty")

            bot.send_message(
                mto=target,
                mbody="ℹ️ No rooms stored.",
                mtype=mtype
            )
            return

        lines = ["📋 Stored rooms:"]

        for room_jid, room_nick, autojoin, status in rows:

            autojoin_icon = "✅" if autojoin else "❌"

            lines.append(
                f"- {room_jid} | nick: {room_nick} | "
                + f"autojoin: {autojoin_icon} | status: {status or '-'}"
            )

        log.info("[ROOMS] 📄 Listed %d rooms", len(rows))

        bot.send_message(
            mto=target,
            mbody="\n".join(lines),
            mtype=mtype
        )

    # --------------------------------------------------
    # JOIN
    # --------------------------------------------------

    elif sub == "join":

        if len(args) < 2:
            bot.send_message(
                mto=target,
                mbody="⚠️ Usage: rooms join <room_jid> [nick]",
                mtype=mtype
            )
            return

        room_jid = args[1]

        if len(args) >= 3:
            room_nick = args[2]
        else:
            room = await bot.db.rooms.get(room_jid)
            room_nick = room[1] if room else bot.boundjid.user

        bot.plugin["xep_0045"].join_muc(room_jid, room_nick)

        if room_jid not in bot.rooms:
            bot.rooms.append(room_jid)
        bot.presence.joined_rooms[room_jid] = room_nick
        bot.presence.broadcast()

        log.info("[ROOMS] 🚪 Joined room %s nick=%s", room_jid, room_nick)

        bot.send_message(
            mto=target,
            mbody=f"🚪 Joined room: {room_jid}",
            mtype=mtype
        )

    # --------------------------------------------------
    # LEAVE
    # --------------------------------------------------

    elif sub == "leave":

        if len(args) < 2:
            bot.send_message(
                mto=target,
                mbody="⚠️ Usage: rooms leave <room_jid>",
                mtype=mtype
            )
            return

        room_jid = args[1]

        bot.plugin["xep_0045"].leave_muc(room_jid, bot.boundjid.user)

        if room_jid in bot.rooms:
            bot.rooms.remove(room_jid)

        log.info("[ROOMS] 🚶 Left room %s", room_jid)

        bot.send_message(
            mto=target,
            mbody=f"🚶 Left room: {room_jid}",
            mtype=mtype
        )

    else:

        log.warning("[ROOMS] ❌ Unknown subcommand: %s", sub)

        bot.send_message(
            mto=target,
            mbody="❌ Unknown subcommand.",
            mtype=mtype
        )
