"""
Global pytest configuration and shared fixtures for the test suite.

This file provides:

- Path setup so the project root can be imported during tests.
- Core fixtures used across the test suite (bot, configuration, XMPP messages).
- Automatic isolation of the global command registry so tests cannot
  contaminate each other via shared state.

The command registry reset fixture runs automatically for every test and
ensures a clean environment before and after execution.
"""

import importlib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import AsyncMock, MagicMock

from tests.xmpp_fixtures import MockMessage
from utils.command import Role, COMMANDS


@pytest.fixture(autouse=True)
def _isolate_command_registry():
    """
    Ensure the global command registry is clean for every test.

    The bot command system uses a global registry. Without resetting it,
    tests that load plugins or register commands can affect later tests.
    This fixture prevents cross-test contamination.
    """
    COMMANDS.index.clear()
    COMMANDS.by_handler.clear()
    COMMANDS.by_plugin.clear()
    COMMANDS.by_prefix.clear()

    yield

    COMMANDS.index.clear()
    COMMANDS.by_handler.clear()
    COMMANDS.by_plugin.clear()
    COMMANDS.by_prefix.clear()


@pytest.fixture
def mock_config(monkeypatch):
    test_config = {
        "jid": "bot@test.local/testbot",
        "password": "test",
        "owner": "owner@test.local",
        "prefix": ",",
        "db": ":memory:"
    }
    # patch the config object used by the bot
    monkeypatch.setattr("utils.config.config", test_config)

    return test_config


@pytest.fixture
def bot(mock_config):

    if "bot" in sys.modules:
        importlib.reload(sys.modules["bot"])

    from envsbot import Bot

    bot = Bot()

    bot.send_message = MagicMock()
    bot.make_message = MagicMock()

    bot.get_user_role = AsyncMock(return_value=Role.OWNER)
    bot.connect = AsyncMock()

    bot.db.connect = AsyncMock()
    bot.db.close = AsyncMock()

    return bot


@pytest.fixture
def xmpp_msg():
    """
    Provide a realistic mock XMPP message.
    """
    return MockMessage()
