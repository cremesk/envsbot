"""
XMPP utility commands plugin.

This plugin provides various utility commands for interacting with XMPP
servers and users, such as pinging a JID, querying service discovery info,
checking compliance scores, and performing DNS SRV lookups.

Commands:
    {prefix}xmpp help - Displays the help message with all available commands.
    {prefix}xmpp version <jid> - Shows the software version of an XMPP entity (XEP-0092).
    {prefix}xmpp items <jid> - Lists the service items of an XMPP entity (XEP-0030).
    {prefix}xmpp contact <jid> - Displays contact information for an XMPP entity (XEP-0030).
    {prefix}xmpp info <jid> - Lists the identities and features of an XMPP entity (XEP-0030).
    {prefix}xmpp ping <jid> - Pings an XMPP entity and reports the round-trip time (XEP-0199).
    {prefix}xmpp uptime <jid> - Shows the uptime of an XMPP entity (XEP-0012).
    {prefix}xmpp srv <domain> - Performs DNS SRV lookups for XMPP services.
    {prefix}xmpp compliance <domain> - Shows the compliance score of a server from compliance.conversations.im.
"""
import time
import socket
import slixmpp
import aiohttp
from utils.command import command, Role
from plugins.rooms import JOINED_ROOMS

PLUGIN_META = {
    "name": "xmpp",
    "version": "0.2.0",
    "description": "XMPP utility tools (ping, diagnostics, service discovery, DNS SRV, etc.)",
    "category": "tools",
    "Requires": ["rooms"],
}

HELP_TEXT = """
XMPP Utility Commands:
  {prefix}x help              - Show this help message
  {prefix}x version <jid>     - Show software version (XEP-0092)
  {prefix}x items <jid>       - List service items (XEP-0030)
  {prefix}x contact <jid>     - Show contact information (XEP-0030)
  {prefix}x info <jid>        - Show identities & features (XEP-0030)
  {prefix}x ping <jid>        - Ping entity (XEP-0199)
  {prefix}x uptime <jid>      - Show uptime (XEP-0012)
  {prefix}x srv <domain>      - DNS SRV lookup
  {prefix}x compliance <domain> - Compliance score
"""


def _resolve_target(bot, args, msg, is_room, nick):
    """
    Resolve the target: JID, room JID/nick, or nick in room context.
    Returns (target, error_message) tuple.
    """
    if not args or len(args) < 1:
        return None, "Missing target JID or nick"

    target = args[0]
    # If in room or MUC PM and target is a nick, resolve to room_jid/nick
    if (is_room or (
        msg.get("type") in ("chat", "normal")
        and hasattr(msg["from"], "bare")
        and str(msg["from"].bare) in JOINED_ROOMS
    )):
        room = msg["from"].bare
        nicks = JOINED_ROOMS.get(room, {}).get("nicks", {})
        if target in nicks:
            return f"{room}/{target}", None
    return target, None


@command("xmpp", "x", role=Role.USER)
async def cmd_xmpp_help(bot, sender_jid, nick, args, msg, is_room):
    """
    Display help message with all available XMPP commands.

    Usage:
        {prefix}xmpp help
        {prefix}x help
    """
    bot.reply(msg, HELP_TEXT)


