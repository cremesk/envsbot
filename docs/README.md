# EnvsBot documentation

This directory contains the operator and command documentation for EnvsBot.

## Index

- [`commands.md`](commands.md) - generated command reference from the live command metadata
- [`help.md`](help.md) - runtime help behavior and usage examples
- [`maintenance.md`](maintenance.md) - offline SQLite maintenance workflow

## Regenerate command reference

Run this after changing command decorators or `utils/command_help.py`:

```bash
python scripts/generate_commands_md.py
```
