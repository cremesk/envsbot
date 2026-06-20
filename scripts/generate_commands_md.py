#!/usr/bin/env python3
"""Generate docs/commands.md from plugin command metadata."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.command import Role  # noqa: E402
from utils.config import config  # noqa: E402

PREFIX = config.get("prefix", ",")


def _clean(value: str | None) -> str:
    return inspect.cleandoc(value or "").strip()


def _first_line(doc: str | None) -> str:
    for line in _clean(doc).splitlines():
        line = line.strip()
        if line:
            return line.replace("{prefix}", PREFIX)
    return "No description available."


def _metadata(cmd):
    short = getattr(cmd, "short", "") or _first_line(cmd.handler.__doc__)
    usage = getattr(cmd, "usage", "") or f"{{prefix}}{cmd.name}"
    examples = getattr(cmd, "examples", []) or []
    return {
        "short": str(short).replace("{prefix}", PREFIX),
        "usage": str(usage).replace("{prefix}", PREFIX),
        "examples": [str(e).replace("{prefix}", PREFIX) for e in examples],
        "context": getattr(cmd, "context", "any") or "any",
        "role": getattr(cmd, "role", Role.NONE),
    }


def _plugin_meta(module, name):
    meta = getattr(module, "PLUGIN_META", {}) or {}
    return {
        "name": meta.get("name", name),
        "category": meta.get("category", "other"),
        "description": meta.get("description") or _first_line(module.__doc__),
        "hidden": bool(meta.get("hidden")),
    }


def _discover_plugins():
    import plugins

    names = sorted(m.name for m in pkgutil.iter_modules(plugins.__path__))
    for name in names:
        try:
            yield name, importlib.import_module(f"plugins.{name}")
        except Exception as exc:
            print(f"warning: could not import plugins.{name}: {exc}", file=sys.stderr)


def _commands_from_module(module):
    seen = set()
    commands = []
    for _, obj in inspect.getmembers(module):
        if not callable(obj) or not hasattr(obj, "__commands__"):
            continue
        for registered_name, cmd in getattr(obj, "__commands__", []):
            if id(cmd) in seen or registered_name != cmd.name:
                continue
            seen.add(id(cmd))
            commands.append(cmd)
    return sorted(commands, key=lambda c: c.name)


def generate() -> str:
    lines = [
        "# envsbot command reference",
        "",
        "This file is generated from command metadata. Edit command decorators or `utils/command_help.py`, then run:",
        "",
        "```bash",
        "python scripts/generate_commands_md.py",
        "```",
        "",
    ]

    for name, module in _discover_plugins():
        meta = _plugin_meta(module, name)
        if meta["hidden"]:
            continue
        commands = _commands_from_module(module)
        if not commands:
            continue

        lines += [
            f"## {meta['name']}",
            "",
            f"Category: `{meta['category']}`",
            "",
            str(meta["description"]),
            "",
        ]

        for cmd in commands:
            data = _metadata(cmd)
            aliases = sorted(set(a for a in (cmd.aliases or []) if a != cmd.name))
            lines += [
                f"### `{PREFIX}{cmd.name}`",
                "",
                data["short"],
                "",
                f"Role: `{str(data['role'])}`  ",
                f"Context: `{data['context']}`  ",
                f"Usage: `{data['usage']}`",
                "",
            ]
            if aliases:
                lines += ["Aliases: " + ", ".join(f"`{PREFIX}{alias}`" for alias in aliases), ""]
            if data["examples"]:
                lines.append("Examples:")
                lines.append("")
                for example in data["examples"]:
                    lines.append(f"- `{example}`")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    output = ROOT / "docs" / "commands.md"
    output.write_text(generate(), encoding="utf-8")
    print(f"wrote {output.relative_to(ROOT)}")
