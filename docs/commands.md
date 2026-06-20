# envsbot command reference

This file is generated from command metadata. Edit command decorators or `utils/command_help.py`, then run:

```bash
python scripts/generate_commands_md.py
```

## admin

Category: `core`

Bot administration commands

### `,bot restart`

Restart the bot process gracefully.

Role: `owner`  
Context: `private chat / MUC PM`  
Usage: `,bot restart`

Aliases: `,restart`

Examples:

- `,bot restart`

### `,bot shutdown`

Stop the bot using the configured stop command.

Role: `owner`  
Context: `private chat / MUC PM`  
Usage: `,bot shutdown`

Aliases: `,shutdown`

Examples:

- `,bot shutdown`

### `,bot status`

Show bot, database, plugin and room status.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,bot status`

Aliases: `,bot info`

Examples:

- `,bot status`

## birthday_notify

Category: `fun`

Automatic birthday notifications in rooms (opt-in per room)

### `,birthday_notify`

Enable, disable or show birthday notifications for a room.

Role: `user`  
Context: `room or MUC PM`  
Usage: `,birthday_notify <on|off|status>`

Examples:

- `,birthday_notify status`

## config_cmd

Category: `core`

Safe config inspection, validation and reload commands.

### `,config reload`

Reload config.json into the running bot where possible.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,config reload`

Examples:

- `,config reload`

### `,config show`

Show the effective config with secrets redacted.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,config show [all|page|last]`

Aliases: `,config`

Examples:

- `,config show`
- `,config show all`

### `,config validate`

Validate the current config.json file.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,config validate`

Examples:

- `,config validate`

## db

Category: `core`

SQLite status and integrity inspection helpers.

### `,db status`

