"""
vCard Lookup Plugin

Command: {prefix}vcard <nick>
Look up the vCard for a user by MUC nick (using only the MUC JID).

- Only available in groupchats or MUC PMs.
- Only uses the MUC JID (nick@room), never the real JID!
- Never displays or logs the user's real JID.
"""

import logging
import textwrap
# from xml.etree import ElementTree as ET
from utils.command import command, Role
from plugins.rooms import JOINED_ROOMS
from utils.plugin_helper import handle_room_toggle_command

VCARD_KEY = "VCARD"

PLUGIN_META = {
    "name": "vcard",
    "version": "0.2.1",
    "description": "Lookup and display vCard of a MUC occupant by MUC JID only",
    "category": "info",
    "requires": ["rooms"],
}

log = logging.getLogger(__name__)


def _is_muc_pm(msg):
    """Returns True if msg is a MUC direct message (not public groupchat)."""
    return (
        msg.get("type") in ("chat", "normal")
        and hasattr(msg["from"], "bare")
        and "@" in str(msg["from"].bare)
        and str(msg["from"].bare) in JOINED_ROOMS
    )


async def get_vcard(bot, msg, target_nick):
    """
    Helper function to fetch vCard for a given JID using the xep_0054 plugin.
    """
    room = msg["from"].bare  # MUC JID
    joined = JOINED_ROOMS.get(room, {})
    nicks = joined.get("nicks", {})
    if target_nick not in nicks:
        log.info(f"[VCARD] Lookup failed: Nick '{target_nick}' not found in room {room}")
        return None

    muc_jid = f"{room}/{target_nick}"
    log.info(f"[VCARD] Attempting vCard lookup for nick '{target_nick}' with MUC JID '{muc_jid}' in room '{room}'")

    try:
        vcard_plugin = bot.plugin.get("xep_0054", None)
        if not vcard_plugin:
            raise RuntimeError("vCard support (xep_0054) is not enabled in this bot.")
        result = await vcard_plugin.get_vcard(jid=muc_jid, cached=False, timeout=10)
        if not result:
            return None
        return result["vcard_temp"]
    except Exception as e:
        log.error(f"[VCARD] Exception during vCard lookup for '{target_nick}' ({muc_jid}): {e}")
        raise


async def get_info(bot, msg, target_nick):
    muc_jid = msg["from"].bare
    try:
        vcard_info = await get_vcard(bot, msg, target_nick)
        if not vcard_info:
            bot.reply(msg, f"ℹ️ No vCard found for {target_nick}.")
            log.info(f"[VCARD] No vCard found for '{target_nick}'.")
            return None, None

        log.info(f"[VCARD] vCard for '{target_nick}' (never real jid!) received.")
        _, vcard = _format_vcard_reply(vcard_info, target_nick, muc_jid)
        log.info(f"[VCARD] vCard for '{target_nick}': {vcard}")

    except Exception as e:
        bot.reply(msg, f"🔴 Failed to fetch vCard for {target_nick}: {e}")
        log.error(f"[VCARD] Exception during vCard lookup for '{target_nick}': {e}")
        return None, None
    if not vcard:
        log.warning(f"[WEATHER] Lookup failed: No vCard found for sender's nick '{target_nick}'.")
        bot.reply(msg, f"🔴  Your vcard for '{target_nick}' not found in this room.")
        return None, None
    return target_nick, vcard


def _get_all_field_values_by_tag(vcard, tag):
    """
    Extract all string values for the field 'tag' from vcard stanza children.
    """
    values = []
    for child in vcard.xml:
        # Check both namespace-tag form and plain tag
        if child.tag.endswith(tag) and child.text:
            values.append(child.text.strip())
    return values


def _get_nested_field_values_by_tag(vcard, parent_tag, child_tag):
    """Get all child_tag values under parent_tag elements in vcard XML."""
    values = []
    for field in vcard.xml:
        if field.tag.endswith(parent_tag):
            for child in field:
                if child.tag.endswith(child_tag) and child.text:
                    values.append(child.text.strip())
    return values


def _extract_email_addresses(vcard):
    """Extract USERID from all EMAIL fields in the vCard XML."""
    emails = []
    for child in vcard.xml:
        if child.tag.endswith("EMAIL"):
            # Find USERID child element within the EMAIL
            for email_child in child:
                if email_child.tag.endswith("USERID") and email_child.text:
                    # find USERID element and extract email address
                    for email_child in child:
                        if (email_child.tag.endswith("USERID")
                                and email_child.text):
                            emails.append(email_child.text.strip())
    return emails


