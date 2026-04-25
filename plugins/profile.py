"""
Profile management plugin.

This plugin allows users to request the Fullname, Nicknames, Birthday, Notes,
Organisations and URLs from their own or others vCard (if public).

It also allows users to set their timezone, which is not supported by vCards.
"""

import slixmpp
from utils.command import command, Role
from utils.config import config
import pytz
import datetime
import re
import urllib.parse
import logging
from plugins.rooms import JOINED_ROOMS
from plugins.vcard import get_info

log = logging.getLogger(__name__)

PLUGIN_META = {
    "name": "profile",
    "version": "0.1.3",
    "description": "User profile management",
    "category": "info",
    "requires": ["vcard", "rooms"],
}


def resolve_real_jid(bot, msg, is_room):
    """
    Resolve the real sender JID in all contexts (groupchat, MUC PM, or DM).
    """
    jid = None
    muc = bot.plugin.get("xep_0045", None)
    if muc:
        room = msg['from'].bare
        nick = msg.get("mucnick") or msg["from"].resource
        jid = muc.get_jid_property(room, nick, "jid")
    if jid is None:
        jid = msg["from"]
    return str(slixmpp.JID(jid).bare)


async def _check_user_exists(bot, sender_jid, msg):
    """
    Check if the user exists in the database.

    Args:
        bot: The bot instance.
        sender_jid: The JID to check.
        msg: The message object.

    Returns:
        bool: True if user exists, False otherwise.
    """
    jid = str(sender_jid)
    user = await bot.db.users.get(jid)
    if not user:
        log.warning(
            "[PROFILE] 🔴  Unregistered user tried to use config: %s", jid
        )
        bot.reply(msg, "🔴  You are not a registered user.")
        return False
    return True


async def _unset_field(bot, jid, field_name, label, msg):
    """
    Helper to unset (clear) a profile field.

    Args:
        bot: The bot instance.
        jid: The user's JID.
        field_name: The field key (e.g., "FULLNAME").
        label: The display name (e.g., "Full Name").
        msg: The message object.
    """
    profile_store = bot.db.users.profile()
    await profile_store.set(str(jid), field_name, None)
    log.info("[PROFILE] 🗑️ %s unset for %s", field_name, jid)
    bot.reply(msg, f"🗑️ {label} removed.")


@command("timezone set", role=Role.USER, aliases=["tz set"])
async def set_timezone(bot, sender_jid, nick, args, msg, is_room):
    """
    Set your TIMEZONE in Linux format eg. for '{prefix}time [nick]' command.

    Usage:
        {prefix}timezone set <timezone>
        {prefix}tz set <timezone>

    Example:
        {prefix}timezone set Europe/Berlin
        {prefix}tz set Alaska/Anchorage
    """
    jid = resolve_real_jid(bot, msg, is_room)
    log.info("[PROFILE] ✅ set_timezone called by %s", jid)
    if not await _check_user_exists(bot, jid, msg):
        return
    if not args or len(args) != 1:
        log.warning("[PROFILE] 🔴  TIMEZONE missing/invalid args for %s",
                    jid)
        bot.reply(
            msg,
            f"🟡️ Usage: {config.get('prefix', ',')}config timezone "
            "<timezone>",
        )
        return
    timezone = args[0].strip()
    try:
        if timezone not in pytz.all_timezones:
            raise ValueError
    except Exception:
        log.warning("[PROFILE] 🔴  Invalid timezone for %s: %s", jid,
                    timezone)
        bot.reply(
            msg,
            "🟡️ Invalid timezone. Use a valid IANA timezone, "
            "e.g. Europe/Berlin.",
        )
        return
    profile_store = bot.db.users.profile()
    await profile_store.set(str(jid), "TIMEZONE", timezone)
    log.info("[PROFILE] ✅ TIMEZONE set for %s: %s", jid, timezone)
    bot.reply(msg, f"✅ TIMEZONE set to: {timezone}")