Show SQLite database path, size and integrity status.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,db status`

Aliases: `,database status`

Examples:

- `,db status`

## dice

Category: `games`

Roll dice with optional modifiers and success conditions.

### `,dice`

Roll dice using common dice notation.

Role: `user`  
Context: `any`  
Usage: `,dice [NdM]`

Aliases: `,r`, `,roll`

Examples:

- `,dice`
- `,dice 2d6`

## ducks

Category: `fun`

Duck game for MUCs with room toggles and leaderboards

### `,bef`

Befriend the current duck.

Role: `user`  
Context: `any`  
Usage: `,bef`

Examples:

- `,bef`

### `,duck`

Start or interact with the duck game.

Role: `user`  
Context: `any`  
Usage: `,duck`

Examples:

- `,duck`

### `,duckstats`

Show duck game stats.

Role: `user`  
Context: `any`  
Usage: `,duckstats [nick]`

Examples:

- `,duckstats`

### `,trap`

Set a trap in the duck game.

Role: `user`  
Context: `any`  
Usage: `,trap`

Examples:

- `,trap`

## help

Category: `core`

Dynamic help for plugins and commands.

### `,help`

Show help for plugins and commands.

Role: `none`  
Context: `any`  
Usage: `,help [all|commands|plugins|roles|<plugin>|<command>]`

Aliases: `,h`

Examples:

- `,help`
- `,help rooms`
- `,help rooms add`
- `,help ,users role`

### `,help inroom`

Enable, disable or show room help availability.

Role: `user`  
Context: `room or MUC PM`  
Usage: `,help inroom <on|off|status>`

Aliases: `,h inroom`

Examples:

- `,help inroom on`
- `,help inroom status`

## info

Category: `info`

Wikipedia, Fediverse, Urban Dictionary and acronym lookup.

### `,acronyms`

Look up stored acronym definitions.

Role: `user`  
Context: `any`  
Usage: `,acronyms <term>`

Aliases: `,acro`, `,acronym`

Examples:

- `,acro XMPP`

### `,acronyms add`

Add a definition to an acronym.

Role: `user`  
Context: `any`  
Usage: `,acronyms add <term> <definition>`

Aliases: `,acro add`, `,acronym add`

Examples:

- `,acro add XMPP Extensible Messaging and Presence Protocol`

### `,acronyms delete`

Delete an acronym completely.

Role: `admin`  
Context: `any`  
Usage: `,acronyms delete <term>`

Aliases: `,acro delete`, `,acronym delete`

Examples:

- `,acro delete XMPP`

### `,acronyms list`

List known acronyms.

Role: `admin`  
Context: `any`  
Usage: `,acronyms list [all|page|last]`

Aliases: `,acro list`, `,acronym list`

Examples:

- `,acro list`

### `,acronyms merge`

Merge one acronym into another.

Role: `admin`  
Context: `any`  
Usage: `,acronyms merge <source> <target>`

Aliases: `,acro merge`, `,acronym merge`

Examples:

- `,acro merge xmpp XMPP`

### `,acronyms remove`

Remove one acronym definition.

Role: `user`  
Context: `any`  
Usage: `,acronyms remove <term> <number>`

Aliases: `,acro remove`, `,acronym remove`

Examples:

- `,acro remove XMPP 1`

### `,fediverse`

Look up Fediverse account or instance information.

Role: `user`  
Context: `any`  
Usage: `,fediverse <account|instance>`

Aliases: `,fedi`

Examples:

- `,fedi @user@example.org`

### `,info`

Enable, disable or show room access to information commands.

Role: `moderator`  
Context: `room or MUC PM`  
Usage: `,info <on|off|status>`

Examples:

- `,info status`

### `,udict`

Search Urban Dictionary.

Role: `user`  
Context: `any`  
Usage: `,udict <term>`

Aliases: `,ud`

Examples:

- `,ud xmpp`

### `,wikipedia`

Search Wikipedia.

Role: `user`  
Context: `any`  
Usage: `,wikipedia <term>`

Aliases: `,wiki`

Examples:

- `,wiki XMPP`

## karma

Category: `fun`

Room-local karma tracking with nick++ / nick--

### `,karma`

Show or update karma for a term.

Role: `user`  
Context: `any`  
Usage: `,karma [term|term++|term--]`

Examples:

- `,karma xmpp++`
- `,karma xmpp`

## pin

Category: `utility`

Pin room messages with paging and non-reply fallback.

### `,pin`

Pin, list or delete room pins.

Role: `user`  
Context: `any`  
Usage: `,pin <add|list|delete|on|off|status> ...`

Examples:

- `,pin list`

## plugins

Category: `core`

Runtime plugin management

### `,plugin info`

Show metadata for one plugin.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,plugin info <plugin>`

Aliases: `,plugins info`

Examples:

- `,plugin info rooms`

### `,plugin list`

List loaded and available plugins by category.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,plugins list [all|page|last]`

Aliases: `,plugins list`

Examples:

- `,plugins list`
- `,plugins list all`

### `,plugin load`

Load one plugin or all plugins.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,plugin load <plugin|all>`

Aliases: `,plugins load`

Examples:

- `,plugin load weather`

### `,plugin reload`

Reload one plugin or all plugins.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,plugin reload <plugin|all> [auto]`

Aliases: `,plugins reload`

Examples:

- `,plugin reload help`
- `,plugin reload all auto`

### `,plugin unload`

Unload one plugin, optionally forced.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,plugin unload <plugin> [force]`

Aliases: `,plugins unload`

Examples:

- `,plugin unload weather`

## poll

Category: `utility`

Room polls with voting, history and auto-close

### `,poll`

Create and manage polls.

Role: `user`  
Context: `any`  
Usage: `,poll <new|vote|list|close|on|off|status> ...`

Examples:

- `,poll list`

## presence

Category: `info`

Bot presence and status management

### `,presence`

Show or control per-room access to presence lookup.

Role: `none`  
Context: `any`  
Usage: `,presence [on|off|status]`

Examples:

- `,presence`
- `,presence status`

### `,presence set`

