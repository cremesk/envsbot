class Rooms:
    """
    Rooms table manager.
    """

    def __init__(self, conn):

        self.conn = conn

    async def init(self):

        await self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                room_jid TEXT PRIMARY KEY,
                nick TEXT,
                autojoin INTEGER DEFAULT 0,
                status TEXT
            )
            """
        )

        await self.conn.commit()

    async def add(self, room_jid, nick, autojoin=False):

        await self.conn.execute(
            "INSERT OR REPLACE INTO rooms (room_jid, nick, autojoin) VALUES (?, ?, ?)",
            (room_jid, nick, int(autojoin))
        )

        await self.conn.commit()

    async def delete(self, room_jid):

        await self.conn.execute(
            "DELETE FROM rooms WHERE room_jid = ?",
            (room_jid,)
        )

        await self.conn.commit()

    async def update(self, room_jid, **fields):

        keys = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values())

        await self.conn.execute(
            f"UPDATE rooms SET {keys} WHERE room_jid=?",
            (*values, room_jid)
        )

        await self.conn.commit()

    async def list(self):

        cursor = await self.conn.execute(
            "SELECT room_jid, nick, autojoin, status FROM rooms"
        )

        return await cursor.fetchall()

    async def get(self, room_jid):

        cursor = await self.conn.execute(
            "SELECT room_jid, nick, autojoin, status FROM rooms WHERE room_jid=?",
            (room_jid,)
        )

        return await cursor.fetchone()