@command("config birthday", role=Role.USER, aliases=["c birthday"])
async def set_birthday(bot, sender_jid, nick, args, msg, is_room):
    """
    Set your BIRTHDAY in your profile. Format: YYYY-MM-DD or MM-DD.
    Birthday must not be in the future.

    Usage:
        {prefix}config birthday <YYYY-MM-DD|MM-DD>
        {prefix}c birthday <YYYY-MM-DD|MM-DD>

    Example:
        {prefix}config birthday 1990-05-23
        {prefix}config birthday 05-23
    """
    jid = resolve_real_jid(bot, msg, is_room)
    if not await _check_user_exists(bot, jid, msg):
        return
    if not args or len(args) != 1:
        bot.reply(
            msg,
            f"🟡️ Usage: {config.get('prefix', ',')}config birthday " +
            "<YYYY-MM-DD|MM-DD>",
        )
        return
    birthday = args[0].strip()
    if not (re.match(r"^\d{4}-\d{2}-\d{2}$", birthday)
            or re.match(r"^\d{2}-\d{2}$", birthday)):
        bot.reply(msg, "🟡️ Please provide birthday as YYYY-MM-DD or MM-DD.")
        return

    # Validate that birthday is not in the future
    today = datetime.date.today()
    try:
        if len(birthday) == 10:  # YYYY-MM-DD
            year = int(birthday[0:4])
            month = int(birthday[5:7])
            day = int(birthday[8:10])
            birthday_date = datetime.date(year, month, day)
            if birthday_date > today:
                bot.reply(msg, "🟡️ Birthday cannot be in the future.")
                return
        elif len(birthday) == 5:  # MM-DD
            month = int(birthday[0:2])
            day = int(birthday[3:5])
            # For MM-DD format, check if the date is valid but don't check future
            # (since we don't have year, we can't determine if it's in the future)
            try:
                datetime.date(today.year, month, day)
            except ValueError:
                bot.reply(msg, "🟡️ Invalid date.")
                return
    except ValueError:
        bot.reply(msg, "🟡️ Invalid date.")
        return

    profile_store = bot.db.users.profile()
    await profile_store.set(str(jid), "BIRTHDAY", birthday)
    log.info("[PROFILE] ✅ BIRTHDAY set for %s: %s", jid, birthday)
    bot.reply(msg, f"✅ BIRTHDAY set to: {birthday}")