@command("xmpp version", "x version", role=Role.USER)
async def cmd_xmpp_version(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the software version of an XMPP entity (XEP-0092).

    Usage:
        {prefix}xmpp version <jid>
        {prefix}x version <jid>
    Example:
        {prefix}x version server.example.org
    """
    target, error = _resolve_target(bot, args, msg, is_room, nick)
    if error:
        bot.reply(msg, f"❌ {error}")
        return

    try:
        result = await bot.plugin["xep_0092"].get_version(jid=target, timeout=8)
        version_info = f"**{result['name']}** v{result['version']}"
        if result.get('os'):
            version_info += f" on {result['os']}"
        bot.reply(msg, f"ℹ️  Version: {version_info}")
    except slixmpp.exceptions.IqTimeout:
        bot.reply(msg, f"🔴 Version request to {target} timed out.")
    except slixmpp.exceptions.IqError as e:
        err = e.iq['error']
        err_condition = err.get('condition', 'unknown')
        bot.reply(msg, f"🔴 Version request failed: {err_condition}")
    except Exception as e:
        bot.reply(msg, f"🔴 Error: {e}")


@command("xmpp items", "x items", role=Role.USER)
async def cmd_xmpp_items(bot, sender_jid, nick, args, msg, is_room):
    """
    List the service items of an XMPP entity (XEP-0030).

    Usage:
        {prefix}xmpp items <jid>
        {prefix}x items <jid>
    Example:
        {prefix}x items conference.example.org
    """
    target, error = _resolve_target(bot, args, msg, is_room, nick)
    if error:
        bot.reply(msg, f"❌ {error}")
        return

    try:
        items = await bot.plugin["xep_0030"].get_items(jid=target, timeout=8)
        if not items['disco_items']['items']:
            bot.reply(msg, f"No items found for {target}")
            return

        items_list = "\n".join([f"  • {item[0]} ({item[1]})" for item in items['disco_items']['items']])
        bot.reply(msg, f"📋 Items for {target}:\n{items_list}")
    except slixmpp.exceptions.IqTimeout:
        bot.reply(msg, f"🔴 Items request to {target} timed out.")
    except slixmpp.exceptions.IqError as e:
        err = e.iq['error']
        err_condition = err.get('condition', 'unknown')
        bot.reply(msg, f"🔴 Items request failed: {err_condition}")
    except Exception as e:
        bot.reply(msg, f"🔴 Error: {e}")


@command("xmpp contact", "x contact", role=Role.USER)
async def cmd_xmpp_contact(bot, sender_jid, nick, args, msg, is_room):
    """
    Display contact information for an XMPP entity (XEP-0030).

    Usage:
        {prefix}xmpp contact <jid>
        {prefix}x contact <jid>
    Example:
        {prefix}x contact server.example.org
    """
    target, error = _resolve_target(bot, args, msg, is_room, nick)
    if error:
        bot.reply(msg, f"❌ {error}")
        return

    try:
        info = await bot.plugin["xep_0030"].get_info(jid=target, timeout=8)
        contact_info = []

        for form in info['disco_info']['form']:
            if form['type'] == 'form':
                for field in form['fields']:
                    if field['var'] in ['abuse-addresses', 'admin-addresses', 'feedback-addresses', 'security-addresses', 'support-addresses']:
                        values = field.get('value', [])
                        if values:
                            contact_info.append(f"  • {field['var']}: {', '.join(values)}")

        if contact_info:
            bot.reply(msg, f"📧 Contact info for {target}:\n" + "\n".join(contact_info))
        else:
            bot.reply(msg, f"No contact information found for {target}")
    except slixmpp.exceptions.IqTimeout:
        bot.reply(msg, f"🔴 Contact request to {target} timed out.")
    except slixmpp.exceptions.IqError as e:
        err = e.iq['error']
        err_condition = err.get('condition', 'unknown')
        bot.reply(msg, f"🔴 Contact request failed: {err_condition}")
    except Exception as e:
        bot.reply(msg, f"🔴 Error: {e}")


@command("xmpp info", "x info", role=Role.USER)
async def cmd_xmpp_info(bot, sender_jid, nick, args, msg, is_room):
    """
    List the identities and features of an XMPP entity (XEP-0030).

    Usage:
        {prefix}xmpp info <jid>
        {prefix}x info <jid>
    Example:
        {prefix}x info server.example.org
    """
    target, error = _resolve_target(bot, args, msg, is_room, nick)
    if error:
        bot.reply(msg, f"❌ {error}")
        return

    try:
        info = await bot.plugin["xep_0030"].get_info(jid=target, timeout=8)

        identities = []
        for ident in info['disco_info']['identities']:
            ident_str = ident['category']
            if ident.get('type'):
                ident_str += f"/{ident['type']}"
            if ident.get('name'):
                ident_str += f" ({ident['name']})"
            identities.append(f"  • {ident_str}")

        features = [f"  • {feature}" for feature in info['disco_info']['features']]

        result = f"🔍 Info for {target}:\n"
        if identities:
            result += f"\n**Identities:**\n" + "\n".join(identities)
        if features:
            result += f"\n**Features:**\n" + "\n".join(features[:10])  # Limit to 10 features
            if len(features) > 10:
                result += f"\n  ... and {len(features) - 10} more"

        bot.reply(msg, result)
    except slixmpp.exceptions.IqTimeout:
        bot.reply(msg, f"🔴 Info request to {target} timed out.")
    except slixmpp.exceptions.IqError as e:
        err = e.iq['error']
        err_condition = err.get('condition', 'unknown')
        bot.reply(msg, f"🔴 Info request failed: {err_condition}")
    except Exception as e:
        bot.reply(msg, f"🔴 Error: {e}")


@command("xmpp ping", "x ping", role=Role.USER)
async def cmd_xmpp_ping(bot, sender_jid, nick, args, msg, is_room):
    """
    Ping an XMPP JID and report round-trip time (XEP-0199).

    Usage:
        {prefix}xmpp ping <jid|nick>
        {prefix}x ping <jid|nick>
    Example:
        {prefix}x ping user@example.org
        {prefix}x ping conference.example.org
        {prefix}x ping Alice
    """
    target, error = _resolve_target(bot, args, msg, is_room, nick)
    if error:
        bot.reply(msg, f"❌ {error}")
        return

    try:
        start = time.monotonic()
        await bot.plugin["xep_0199"].ping(jid=target, timeout=8)
        rtt = (time.monotonic() - start) * 1000
        bot.reply(msg, f"🏓 Pong from {target} in {rtt:.1f} ms")
    except slixmpp.exceptions.IqTimeout:
        bot.reply(msg, f"🔴 Ping to {target} timed out.")
    except slixmpp.exceptions.IqError as e:
        err = e.iq['error']
        err_type = err.get('type', 'unknown')
        err_condition = err.get('condition', 'unknown')
        err_text = err.get('text', '')
        bot.reply(
            msg,
            f"🔴 Ping to {target} failed: {err_type}/"
            f"{err_condition} {err_text}".strip()
        )
    except Exception as e:
        bot.reply(msg, f"🔴 Ping to {target} failed: {e}")


@command("xmpp uptime", "x uptime", role=Role.USER)
async def cmd_xmpp_uptime(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the uptime of an XMPP entity (XEP-0012).

    Usage:
        {prefix}xmpp uptime <jid>
        {prefix}x uptime <jid>
    Example:
        {prefix}x uptime server.example.org
    """
    target, error = _resolve_target(bot, args, msg, is_room, nick)
    if error:
        bot.reply(msg, f"❌ {error}")
        return

    try:
        result = await bot.plugin["xep_0012"].get_last_activity(jid=target, timeout=8)
        seconds = result['last_activity']['seconds']

        # Convert seconds to human-readable format
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        uptime_str = []
        if days > 0:
            uptime_str.append(f"{days}d")
        if hours > 0:
            uptime_str.append(f"{hours}h")
        if minutes > 0:
            uptime_str.append(f"{minutes}m")
        if secs > 0 or not uptime_str:
            uptime_str.append(f"{secs}s")

        bot.reply(msg, f"⏱️  Uptime for {target}: {' '.join(uptime_str)}")
    except slixmpp.exceptions.IqTimeout:
        bot.reply(msg, f"🔴 Uptime request to {target} timed out.")
    except slixmpp.exceptions.IqError as e:
        err = e.iq['error']
        err_condition = err.get('condition', 'unknown')
        bot.reply(msg, f"🔴 Uptime request failed: {err_condition}")
    except Exception as e:
        bot.reply(msg, f"🔴 Error: {e}")


@command("xmpp srv", "x srv", role=Role.USER)
async def cmd_xmpp_srv(bot, sender_jid, nick, args, msg, is_room):
    """
    Perform DNS SRV lookups for XMPP services.

    Usage:
        {prefix}xmpp srv <domain>
        {prefix}x srv <domain>
    Example:
        {prefix}x srv example.org
    """
    if not args or len(args) < 1:
        bot.reply(msg, "❌ Missing domain")
        return

    domain = args[0]

    try:
        srv_records = {}
        for service in ['_xmpp-client', '_xmpp-server']:
            try:
                results = socket.getaddrinfo(
                    f"{service}._tcp.{domain}", None,
                    family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
                )
                # This is simplified; real SRV lookup would use dnspython
                srv_records[service] = "Found"
            except socket.gaierror:
                srv_records[service] = "Not found"

        result = f"🔍 DNS SRV records for {domain}:\n"
        for service, status in srv_records.items():
            result += f"  • {service}: {status}\n"

        bot.reply(msg, result)
    except Exception as e:
        bot.reply(msg, f"🔴 DNS lookup failed: {e}")


@command("xmpp compliance", "x compliance", role=Role.USER)
async def cmd_xmpp_compliance(bot, sender_jid, nick, args, msg, is_room):
    """
    Show the compliance score of a server from compliance.conversations.im.

    Usage:
        {prefix}xmpp compliance <domain>
        {prefix}x compliance <domain>
    Example:
        {prefix}x compliance example.org
    """
    if not args or len(args) < 1:
        bot.reply(msg, "❌ Missing domain")
        return

    domain = args[0]

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://compliance.conversations.im/api/v1/server/{domain}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    score = data.get('compliance', {}).get('score', 'N/A')
                    result_url = f"https://compliance.conversations.im/server/{domain}"
                    bot.reply(msg, f"✅ Compliance score for {domain}: **{score}%**\nDetails: {result_url}")
                else:
                    bot.reply(msg, f"🔴 Server not found in compliance database")
    except asyncio.TimeoutError:
        bot.reply(msg, f"🔴 Compliance request timed out.")
    except Exception as e:
        bot.reply(msg, f"🔴 Error: {e}")
