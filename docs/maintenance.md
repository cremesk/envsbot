# Maintenance

This document covers maintenance tasks that should be run by the server administrator outside the running bot process.

## SQLite database maintenance

Do not run `VACUUM` from a live bot command. `VACUUM` rewrites the SQLite database file and should be performed during a planned maintenance window while envsbot is stopped.

Recommended manual procedure:

```bash
systemctl stop envsbot.service

sqlite3 envsbot.db "PRAGMA integrity_check;"
sqlite3 envsbot.db "PRAGMA optimize;"
sqlite3 envsbot.db "VACUUM;"

systemctl start envsbot.service
```

Adjust the service name and database path if your installation uses different names.

For a quick online status check from the bot, use:

```text
,db status
```
