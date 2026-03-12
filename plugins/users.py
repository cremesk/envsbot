"""
Users management plugin.

This plugin provides administrative commands for managing users
stored in the bot database.

Commands
--------
{prefix}users add <jid> [role] [nickname]
    Add a user to the database.

{prefix}users update <jid> <field> <value>
    Update a user field (role, nickname, banned).

{prefix}users delete <jid>
    Remove a user from the database.

{prefix}users list
    Show all stored users.

Notes
-----
Roles:
    1 = owner
    2 = admin
    3 = moderator
    4 = user
    5 = none
"""

import logging
from command import command

log = logging.getLogger(__name__)

PLUGIN_META = {
    "name": "users",
    "version": "1.0",
    "description": "Database user management"
}


ROLES = {
    "owner": 1,
    "admin": 2,
    "moderator": 3,
    "user": 4,
    "none": 5
}

ROLE_NAMES = {v: k for k, v in ROLES.items()}


@command("users", admins_only=True)
async def users_command(bot, sender_jid, nick, args, msg, is_room):
    """
    Manage users stored in the bot database.

    Usage
    -----
    {prefix}users add <jid> [role] [nickname]
    {prefix}users update <jid> <field> <value>
    {prefix}users delete <jid>
    {prefix}users list

    Examples
    --------
    {prefix}users add alice@example.org admin Alice
    {prefix}users update alice@example.org role moderator
    {prefix}users update alice@example.org banned true
    {prefix}users delete alice@example.org
    {prefix}users list
    """

    target = msg["from"].bare if is_room else msg["from"]
    mtype = "groupchat" if is_room else "chat"

    if not args:
        bot.send_message(
            mto=target,
            mbody="⚠️ Usage: users <add|update|delete|list>",
            mtype=mtype
        )
        return

    sub = args[0].lower()

    log.info("[USERS] 📥 Command from %s: %s", sender_jid, args)

    # --------------------------------------------------
    # ADD USER
    # --------------------------------------------------

    if sub == "add":

        if len(args) < 2:
            bot.send_message(
                mto=target,
                mbody="⚠️ Usage: users add <jid> [role] [nickname]",
                mtype=mtype
            )
            return

        jid = args[1]
        role = 5
        nickname = None

        if len(args) >= 3:
            role = ROLES.get(args[2].lower(), 5)

        if len(args) >= 4:
            nickname = args[3]

        await bot.db.users.add(
            jid,
            nickname=nickname,
            role=role
        )

        log.info("[USERS] ➕ Added user %s role=%s", jid, role)

        bot.send_message(
            mto=target,
            mbody=f"✅ User added: {jid}",
            mtype=mtype
        )

    # --------------------------------------------------
    # UPDATE USER
    # --------------------------------------------------

    elif sub == "update":

        if len(args) < 4:
            bot.send_message(
                mto=target,
                mbody="⚠️ Usage: users update <jid> <field> <value>",
                mtype=mtype
            )
            return

        jid = args[1]
        field = args[2].lower()
        value = args[3]

        if field == "role":
            value = ROLES.get(value.lower(), 5)

        if field == "banned":
            value = value.lower() in ["1", "true", "yes"]

        await bot.db.users.update(
            jid,
            **{field: value}
        )

        log.info("[USERS] 🔧 Updated %s: %s=%s", jid, field, value)

        bot.send_message(
            mto=target,
            mbody=f"🔧 User updated: {jid}",
            mtype=mtype
        )

    # --------------------------------------------------
    # DELETE USER
    # --------------------------------------------------

    elif sub == "delete":

        if len(args) < 2:
            bot.send_message(
                mto=target,
                mbody="⚠️ Usage: users delete <jid>",
                mtype=mtype
            )
            return

        jid = args[1]

        await bot.db.users.delete(jid)

        log.info("[USERS] 🗑️ Deleted user %s", jid)

        bot.send_message(
            mto=target,
            mbody=f"🗑️ User removed: {jid}",
            mtype=mtype
        )

    # --------------------------------------------------
    # LIST USERS
    # --------------------------------------------------

    elif sub == "list":

        async with bot.db.db.execute(
            "SELECT jid, nickname, role, banned FROM users"
        ) as cur:
            rows = await cur.fetchall()

        if not rows:

            log.info("[USERS] 📭 User list requested but database empty")

            bot.send_message(
                mto=target,
                mbody="ℹ️ No users in database.",
                mtype=mtype
            )
            return

        lines = ["📋 Stored users:"]

        for jid, nickname, role, banned in rows:

            role_name = ROLE_NAMES.get(role, role)
            banned_icon = "🚫" if banned else "✅"

            lines.append(
                f"{jid} | nick={nickname or '-'} | role={role_name} | {banned_icon}"
            )

        log.info("[USERS] 📄 Listed %d users", len(rows))

        bot.send_message(
            mto=target,
            mbody="\n".join(lines),
            mtype=mtype
        )

    else:

        log.warning("[USERS] ❌ Unknown subcommand: %s", sub)

        bot.send_message(
            mto=target,
            mbody="❌ Unknown subcommand.",
            mtype=mtype
        )