Set the bot presence state and status text.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,presence set <online|chat|away|xa|dnd> [message]`

Examples:

- `,presence set away maintenance`

## reminder

Category: `utility`

Schedule and manage reminders

### `,remind`

Create a reminder.

Role: `user`  
Context: `any`  
Usage: `,remind <when> <text>`

Aliases: `,rem`, `,reminder`

Examples:

- `,remind 10m check logs`

### `,remind delete`

Delete one reminder.

Role: `user`  
Context: `any`  
Usage: `,remind delete <id>`

Aliases: `,remind cancel`, `,remind rm`

Examples:

- `,remind delete 12`

### `,reminders`

List your reminders.

Role: `user`  
Context: `any`  
Usage: `,reminders [all|page|last]`

Aliases: `,remind list`, `,rems`

Examples:

- `,reminders`

## rooms

Category: `core`

Database-backed room management

### `,rooms add`

Add or update a stored room configuration.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,rooms add <room_jid> [nick] [autojoin]`

Aliases: `,room add`

Examples:

- `,rooms add test@conference.example.org EnvsBot true`

### `,rooms delete`

Remove a stored room and leave it if currently joined.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,rooms delete <room_jid>`

Aliases: `,room delete`

Examples:

- `,rooms delete test@conference.example.org`

### `,rooms disable`

Disable a room-scoped plugin for the current room.

Role: `moderator`  
Context: `MUC PM only`  
Usage: `,rooms disable <plugin>`

Aliases: `,room disable`

Examples:

- `,rooms disable xkcd`

### `,rooms enable`

Enable a room-scoped plugin for the current room.

Role: `moderator`  
Context: `MUC PM only`  
Usage: `,rooms enable <plugin>`

Aliases: `,room enable`

Examples:

- `,rooms enable weather`

### `,rooms join`

Join a room immediately and store it if needed.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,rooms join <room_jid> [nick]`

Aliases: `,room join`

Examples:

- `,rooms join test@conference.example.org`

### `,rooms leave`

Leave a room without deleting its stored configuration.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,rooms leave <room_jid>`

Aliases: `,room leave`

Examples:

- `,rooms leave test@conference.example.org`

### `,rooms list`

List stored rooms and currently joined rooms.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,rooms list [all|page|last]`

Aliases: `,room list`

Examples:

- `,rooms list`
- `,rooms list all`

### `,rooms plugins`

Show plugin toggle state for the current room.

Role: `moderator`  
Context: `MUC PM only`  
Usage: `,rooms plugins [all|page|last]`

Aliases: `,room plugins`

Examples:

- `,room plugins`
- `,room plugins all`

### `,rooms set_plugin_defaults`

Restore room plugin toggles to default values.

Role: `moderator`  
Context: `MUC PM only`  
Usage: `,rooms set_plugin_defaults`

Aliases: `,room set_plugin_defaults`, `,room spd`, `,rooms spd`

Examples:

- `,room spd`

### `,rooms sync`

Synchronize joined rooms with stored autojoin settings.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,rooms sync`

Aliases: `,room sync`

Examples:

- `,rooms sync`

### `,rooms update`

Update one field of a stored room.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,rooms update <room_jid> <nick|autojoin|status> <value>`

Aliases: `,room update`

Examples:

- `,rooms update test@conference.example.org autojoin true`

## rss

Category: `info`

RSS/Atom feed watcher and poster

### `,rss`

Manage RSS feed subscriptions for a room.

Role: `moderator`  
Context: `any`  
Usage: `,rss <add|list|delete|on|off|status> ...`

Examples:

- `,rss list`

## sed

Category: `tools`

Message correction using sed-like syntax

### `,sed`

Apply sed-style corrections to recent messages.

Role: `user`  
Context: `any`  
Usage: `,s/old/new/`

Examples:

- `,s/teh/the/`

## tell

Category: `utility`

Store and deliver messages for users when they join a room again.

### `,tell`

Leave a message for another user.

