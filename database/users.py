class Users:
    """
    Users table manager.
    """

    def __init__(self, conn):

        self.conn = conn

    async def init(self):

        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                jid TEXT PRIMARY KEY,
                nickname TEXT,
                role INTEGER DEFAULT 5,
                last_seen TEXT,
                banned INTEGER DEFAULT 0
            )
            """
        )

        await self.conn.commit()

    async def add(self, jid, role=5, nickname=None):

        await self.conn.execute(
            "INSERT OR REPLACE INTO users (jid, role, nickname) VALUES (?, ?, ?)",
            (jid, role, nickname)
        )

        await self.conn.commit()

    async def delete(self, jid):

        await self.conn.execute(
            "DELETE FROM users WHERE jid = ?",
            (jid,)
        )

        await self.conn.commit()

    async def update(self, jid, **fields):

        keys = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values())

        await self.conn.execute(
            f"UPDATE users SET {keys} WHERE jid=?",
            (*values, jid)
        )

        await self.conn.commit()

    async def list(self):

        cursor = await self.conn.execute(
            "SELECT jid, nickname, role, last_seen, banned FROM users"
        )

        return await cursor.fetchall()