def _format_vcard_reply(vcard, nick, muc_jid):
    # log vcard.xml to file
    # log.info("[VCARD] Raw vCard XML: %s",
    #          ET.tostring(vcard.xml, encoding="unicode"))
    c = {}
    lines = [f"📄 vCard for {nick} ({muc_jid}):"]

    fn = vcard.get("FN")
    c["FN"] = None
    if fn:
        lines.append(f"• Name: {fn}")
        c["FN"] = fn
    nicknames = _get_all_field_values_by_tag(vcard, "NICKNAME")
    c["NICKNAME"] = []
    if nicknames:
        lines.append(f"• Nicknames: {nicknames}")
        c["NICKNAME"] = nicknames
    bday = vcard.get("BDAY")
    if bday:
        lines.append(f"• Birthday: {bday}")
        c["BDAY"] = bday

    # All URLs
    c["URL"] = []
    urls = _get_all_field_values_by_tag(vcard, "URL")
    if urls:
        lines.append("")
        c["URL"] = urls
    for url in urls:
        lines.append(f"• URL: {url}")

    c["ORG"] = []
    org_names = _get_nested_field_values_by_tag(vcard, "ORG", "ORGNAME")
    if org_names:
        lines.append("")
        for org in org_names:
            lines.append(f"• Organization: {org}")
            c["ORG"].append(org)

    # All Notes with wrapping
    c["NOTE"] = []
    notes = _get_all_field_values_by_tag(vcard, "NOTE")
    if notes:
        lines.append("")
        c["NOTE"] = notes
    for note in notes:
        wrapped = textwrap.fill(
            note,
            width=70,
            initial_indent="• Note: ",
            subsequent_indent="        "
        )
        lines.append(wrapped)

    # Multiple emails support
    c["EMAIL"] = []
    emails = _extract_email_addresses(vcard)
    if emails:
        lines.append("")
        c["EMAIL"] = emails
        for email_addr in emails:
            lines.append(f"• Email: {email_addr}")

    adr = vcard.get("ADR")
    c["LOCALITY"] = None
    c["CTRY"] = None
    if adr:
        locality = adr.get("LOCALITY")
        if locality:
            lines.append("")  # Blank line before address
            c["LOCALITY"] = locality
        ctry = adr.get("CTRY")
        c["CTRY"] = ctry
        vals = [val for val in (locality, ctry) if val]
        if vals:
            lines.append(f"• Address: {' '.join(vals)}")

    if len(lines) == 1:
        lines.append("  (no public vCard fields found)")
    return lines, c


async def get_vcard_store(bot):
    return bot.db.users.plugin("vcard")


@command("vcard", role=Role.USER, aliases=["v"])
async def vcard_command(bot, sender_jid, sender_nick, args, msg, is_room):
    """
    Look up the vCard of a user by MUC nick (MUC JID only), never real JID!

    Usage: {prefix}vcard <nick>
    Only available in groupchats or MUC DMs, and only for nicks present in
    this room.
    """

    handled = await handle_room_toggle_command(
        bot,
        msg,
        is_room,
        args,
        store_getter=get_vcard_store,
        key=VCARD_KEY,
        label="Get weather",
        storage="dict",
        log_prefix="[VCARD]",
    )
    if handled:
        return

    store = await get_vcard_store(bot)
    enabled_rooms = await store.get_global(VCARD_KEY, default={})
    if not (is_room or _is_muc_pm(msg)):
        bot.reply(msg, "🔴 This command is only available in groupchats or MUC DMs.")
        return

    if not args:
        muc_jid = msg["from"].bare
        target_nick = sender_nick

        if muc_jid not in enabled_rooms:
            return
    else:
        target_nick = " ".join(args).strip()
        muc_jid = f"{msg['from'].bare}"

        if muc_jid not in enabled_rooms:
            return

    try:
        vcard = await get_vcard(bot, msg, target_nick)
        if not vcard:
            bot.reply(msg, f"ℹ️ No vCard found for {target_nick} ({muc_jid}).")
            log.info(f"[VCARD] No vCard found for '{target_nick}' ({muc_jid})")
            return

        lines, _ = _format_vcard_reply(vcard, target_nick, muc_jid)
        bot.reply(msg, lines)
        log.info(f"[VCARD] vCard for '{target_nick}' ({muc_jid}) sent (never real jid!).")
    except Exception as e:
        bot.reply(msg, f"🔴 Failed to fetch vCard for {target_nick}: {e}")
        log.error(f"[VCARD] Exception during vCard lookup for '{target_nick}' ({muc_jid}): {e}")
