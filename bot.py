import slixmpp
import asyncio
import json
import os
import importlib
import inspect
import logging

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
        import importlib
        import os

        plugin_dir = "plugins"

        for file in os.listdir(plugin_dir):
            if not file.endswith(".py") or file.startswith("_"):
                continue
            module_name = file[:-3]
            module = importlib.import_module(f"{plugin_dir}.{module_name}")

            # optional plugin initialization
            if hasattr(module, "register"):
                module.register(self)

            # -------------------------------------------------
            # decorator command auto-registration
            # -------------------------------------------------
            for attr in vars(module).values():
                if not callable(attr):
                    continue
                if not hasattr(attr, "_command_names"):
                    continue
                for name in attr._command_names:
                    # prevent duplicate command names
                    if name in self.commands:
                        raise ValueError(
                            f"Duplicate command name '{name}' "
                            f"in plugin '{module_name}'"
                        )

                    self.commands[name] = attr

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

        if getattr(command, "owner_only", False) and not self.is_admin(sender_jid):

            self.send_message(
                mto=msg["from"].bare if is_room else msg["from"],
                mbody="You are not allowed to use this command.",
                mtype="groupchat" if is_room else "chat"
            )

            return

        if inspect.iscoroutinefunction(command):
            await command(self, sender_jid, nick, args, msg, is_room)
        else:
            command(self, sender_jid, nick, args, msg, is_room)


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
