import slixmpp
import asyncio
import json
import inspect
import os
import sys
import logging
import time

from plugin_manager import PluginManager
from logging_setup import setup_logging
from database import DatabaseManager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# === set up logging ===
setup_logging()
log = logging.getLogger(__name__)


class PresenceManager:

    def __init__(self, bot):

        self.bot = bot

        self.status = {
            "show": "online",
            "status": "I'm ready to serve you!"
        }

        self.joined_rooms = {}

        self.emojis = {
            "online": "✅",
            "chat": "💬",
            "away": "👋 ",
            "xa": "💤",
            "dnd": "⛔"
        }

    def update(self, show, status):

        self.status["show"] = show
        self.status["status"] = status

        self.broadcast()

    def broadcast(self):

        show = self.status["show"]
        status = self.status["status"]

        self.bot.send_presence(pshow=show, pstatus=status)

        for room, nick in self.joined_rooms.items():
            self.bot.send_presence(
                pto=f"{room}/{nick}", pshow=show, pstatus=status)
        # log message
        log.info(f"{self.emoji(show)} Status set: '{show}': [{status}]")

    def emoji(self, show=None):

        show = show or self.status["show"]
        return self.emojis.get(show, "")


class Bot(slixmpp.ClientXMPP):

    def __init__(self, config_file):
        # load config file (json)
        with open(config_file) as f:
            self.config = json.load(f)
        # run __init__() from ClientXMPP
        super().__init__(self.config["jid"], self.config["password"])

        self.rooms = []
        self.nick = self.config.get("nick", "bot")
        self.admins = []
        owner = self.config.get("owner")
        if owner:
            self.admins.append(owner)
        self.prefix = self.config.get("prefix", ",")
        self.commands = {}

        # Presence Manager
        self.presence = PresenceManager(self)

        # Database Manager
        self.db = DatabaseManager(self.config.get("db", "bot.db"))

        # Plugin Manager
        self.commands = {}
        self.plugins = PluginManager(self)
        self.load_plugins()

        self.add_event_handler("session_start", self.on_start)
        self.add_event_handler("groupchat_message", self.on_muc_message)
        self.add_event_handler("message", self.on_private_message)
        self.add_event_handler("muc::%s::got_online" % "*", self.on_muc_join)
        self.add_event_handler("muc::%s::got_offline" % "*", self.on_muc_leave)
        self.add_event_handler("muc::%s::nick_changed" % "*",
                               self.on_muc_nick_changed)

    async def autojoin_rooms(self):
        """
        Join all rooms marked with autojoin in the database.
        """

        rows = await self.db.rooms.list()
        for room_jid, nick, autojoin, status in rows:
            if not autojoin:
                continue
            log.info("Autojoining room %s as %s", room_jid, nick)
            self.plugin["xep_0045"].join_muc(
                room_jid,
                nick,
                pshow=self.presence.status["show"],
                pstatus=self.presence.status["status"])
            if room_jid not in self.rooms:
                self.rooms.append(room_jid)
            self.presence.joined_rooms[room_jid] = nick

    def load_plugins(self):
        """
        Discover and load all plugins from the plugins directory.
        """
        log.info("✅ Loading plugins")
        try:
            # discover plugin names
            plugin_list = self.plugins.discover()
        except Exception as e:
            log.error(f"[PLUGIN] Failed to discover plugins: {e}")
            return

        if not plugin_list:
            log.info("[PLUGIN] No plugins found.")
            return

        log.info(f"[PLUGIN] Found {len(plugin_list)} plugin(s): "
                 + f"{', '.join(plugin_list)}")

        loaded = 0
        failed = 0
        for plugin_name in plugin_list:
            try:
                self.plugins.load(plugin_name)
                log.info(f"[PLUGIN] Loaded: {plugin_name}")
                loaded += 1
            except Exception as e:
                log.error(f"[PLUGIN] Failed to load {plugin_name}: {e}")
                failed += 1

        log.info(f"[PLUGIN] Load complete: {loaded} loaded, {failed} failed.")

    def reply(self, msg, text, mention=True, thread=True, rate_limit=True):
        """
        Smart reply helper for plugins.

        Features:
        - Mentions the sender in group chats
        - Supports message threading
        - Formats multi-line responses
        - Basic per-user rate limiting

        Args:
            msg: Original message object
            text (str|list): Reply text or list of lines
            mention (bool): Mention sender in group chats
            thread (bool): Thread reply if possible
            rate_limit (bool): Apply anti-spam limit
        """

        # Convert list responses into multi-line text
        if isinstance(text, list):
            text = "\n".join(text)

        sender = str(msg["from"])

        # basic rate limit storage
        if not hasattr(self, "_reply_rate"):
            self._reply_rate = {}

        # Rate limiting (2 replies per second per user)
        if rate_limit:
            now = time.time()
            last = self._reply_rate.get(sender, 0)
            if now - last < 0.5:
                return
            if len(self._reply_rate) > 1000:
                cutoff = now - 60
                self._reply_rate = {
                        k: v for k, v in self._reply_rate.items()
                        if v > cutoff
                }

        if msg["type"] == "groupchat":
            body = text
            if mention:
                nick = msg.get("mucnick") or msg["from"].resource
                body = f"{nick}: {text}"
            reply_kwargs = {}
            if thread and msg.get("id"):
                reply_kwargs["replyto"] = msg["id"]
            self.send_message(
                mto=msg["from"].bare,
                mbody=body,
                mtype="groupchat",
                **reply_kwargs
            )
        else:
            self.send_message(
                mto=msg["from"],
                mbody=text,
                mtype="chat"
            )

    async def on_start(self, event):
        # send startup presence
        self.presence.broadcast()
        # Get roster
        await self.get_roster()
        # Connect to DB
        await self.db.connect()
        # Autojoin Rooms from DB
        await self.autojoin_rooms()
        # send presence again
        self.presence.broadcast()
        # set automatic mutual subscriptions
        self.roster.auto_subscribe = True

        log.info("✅ Bot started, all rooms joined")

    def is_admin(self, jid):
        return slixmpp.JID(jid).bare in self.admins

    def on_muc_join(self, presence):

        room = presence["from"].bare
        nick = presence["muc"]["nick"]

        log.info("[MUC] 🤖 Joined room %s as %s", room, nick)

    def on_muc_leave(self, presence):
        """
        Handle occupants leaving a MUC.

        If the bot itself leaves a room, remove the room from the
        presence manager's joined_rooms mapping.
        """

        room = presence["from"].bare
        nick = presence["muc"]["nick"]

        # ignore if we never registered this room
        if room not in self.presence.joined_rooms:
            return

        # if the leaving nick is our own nick, we left the room
        if self.presence.joined_rooms.get(room) == nick:
            self.presence.joined_rooms.pop(room, None)
            if room in self.rooms:
                self.rooms.remove(room)
            log.info("[MUC] 🚪 Left room %s (%s)", room, nick)

    def on_muc_nick_changed(self, presence):

        room = presence["from"].bare
        new_nick = presence["muc"]["nick"]

        if presence["muc"]["jid"] == self.boundjid.bare:
            # update the bot's nick tracking
            self.plugin["xep_0045"].our_nicks[room] = new_nick
            # update PresenceManager
            try:
                self.presence.joined_rooms[room] = new_nick
            except KeyError:
                log.warning("⚠️Room not present in PresenceManager!")

            log.info(f"✅ Room Nick changed: '{self.nick}' -> [{new_nick}]")

    async def on_muc_message(self, msg):

        room = msg['from'].bare
        nick = msg['mucnick']
        if self.presence.joined_rooms.get(room) == nick:
            return

        if msg["type"] == "groupchat":
            await self.handle_command(
                msg["body"],
                msg["from"].bare,
                msg["mucnick"],
                msg,
                True
            )

    async def on_private_message(self, msg):

        if msg["type"] in ("chat", "normal"):
            await self.handle_command(
                msg["body"],
                msg["from"].bare,
                None,
                msg,
                False
            )

    async def handle_command(self, body, sender_jid, nick, msg, is_room):
        if not body:
            return
        if not body.startswith(self.prefix):
            return

        parts = body[len(self.prefix):].strip().split()

        if not parts:
            return

        command = None
        cmd = None
        args = []

        # try longest command match
        for i in range(len(parts), 0, -1):
            candidate = " ".join(parts[:i])
            if candidate in self.commands:
                cmd = candidate
                command = self.commands[candidate]
                args = parts[i:]
                break

        if not command:
            return

        if (getattr(command, "admins_only", False)
                and not self.is_admin(sender_jid)):
            self.send_message(
                mto=msg["from"].bare if is_room else msg["from"],
                mbody="❌You are not allowed to use this command.",
                mtype="groupchat" if is_room else "chat"
            )
            return

        try:
            if inspect.iscoroutinefunction(command):
                await command(self, sender_jid, nick, args, msg, is_room)
            else:
                command(self, sender_jid, nick, args, msg, is_room)
        except Exception as e:
            log.exception(f"❌ Error while executing command '{cmd}'")
            # send user-friendly error message
            target = msg["from"].bare if is_room else msg["from"]
            if self.is_admin(sender_jid):
                err_msg = f"❌Command error: {e}"
            else:
                err_msg = f"❌Command '{cmd}' failed due to internal error."
            self.send_message(
                mto=target,
                mbody=err_msg,
                mtype="groupchat" if is_room else "chat"
            )


async def main():
    xmpp = Bot("config.json")

    xmpp.register_plugin("xep_0030")
    xmpp.register_plugin("xep_0045")
    xmpp.register_plugin("xep_0084")
    xmpp.register_plugin("xep_0163")
    xmpp.register_plugin("xep_0054")

    try:
        # startup bot
        await xmpp.connect()
        log.info("[XMPP] ✅ Connected successfully. Starting event loop...")
        # await disconnected
        await xmpp.disconnected
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Gracefully shut down on CTRL-c
        log.info("[XMPP] Shutdown request")
    finally:
        log.info("[XMPP] Disconnecting bot")
        if xmpp.db:
            await xmpp.db.close()
        xmpp.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
