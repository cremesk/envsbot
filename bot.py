import slixmpp
import asyncio
import json
import inspect
import os
import sys
import importlib
import logging
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# === set up logging ===
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class PresenceManager:

    def __init__(self, bot):

        self.bot = bot

        self.status = {
            "show": "online",
            "status": "I'm ready to serve you!"
        }

        self.joined_rooms = set()

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

        for room in self.bot.rooms:

            nick = self.bot.plugin["xep_0045"].our_nicks.get(room,
                                                             self.bot.nick)

            self.bot.send_presence(
                pto=f"{room}/{nick}",
                pshow=show,
                pstatus=status
            )

        # log message
        log.info(f"✅ Status set: '{show}': [{status}]")

    def emoji(self, show=None):

        show = show or self.status["show"]
        return self.emojis.get(show, "")


class Bot(slixmpp.ClientXMPP):

    def __init__(self, config_file):

        with open(config_file) as f:
            self.config = json.load(f)

        super().__init__(self.config["jid"], self.config["password"])

        self.rooms = self.config.get("rooms", [])
        self.nick = self.config.get("nick", "bot")
        self.admins = set(self.config.get("admins", []))
        self.prefix = self.config.get("prefix", ",")
        self.commands = {}

        self.presence = PresenceManager(self)

        self.load_plugins()

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("groupchat_message", self.muc_message)
        self.add_event_handler("message", self.private_message)
        self.add_event_handler("muc::%s::got_online" % "*", self.muc_join)
        self.add_event_handler("muc::%s::got_offline" % "*", self.muc_leave)
        self.add_event_handler("muc::%s::nick_changed" % "*",
                               self.muc_nick_changed)

    def load_plugins(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        plugin_dir = os.path.join(base_dir, "plugins")
        sys.path.insert(0, base_dir)

        for filename in os.listdir(plugin_dir):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            module_name = filename[:-3]
            module_path = f"plugins.{module_name}"

            try:
                module = importlib.import_module(module_path)
                importlib.reload(module)
            except Exception:
                log.exception(f"❌ Failed to load plugin {module_name}")
                continue

            log.info(f"✅ Loaded plugin: {module_name}")

            # optional register hook
            if hasattr(module, "register"):
                try:
                    module.register(self)
                except Exception:
                    log.exception(f"❌Plugin register() failed: {module_name}")

            # command discovery
            for attr in vars(module).values():
                if callable(attr) and hasattr(attr, "_command_names"):
                    for name in attr._command_names:
                        if name in self.commands:
                            log.warning(
                                f"⚠️ Command '{name}' already registered "
                                + "(plugin {module_name})"
                            )
                            continue
                        self.commands[name] = attr
                        log.info(
                            f"- Registered command '{name}' from {module_name}"
                        )

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
            self._reply_rate[sender] = now

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

    async def start(self, event):

        self.presence.broadcast()

        await self.get_roster()

        for room in self.rooms:
            self.plugin["xep_0045"].join_muc(room, self.nick)
        self.presence.broadcast()

        # set automatic mutual subscriptions
        self.roster.auto_subscribe = True

        log.info("✅ Bot started, all rooms joined")

    def is_admin(self, jid):
        return jid in self.admins

    def muc_join(self, presence):

        room = presence["from"].bare
        nick = presence["muc"]["nick"]

        if nick == self.nick:
            self.presence.joined_rooms.add(room)

    def muc_leave(self, presence):

        room = presence["from"].bare
        nick = presence["muc"]["nick"]

        if nick == self.nick and room in self.presence.joined_rooms:
            self.presence.joined_rooms.remove(room)

    def muc_nick_changed(self, presence):

        room = presence["from"].bare
        new_nick = presence["muc"]["nick"]

        if presence["muc"]["jid"] == self.boundjid.bare:

            # update the bot's nick tracking
            self.plugin["xep_0045"].our_nicks[room] = new_nick

            log.info(f"✅ Room Nick changed: '{self.nick}' -> [{new_nick}]")

    async def muc_message(self, msg):

        if msg["mucnick"] == self.nick:
            return

        if msg["type"] == "groupchat":
            await self.handle_command(
                msg["body"],
                msg["from"].bare,
                msg["mucnick"],
                msg,
                True
            )

    async def private_message(self, msg):

        if msg["type"] in ("chat", "normal"):
            await self.handle_command(
                msg["body"],
                msg["from"].bare,
                None,
                msg,
                False
            )

    async def handle_command(self, body, sender_jid, nick, msg, is_room):

        if not body.startswith(self.prefix):
            return

        parts = body[len(self.prefix):].strip().split()

        if not parts:
            return

        cmd = parts[0]
        args = parts[1:]

        if cmd not in self.commands:
            return

        command = self.commands[cmd]

        if (getattr(command, "owner_only", False)
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


if __name__ == "__main__":

    xmpp = Bot("config.json")

    xmpp.register_plugin("xep_0030")
    xmpp.register_plugin("xep_0045")
    xmpp.register_plugin("xep_0084")
    xmpp.register_plugin("xep_0163")
    xmpp.register_plugin("xep_0054")

    if xmpp.connect():
        log.info("✅ Connected successfully. Starting event loop...")
        try:
            # Run the slixmpp event loop forever
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            # Gracefully shut down on CTRL-c
            log.info("Bot stopped manually.")
            xmpp.disconnect()
    else:
        log.error("❌Unable to connect to XMPP server.")
