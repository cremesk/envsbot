"""
Async plugin manager for dynamic loading, unloading, and reloading of plugins.

This module provides the PluginManager class, which is responsible for:
- Discovering plugins from a package
- Loading plugins with dependency resolution
- Registering commands into the global COMMANDS registry
- Managing plugin lifecycle hooks (on_load / on_unload)
- Tracking plugin metadata and event handlers

All lifecycle operations are fully asynchronous and must be awaited.
"""

import asyncio
import importlib
import pkgutil
import sys
import inspect
import logging

from utils.command import COMMANDS, Role

log = logging.getLogger(__name__)


class PluginManager:
    """
    Manages plugin lifecycle and integration with the bot.

    This class is fully asynchronous. All lifecycle methods (load, unload,
    reload, load_all) must be awaited.

    Attributes:
        bot: The bot instance used for registering event handlers.
        package (str): Python package path where plugins are located.
        plugins (dict): Loaded plugin modules mapped by name.
        meta (dict): Cached PLUGIN_META per plugin.
        _event_handlers (dict): Registered event handlers per plugin.
        _lock (asyncio.Lock): Ensures safe concurrent lifecycle operations.
    """

    def __init__(self, bot, package="plugins"):
        """Initialize the plugin manager."""
        self.bot = bot
        self.package = package

        self.plugins = {}
        self.meta = {}
        self._event_handlers = {}

        self._lock = asyncio.Lock()

    # --------------------------------------------------
    # EVENTS
    # --------------------------------------------------

    def register_event(self, plugin_name, event, handler):
        """
        Register an event handler for a plugin.

        Args:
            plugin_name (str): Name of the plugin.
            event (str): Event name.
            handler (callable): Event handler function.
        """
        self.bot.add_event_handler(event, handler)
        self._event_handlers.setdefault(plugin_name, []).append((event, handler))

    # --------------------------------------------------
    # DISCOVERY
    # --------------------------------------------------

    def discover(self):
        """
        Discover available plugins in the configured package.

        Returns:
            list[str]: Sorted list of plugin module names.
        """
        package = importlib.import_module(self.package)
        return sorted([m.name for m in pkgutil.iter_modules(package.__path__)])

    def list(self):
        """
        List currently loaded plugins.

        Returns:
            list[str]: Sorted list of loaded plugin names.
        """
        return sorted(self.plugins.keys())

    def available(self):
        """
        List plugins that are available but not currently loaded.

        Returns:
            list[str]: Sorted list of plugin names.
        """
        return sorted(set(self.discover()) - set(self.plugins))

    # --------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------

    async def _run_hook(self, hook):
        """
        Execute a plugin hook safely.

        Supports both sync and async functions.

        Args:
            hook (callable): Hook function.
        """
        if inspect.iscoroutinefunction(hook):
            await hook(self.bot)
        else:
            await asyncio.to_thread(hook, self.bot)

    async def _import(self, module_path):
        """
        Import a module asynchronously.

        Args:
            module_path (str): Full module path.

        Returns:
            module: Imported module.
        """
        return await asyncio.to_thread(importlib.import_module, module_path)

    # --------------------------------------------------
    # CORE (ASYNC)
    # --------------------------------------------------

    async def load(self, name, _stack=None):
        """
        Load a plugin and its dependencies.

        Args:
            name (str): Plugin name.
            _stack (list, optional): Dependency stack for cycle detection.
        """
        if name in self.plugins:
            log.warning("[PLUGIN] already loaded: %s", name)
            return

        if _stack is None:
            _stack = []

        if name in _stack:
            log.error(
                "[PLUGIN] circular dependency: %s -> %s",
                " -> ".join(_stack),
                name,
            )
            return

        _stack = _stack + [name]

        try:
            log.info("[PLUGIN] loading: %s", name)

            module = await self._import(f"{self.package}.{name}")
            meta = getattr(module, "PLUGIN_META", {})

            # Load dependencies first
            for dep in meta.get("requires", []):
                if dep not in self.plugins:
                    await self.load(dep, _stack)

            # Run on_load hook if present
            async with self._lock:
                if name in self.plugins:
                    return
                try:
                    if hasattr(module, "on_load"):
                        await self._run_hook(module.on_load)

                    # Register commands
                    self._register_commands(name, module)

                    self.plugins[name] = module
                    self.meta[name] = meta

                    log.info("[PLUGIN] loaded: %s", name)
                except Exception:
                    log.exception("[PLUGIN] ❌Failed to load plugin (on_load)"
                                  f": '{name}'")
                    COMMANDS.remove_by_plugin(name)
                    raise

        finally:
            pass

    async def unload(self, name):
        """
        Unload a plugin and clean up all associated resources.

        Args:
            name (str): Plugin name.

        Returns:
            bool: True if unloaded, False if not loaded.
        """
        async with self._lock:
            module = self.plugins.pop(name, None)
            if not module:
                return False

            # Remove event handlers
            for event, handler in self._event_handlers.pop(name, []):
                self.bot.del_event_handler(event, handler)

            # Run unload hook
            if hasattr(module, "on_unload"):
                try:
                    await self._run_hook(module.on_unload)
                except Exception:
                    log.exception("[PLUGIN] on_unload failed: %s", name)

            # Remove commands
            COMMANDS.remove_by_plugin(name)

            # Debug leak detection (if enabled)
            if log.isEnabledFor(logging.DEBUG):
                from utils.command import debug_leaks
                debug_leaks()

            # Cleanup metadata and module
            self.meta.pop(name, None)

            modname = module.__name__
            module.__dict__.clear()
            sys.modules.pop(modname, None)

            log.info("[PLUGIN] unloaded: %s", name)
            return True

    async def reload(self, name):
        """
        Reload a plugin.

        Args:
            name (str): Plugin name.
        """
        log.info("[PLUGIN] reloading: %s", name)
        await self.unload(name)
        await self.load(name)

    async def load_all(self):
        """
        Load all available plugins.
        """
        for plugin in self.discover():
            if plugin not in self.plugins:
                try:
                    await self.load(plugin)
                except Exception:
                    log.exception("[PLUGIN] failed to load: %s", plugin)

    # --------------------------------------------------
    # COMMAND REGISTRATION
    # --------------------------------------------------

    def _register_commands(self, plugin_name, module):
        """
        Register commands defined in a plugin module.

        This preserves the existing command system behavior.

        Args:
            plugin_name (str): Plugin name.
            module (module): Plugin module.
        """
        is_internal = plugin_name.startswith("_")

        for _, obj in inspect.getmembers(module):
            if callable(obj) and hasattr(obj, "_command_names"):

                for name, cmd in getattr(obj, "__commands__", []):
                    COMMANDS.register(name, cmd, plugin_name)

                for name in obj._command_names:
                    if is_internal:
                        tokens = tuple(name.lower().split())
                        cmd = COMMANDS.get(tokens)

                        if cmd and cmd.role > Role.ADMIN:
                            cmd.role = Role.ADMIN

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    async def get_plugin_info(self, name):
        """
        Retrieve PLUGIN_META for a plugin.

        Args:
            name (str): Plugin name.

        Returns:
            dict | None: Plugin metadata or None if not found.
        """
        if name in self.meta:
            return self.meta[name]

        try:
            module = await self._import(f"{self.package}.{name}")
            return getattr(module, "PLUGIN_META", {})
        except Exception:
            return None

    async def list_detailed(self):
        """
        Get categorized plugin status.

        Returns:
            dict: {category: {"loaded": [...], "available": [...]}}
        """
        loaded = set(self.plugins.keys())
        available = set(self.discover()) - loaded

        result = {}

        for name in loaded:
            meta = self.meta.get(name, {})
            cat = meta.get("category", "other")
            result.setdefault(cat, {"loaded": [], "available": []})
            result[cat]["loaded"].append(name)

        for name in available:
            meta = await self.get_plugin_info(name) or {}
            cat = meta.get("category", "other")
            result.setdefault(cat, {"loaded": [], "available": []})
            result[cat]["available"].append(name)

        return result