@command("fullname", role=Role.USER, aliases=["f"])
async def get_fullname(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the FULLNAME of a user from their vCard.

    Usage:
        {prefix}fullname [nick]
        {prefix}f [nick]

    Example:
        {prefix}fullname Envsi
    """
    await _get_profile_field(bot, sender_jid, nick, args, msg, is_room,
                             "FN", "Full Name")

@command("nicknames", role=Role.USER, aliases=["nicks"])
async def get_nicknames(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the nicknames from a user's vCard.

    Usage:
        {prefix}nicknames [nick]
        {prefix}nicks [nick]

    Example:
        {prefix}nicknames Envsi
    """
    await _get_profile_field(bot, sender_jid, nick, args, msg, is_room,
                             "NICKNAME", "Nicknames")


@command("organisations", role=Role.USER, aliases=["orgs"])
async def get_organisations(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the organisations from a user's vCard.

    Usage:
        {prefix}organisations [nick]
        {prefix}orgs [nick]

    Example:
        {prefix}orgs Envsi
    """
    await _get_profile_field(bot, sender_jid, nick, args, msg, is_room,
                             "ORG", "Organisations")


@command("notes", role=Role.USER)
async def get_notes(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the notes from a user's vCard.

    Usage:
        {prefix}notes [nick]

    Example:
        {prefix}notes Envsi
    """
    await _get_profile_field(bot, sender_jid, nick, args, msg, is_room,
                             "NOTE", "Notes")


@command("email", role=Role.USER, aliases=["e"])
async def get_email(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the EMAIL of a user.

    Usage:
        {prefix}email [nick]
        {prefix}e [nick]

    Example:
        {prefix}email Envsi
    """
    await _get_profile_field(bot, sender_jid, nick, args, msg, is_room,
                             "EMAIL", "Emails")


@command("urls", role=Role.USER, aliases=["u"])
async def get_urls(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the URLS of a user.

    Usage:
        {prefix}urls [nick]
        {prefix}u [nick]

    Example:
        {prefix}urls Envsi
    """
    await _get_profile_field(bot, sender_jid, nick, args, msg, is_room,
                             "URL", "URLs")


# -------------------------------------------------
# Output of information (complex task)
# -------------------------------------------------

def _is_muc_pm(msg):
    return (
        msg.get("type") in ("chat", "normal")
        and hasattr(msg["from"], "bare")
        and "@" in str(msg["from"].bare)
        and str(msg["from"].bare) in JOINED_ROOMS
    )


async def _format_profile_field_for_nick(field, label, values,
                                        display_name, rooms=None):
    if field == "URL":
        lines = []
        if rooms:
            lines.append(f"{label} - {display_name} in {', '.join(rooms)}:")
        else:
            lines.append(f"{label} - {display_name}:")
        if values and isinstance(values, list):
            for v in values:
                lines.append(f"    • {urllib.parse.unquote(v)}")
        else:
            lines.append("    • —")
        return lines
    elif field in ["EMAIL", "NICKNAME", "ORG", "NOTE"]:
        lines = []
        if rooms:
            lines.append(f"{label} - {display_name} in {', '.join(rooms)}:")
        else:
            lines.append(f"{label} - {display_name}:")
        if values and isinstance(values, list):
            for v in values:
                lines.append(f"    • {v}")
        else:
            lines.append("    • —")
        return lines
    else:
        if values is None or values == "" or values == []:
            values = "—"
        if rooms:
            return [f"{label} - {display_name} in {', '.join(rooms)}: {values}"]
        else:
            return [f"{label} - {display_name}: {values}"]


async def _get_profile_field(bot, sender_jid, nick, args, msg, is_room,
                             field, label):
    """
    Helper to fetch and display a profile field for a user nick.
    """
    # 1. Room context (groupchat) or MUC PM: lookup nick in room
    if (is_room or _is_muc_pm(msg)) and args:
        target_nick = " ".join(args).strip()
        room = msg["from"].bare
        joined = JOINED_ROOMS.get(room, {})
        nicks = joined.get("nicks", {})
        nick_info = nicks.get(target_nick)
        if not nick_info:
            log.warning("[PROFILE] 🔴  Nick '%s' not found in room '%s'",
                        target_nick, room)
            bot.reply(msg, f"🔴  Nick '{target_nick}' not found in this room.")
            return
        _, vcard = await get_info(bot, msg, target_nick)
        if vcard[field] is None:
            log.warning("[PROFILE] 🔴  No vCard field '%s' for nick '%s' in room '%s'",
                        label, target_nick, room)
            bot.reply(msg, f"🔴  No {label} found in vCard for nick '{target_nick}'.")
            return
        display_name = target_nick
        value = vcard[field]
        log.info(f"[PROFILE] {sender_jid} looking up {field} for"
                 f"'{target_nick}'")
        if value is None or value == "" or value == []:
            log.warning("[PROFILE] 🔴  No %s for requested user '%s'",
                        field, target_nick)
            bot.reply(msg, f"ℹ️ No {label} set for nick '{args[0]}'.")
            return
        if field in ["FULLNAME", "BDAY", "URL", "NICKNAME", "ORG",
                     "NOTE", "EMAIL"]:
            lines = await _format_profile_field_for_nick(field, label,
                                                        vcard[field],
                                                        display_name,
                                                        [room])
            bot.reply(msg, lines)
        return
    # 2. Request own vCard information
    elif (is_room or _is_muc_pm(msg)) and not args:
        target_nick = msg["from"].resource
        room = msg["from"].bare
        joined = JOINED_ROOMS.get(room, {})
        nicks = joined.get("nicks", {})
        nick_info = nicks.get(target_nick)
        if not nick_info:
            log.warning("[PROFILE] 🔴  Nick '%s' not found in room '%s'",
                        target_nick, room)
            bot.reply(msg, f"🔴  Your Nick '{target_nick}' not found in this room.")
            return
        _, vcard = await get_info(bot, msg, target_nick)
        if vcard[field] is None:
            log.warning("[PROFILE] 🔴  No vCard field '%s' for nick '%s' in room '%s'",
                        label, target_nick, room)
            bot.reply(msg, f"🔴  No {label} found in vCard for nick '{target_nick}'.")
            return
        display_name = target_nick
        value = vcard[field]
        log.info(f"[PROFILE] {sender_jid} looking up {field} for"
                 f"'{target_nick}'")
        if value is None or value == "" or value == []:
            log.warning("[PROFILE] 🔴  No %s for requested user '%s'",
                        field, target_nick)
            bot.reply(msg, f"ℹ️ No {label} set for nick '{args[0]}'.")
            return
        if field in ["FULLNAME", "BDAY", "URL", "NICKNAME", "ORG",
                     "NOTE", "EMAIL"]:
            lines = await _format_profile_field_for_nick(field, label,
                                                        vcard[field],
                                                        display_name,
                                                        [room])
            bot.reply(msg, lines)

        else:
            bot.reply(msg, f"{label} for {display_name}: {value}")
        return

    # 2. Direct message to bot JID: lookup nick globally, group by JID/rooms
    else:
        bot.reply(msg, "🔴 Please use this command in a room or MUC PM.")
        log.warning("[PROFILE] 🔴  Command used outside of room/MUC PM by %s",
                    sender_jid)
        return


@command("birthday", role=Role.USER, aliases=["b"])
async def get_birthday(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the BIRTHDAY of a user and days until next birthday from their vCard.

    Usage:
        {prefix}birthday [nick]
        {prefix}b [nick]
    Example:
        {prefix}birthday Envsi
    """
    # 1. Room context (groupchat) or MUC PM: lookup nick in room
    if (is_room or _is_muc_pm(msg)) and args:
        target_nick = " ".join(args).strip()
        room = msg["from"].bare
        joined = JOINED_ROOMS.get(room, {})
        nicks = joined.get("nicks", {})
        nick_info = nicks.get(target_nick)
        if not nick_info:
            bot.reply(msg, f"🔴  Nick '{target_nick}' not found in this room.")
            return
        display_name = target_nick
    elif (is_room or _is_muc_pm(msg)) and not args:
        target_nick = msg["from"].resource
        room = msg["from"].bare
        joined = JOINED_ROOMS.get(room, {})
        nicks = joined.get("nicks", {})
        nick_info = nicks.get(target_nick)
        if not nick_info:
            bot.reply(msg, f"🔴  Your Nick '{target_nick}' not found in this room.")
            return
        display_name = target_nick
    else:
        display_name = msg["from"].resource or nick
        bot.reply(msg, "🔴 Please use this command in a room or MUC PM.")
        log.warning("[PROFILE] 🔴  Command used outside of room/MUC PM by %s",
                    display_name)
        return

    _, vcard = await get_info(bot, msg, target_nick)
    value = None
    if vcard.get("BDAY"):
        value = vcard["BDAY"]
    if value is None or value == "" or value == []:
        bot.reply(msg, f"ℹ️ No Birthday set for {display_name}.")
        return

    # Calculate days until next birthday
    today = datetime.date.today()
    try:
        if len(value) == 10:  # YYYY-MM-DD
            month = int(value[5:7])
            day = int(value[8:10])
        elif len(value) == 5:  # MM-DD
            month = int(value[0:2])
            day = int(value[3:5])
        else:
            raise ValueError
        this_year = today.year
        next_birthday = datetime.date(this_year, month, day)
        if next_birthday < today:
            next_birthday = datetime.date(this_year + 1, month, day)
        days_left = (next_birthday - today).days
        days_str = f"{days_left} day{'s' if days_left != 1 else ''}"
        bot.reply(msg, f"🎂 Birthday for {display_name}: {value}"
                       + f" ({days_str} until next birthday)")
    except Exception:
        bot.reply(msg, f"🎂 Birthday for {display_name}: {value}")


@command("config unset", role=Role.USER, aliases=["c unset"])
async def unset_field(bot, sender_jid, nick, args, msg, is_room):
    """
    Unset (clear) a profile field from the bots database.

    Usage:
        {prefix}config unset <field>
        {prefix}c unset <field>

    Available fields:
        fullname, location, timezone, birthday, pronouns, species, email, urls

    Example:
        {prefix}config unset fullname
        {prefix}config unset birthday
    """
    jid = resolve_real_jid(bot, msg, is_room)
    if not await _check_user_exists(bot, jid, msg):
        return

    if not args or len(args) != 1:
        log.warning("[PROFILE] 🔴  UNSET missing/invalid args for %s", jid)
        bot.reply(
            msg,
            f"🟡️ Usage: {config.get('prefix', ',')}config unset "
            "<field>\n"
            "Available fields: fullname, location, timezone, birthday, "
            "pronouns, species, email, urls",
        )
        return

    field_arg = args[0].lower().strip()

    field_map = {
        "fullname": ("FULLNAME", "Full Name"),
        "location": ("LOCATION", "Location"),
        "timezone": ("TIMEZONE", "Timezone"),
        "birthday": ("BIRTHDAY", "Birthday"),
        "pronouns": ("PRONOUNS", "Pronouns"),
        "species": ("SPECIES", "Species"),
        "email": ("EMAIL", "Email"),
        "urls": ("URLS", "URLs"),
    }

    if field_arg not in field_map:
        log.warning("[PROFILE] 🔴  Invalid field for unset for %s: %s",
                    jid, field_arg)
        bot.reply(
            msg,
            f"🟡️ Unknown field '{field_arg}'.\n"
            "Available fields: fullname, location, timezone, birthday, "
            "pronouns, species, email, urls",
        )
        return

    field_name, label = field_map[field_arg]
    await _unset_field(bot, jid, field_name, label, msg)