Role: `user`  
Context: `any`  
Usage: `,tell <nick> <message>`

Examples:

- `,tell alice I fixed it`

## tools

Category: `utility`

Utility commands: ping/pong, message echo, timezone-aware time/date lookups, and Unix timestamp conversion

### `,date`

Show the current date.

Role: `user`  
Context: `any`  
Usage: `,date [timezone]`

Examples:

- `,date`

### `,echo`

Echo text back to you.

Role: `user`  
Context: `any`  
Usage: `,echo <text>`

Examples:

- `,echo hello`

### `,ping`

Check whether the bot is alive.

Role: `user`  
Context: `any`  
Usage: `,ping`

Aliases: `,pong`

Examples:

- `,ping`

### `,seen`

Show when a user was last seen.

Role: `user`  
Context: `any`  
Usage: `,seen <nick|jid>`

Aliases: `,s`

Examples:

- `,seen alice`

### `,time`

Show the current time.

Role: `user`  
Context: `any`  
Usage: `,time [timezone]`

Aliases: `,t`

Examples:

- `,time Europe/Berlin`

### `,tools`

Enable, disable or show room access to utility commands.

Role: `moderator`  
Context: `room or MUC PM`  
Usage: `,tools <on|off|status>`

Examples:

- `,tools status`

### `,ts`

Convert or show Unix timestamps.

Role: `user`  
Context: `any`  
Usage: `,ts [timestamp]`

Examples:

- `,ts`

### `,utc`

Show current UTC time.

Role: `user`  
Context: `any`  
Usage: `,utc`

Examples:

- `,utc`

## urlcheck

Category: `info`

URL title and YouTube info fetcher for groupchats

### `,urlcheck`

Check URLs for status and metadata.

Role: `user`  
Context: `any`  
Usage: `,urlcheck <url>`

Examples:

- `,urlcheck https://envs.net`

## users

Category: `core`

User management with caching, nick lookup and logging

### `,users admins`

List users with admin-level roles.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,users admins [all|page|last]`

Aliases: `,user admin`, `,user admins`, `,users admin`

Examples:

- `,users admins`

### `,users delete`

Delete one user record and its runtime data.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,users delete <jid>`

Aliases: `,user delete`

Examples:

- `,users delete alice@example.org`

### `,users info`

Show user info by JID or known nickname.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,users info <jid|nick>`

Aliases: `,user info`

Examples:

- `,users info alice@example.org`

### `,users list`

List users currently known in one joined room.

Role: `admin`  
Context: `private chat only`  
Usage: `,users list [room_jid]`

Aliases: `,user list`

Examples:

- `,users list test@conference.example.org`

### `,users role`

Change a user's global bot role.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,users role <jid> <role>`

Aliases: `,user role`

Examples:

- `,users role alice@example.org trusted`

### `,users roles`

Show available roles and their ordering.

Role: `admin`  
Context: `private chat / MUC PM`  
Usage: `,users roles`

Aliases: `,user roles`

Examples:

- `,users roles`

## vcard

Category: `info`

Lookup and display vCard of a MUC occupant by MUC JID only

### `,birthday`

Show or set your birthday.

Role: `user`  
Context: `any`  
Usage: `,birthday [YYYY-MM-DD]`

Aliases: `,b`

Examples:

- `,birthday 1989-01-01`

### `,emails`

Show or set profile emails.

Role: `user`  
Context: `any`  
Usage: `,emails [email]`

Aliases: `,e`

Examples:

- `,emails me@example.org`

### `,fullname`

Show or set your full name.

Role: `user`  
Context: `any`  
Usage: `,fullname [name]`

Aliases: `,f`

Examples:

- `,fullname Sven`

### `,nicknames`

Show or set profile nicknames.

Role: `user`  
Context: `any`  
Usage: `,nicknames [names]`

Aliases: `,nicks`

Examples:

- `,nicks Sven, creme`

### `,notes`

Show or set profile notes.

