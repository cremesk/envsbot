import importlib
import inspect
import sys
import os
import logging

log = logging.getLogger(__name__)


class PluginManager:

    def __init__(self, bot, plugin_package="plugins"):
        self.bot = bot
        self.plugin_package = plugin_package
        self.plugins = {}
        self.command_map = {}

    # -------------------------
    # DISCOVER
    # -------------------------
    def discover(self):
        plugin_dir = self.plugin_package.replace(".", "/")
        plugins = []
        for file in os.listdir(plugin_dir):
            if file.endswith(".py") and not file.startswith("_"):
                plugins.append(file[:-3])
        return plugins

    # -------------------------
    # LOAD
    # -------------------------
    def load(self, name):
        # Prevent of loading a plugin twice
        if name in self.plugins:
            return

        # Load the plugin
        module_path = f"{self.plugin_package}.{name}"
        module = importlib.import_module(module_path)
        self._register_plugin(name, module)
        return module

    # -------------------------
    # REGISTER
    # -------------------------
    def _register_plugin(self, name, module):
        meta = getattr(module, "PLUGIN_META", {})
        requires = meta.get("requires", [])
        for dep in requires:
            if dep not in self.plugins:
                self.load(dep)
        commands = []

        for _, obj in inspect.getmembers(module):
            if hasattr(obj, "_command"):
                for cmd_name in obj._command_names:
                    self.bot.commands[cmd_name] = obj
                    self.command_map[cmd_name] = name
                commands.append(obj)

        if hasattr(module, "register"):
            module.register(self.bot)

        self.plugins[name] = {
            "module": module,
            "commands": commands,
            "meta": meta
        }

    # -------------------------
    # UNLOAD
    # -------------------------
    def unload(self, name):
        if name not in self.plugins:
            return

        module_path = f"{self.plugin_package}.{name}"

        # remove commands
        remove = []

        for cmd, owner in self.command_map.items():
            if owner == name:
                remove.append(cmd)

        for cmd in remove:
            del self.bot.commands[cmd]
            del self.command_map[cmd]

        # unload hook
        plugin = self.plugins[name]
        module = plugin["module"]

        if hasattr(module, "unregister"):
            module.unregister(self.bot)

        # remove module cache
        if module_path in sys.modules:
            del sys.modules[module_path]

        del self.plugins[name]

    # -------------------------
    # RELOAD
    # -------------------------
    def reload(self, name):
        self.unload(name)
        return self.load(name)

    # -------------------------
    # LOAD ALL
    # -------------------------
    def load_all(self, plugin_list):
        for name in plugin_list:
            self.load(name)
