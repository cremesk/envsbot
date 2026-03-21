"""
command.py

Command registration and resolution system for the bot.
"""

from __future__ import annotations
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


class Role(IntEnum):
    """
    Role hierarchy used for command permission checks.

    Lower numbers represent higher privileges.

    The range 1–100 leaves large gaps for future roles.
    """

    OWNER = 1

    SUPERADMIN = 10
    ADMIN = 20

    MODERATOR = 40

    TRUSTED = 60
    USER = 80

    NEW = 90
    NONE = 95

    BANNED = 100

    def __str__(self):
        return self.name.lower()


def role_from_int(value: int) -> Role:
    """
    Convert an integer (typically from the database) to a Role enum.

    Unknown values default to USER.
    """

    try:
        return Role(value)
    except ValueError:
        return Role.USER


def is_banned(role: Role) -> bool:
    """
    Check whether a role represents a banned user.
    """

    return role >= Role.BANNED


class CommandRegistry:
    """
    Central registry for all commands exposed by plugins.
    """

    def __init__(self):
        self.index: Dict[Tuple[str, ...], Command] = {}
        self.by_handler: Dict[object, set[tuple[str, ...]]] = {}
        self.by_plugin: Dict[str, set[tuple[str, ...]]] = {}
        self.by_prefix: Dict[str, set[tuple[str, ...]]] = {}

    def register(self, name: str, cmd: "Command", plugin: str | None = None):
        tokens = tuple(name.lower().split())
        if not tokens:
            return

        if tokens in self.index:
            existing = self.index[tokens]
            raise ValueError(
                f"Command already registered: '{' '.join(tokens)}' "
                f"(handler={existing.handler.__name__})"
            )

        self.index[tokens] = cmd

        prefix = tokens[0]
        self.by_prefix.setdefault(prefix, set()).add(tokens)

        if plugin:
            self.by_plugin.setdefault(plugin, set()).add(tokens)

        handler = getattr(cmd, "handler", None)
        if handler is not None:
            self.by_handler.setdefault(handler, set()).add(tokens)

    def remove(self, tokens: Tuple[str, ...]):
        cmd = self.index.pop(tokens, None)

        if not cmd:
            return

        prefix = tokens[0]

        if prefix in self.by_prefix:
            self.by_prefix[prefix].discard(tokens)
            if not self.by_prefix[prefix]:
                del self.by_prefix[prefix]

        handler = getattr(cmd, "handler", None)

        if handler in self.by_handler:
            self.by_handler[handler].discard(tokens)
            if not self.by_handler[handler]:
                del self.by_handler[handler]

    def remove_by_handler(self, handler):
        tokens = list(self.by_handler.get(handler, ()))
        for t in tokens:
            self.remove(t)

    def remove_by_plugin(self, plugin: str):
        tokens = list(self.by_plugin.get(plugin, ()))

        for t in tokens:
            self.remove(t)

        self.by_plugin.pop(plugin, None)

    def items(self):
        return self.index.items()

    def get(self, tokens):
        return self.index.get(tokens)

    def debug_dump(self) -> Dict[str, dict]:
        """
        Return a structured snapshot of the command registry.

        Useful for debugging plugin reload issues or command collisions.
        """

        data = {}

        for tokens, cmd in self.index.items():
            name = " ".join(tokens)

            data[name] = {
                "handler": getattr(cmd.handler, "__name__", str(cmd.handler)),
                "role": str(cmd.role),
                "aliases": list(cmd.aliases),
            }

        return data


@dataclass
class Command:
    """
    Representation of a registered command.
    """

    name: str
    handler: Callable
    role: Role = Role.NONE
    aliases: List[str] = field(default_factory=list)


COMMANDS = CommandRegistry()


def _register(name: str, cmd: Command):
    """
    Attach command metadata to the handler so PluginManager
    can register it when the plugin loads.
    """

    tokens = tuple(name.lower().split())

    if not tokens:
        return

    if not hasattr(cmd.handler, "__commands__"):
        cmd.handler.__commands__ = []
    else:
        if not isinstance(cmd.handler.__commands__, list):
            cmd.handler.__commands__ = []

    entry = (name, cmd)

    # Prevent duplicate registrations during plugin reload
    if entry not in cmd.handler.__commands__:
        cmd.handler.__commands__.append((name, cmd))


def command(
    name: str,
    role: Role = Role.NONE,
    aliases: Optional[List[str]] = None,
):
    """
    Decorator used to register a command.
    """

    if aliases is None:
        aliases = []

    def decorator(func: Callable):

        cmd = Command(
            name=name,
            handler=func,
            role=role,
            aliases=aliases,
        )

        _register(name, cmd)

        for alias in aliases:
            _register(alias, cmd)

        func._command = name
        func._command_names = [name] + aliases
        func._required_role = role
        func._aliases = aliases

        return func

    return decorator


def resolve_command(text: str):
    """
    Resolve the longest matching command from a text input.
    """

    tokens = text.split()

    if not tokens:
        return None, []

    lower_tokens = [t.lower() for t in tokens]

    best_cmd = None
    best_len = 0

    candidates = COMMANDS.by_prefix.get(lower_tokens[0], ())

    for cmd_tokens in candidates:

        cmd = COMMANDS.get(cmd_tokens)

        n = len(cmd_tokens)

        if len(lower_tokens) < n:
            continue

        if tuple(lower_tokens[:n]) == cmd_tokens:

            if n > best_len:
                best_cmd = cmd
                best_len = n

    if best_cmd is None:
        return None, tokens

    args = tokens[best_len:]

    return best_cmd, args


def has_permission(user_role: Role, required_role: Role) -> bool:
    """
    Check whether a user role satisfies a command's role requirement.
    """

    if is_banned(user_role):
        return False

    return user_role <= required_role


def check_permission(user_role: Role, cmd: Command) -> bool:
    """
    Convenience wrapper for permission checking.
    """

    return has_permission(user_role, cmd.role)


def debug_leaks():
    print("\n--- COMMAND REGISTRY DEBUG ---")

    print("index size:", len(COMMANDS.index))
    print("by_handler size:", len(COMMANDS.by_handler))
    print("by_plugin size:", len(COMMANDS.by_plugin))
    print("by_prefix size:", len(COMMANDS.by_prefix))

    if COMMANDS.by_handler:
        print("\nHandlers still referenced:")
        for handler, tokens in COMMANDS.by_handler.items():
            print(" ", handler, "->", tokens)

    if COMMANDS.by_plugin:
        print("\nPlugins still registered:")
        for plugin, tokens in COMMANDS.by_plugin.items():
            print(" ", plugin, "->", tokens)

    print("--- END DEBUG ---\n")
