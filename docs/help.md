# Runtime help

EnvsBot builds its help output from the live command registry. This keeps the in-chat help and the generated command reference close to the code.

## Main entry points

Examples use the default prefix `,`.

```text
,help
,help commands
,help categories
,help category <name>
,help plugins
,help roles
,help <plugin>
,help <command>
,help ,<command>
,help all
```

## Focused help

Use focused help when you already know the plugin or command name:

```text
,help rooms
,help rooms add
,help users role
,help ,users role
```

Plugin help shows the plugin description, category, requirements and visible commands. Command help shows role, context, aliases, usage and examples.

## Categories

`,help commands` groups visible commands by category. Use `,help categories` to list the available categories and `,help category <name>` to show only one group.

Typical categories are:

```text
admin
core
fun
info
rooms
users
xmpp
```

The exact list depends on loaded plugins and your role.

## Roles and visibility

Help output is role-aware. Commands that require a stronger role are hidden or rejected.

Lower role values have more privileges:

```text
owner > superadmin > admin > moderator > trusted > user > new/none > banned
```

Privileged commands are normally intended for private chats or MUC PMs. The configured owner should be the only user able to grant superadmin rights.

## In-room help

By default, public room help can be disabled per room to reduce noise. Admins or users with sufficient permissions can control the room setting with:

```text
,help inroom status
,help inroom on
,help inroom off
```

Private chats and MUC PMs remain the preferred place for full help output.

## Updating command docs

After changing command decorators or `utils/command_help.py`, regenerate the command reference:

```bash
python scripts/generate_commands_md.py
```

Generated output lives in [`commands.md`](commands.md).