Role: `user`  
Context: `any`  
Usage: `,notes [text]`

Examples:

- `,notes likes boring tech`

### `,organisations`

Show or set organisations in your profile.

Role: `user`  
Context: `any`  
Usage: `,organisations [text]`

Aliases: `,orgs`

Examples:

- `,orgs envs.net`

### `,timezone`

Show your configured timezone.

Role: `user`  
Context: `any`  
Usage: `,timezone`

Aliases: `,tz`

Examples:

- `,tz`

### `,timezone set`

Set your timezone in the bot profile.

Role: `user`  
Context: `any`  
Usage: `,timezone set <IANA timezone>`

Aliases: `,tz set`

Examples:

- `,tz set Europe/Berlin`

### `,urls`

Show or set profile URLs.

Role: `user`  
Context: `any`  
Usage: `,urls [url]`

Aliases: `,u`

Examples:

- `,urls https://envs.net`

### `,vcard`

Show your bot profile/vCard data.

Role: `user`  
Context: `any`  
Usage: `,vcard`

Aliases: `,v`

Examples:

- `,vcard`

## weather

Category: `info`

Gives weather according to users location (supports MUCsand MUC DMs)

### `,weather`

Show weather for a location.

Role: `user`  
Context: `any`  
Usage: `,weather <location>`

Aliases: `,w`

Examples:

- `,weather Berlin`

## xkcd

Category: `fun`

XKCD comic fetcher and broadcaster with full indexing

### `,xkcd`

Show an XKCD comic.

Role: `user`  
Context: `any`  
Usage: `,xkcd [latest|random|number]`

Examples:

- `,xkcd random`

## xmpp

Category: `tools`

XMPP utility tools (ping, diagnostics, service discovery, DNS SRV, etc.)

### `,xmpp`

Enable, disable or show room access to XMPP lookup commands.

Role: `user`  
Context: `room or MUC PM`  
Usage: `,xmpp <on|off|status>`

Aliases: `,x`

Examples:

- `,xmpp status`

### `,xmpp compliance`

Check XMPP compliance features via disco.

Role: `user`  
Context: `any`  
Usage: `,xmpp compliance <jid>`

Aliases: `,x compliance`

Examples:

- `,x compliance envs.net`

### `,xmpp contact`

Show contact addresses from service discovery.

Role: `user`  
Context: `any`  
Usage: `,xmpp contact <jid>`

Aliases: `,x contact`

Examples:

- `,x contact envs.net`

### `,xmpp help`

Show help for XMPP lookup subcommands.

Role: `user`  
Context: `any`  
Usage: `,xmpp help`

Aliases: `,x help`

Examples:

- `,x help`

### `,xmpp info`

Show service discovery identity/features.

Role: `user`  
Context: `any`  
Usage: `,xmpp info <jid>`

Aliases: `,x info`

Examples:

- `,x info conference.envs.net`

### `,xmpp items`

List service discovery items.

Role: `user`  
Context: `any`  
Usage: `,xmpp items <jid>`

Aliases: `,x items`

Examples:

- `,x items envs.net`

### `,xmpp ping`

Ping an XMPP entity.

Role: `user`  
Context: `any`  
Usage: `,xmpp ping <jid>`

Aliases: `,x ping`

Examples:

- `,x ping envs.net`

### `,xmpp srv`

Look up XMPP DNS SRV records.

Role: `user`  
Context: `any`  
Usage: `,xmpp srv <domain>`

Aliases: `,x srv`

Examples:

- `,x srv envs.net`

### `,xmpp uptime`

Query XMPP entity uptime.

Role: `user`  
Context: `any`  
Usage: `,xmpp uptime <jid>`

Aliases: `,x uptime`

Examples:

- `,x uptime envs.net`

### `,xmpp version`

Query XMPP software version via XEP-0092.

Role: `user`  
Context: `any`  
Usage: `,xmpp version <jid>`

Aliases: `,x version`

Examples:

- `,x version envs.net`
