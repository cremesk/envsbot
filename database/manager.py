import aiosqlite

from .users import Users
from .rooms import Rooms


class DatabaseManager:
    """
    Central database manager.

    Handles the SQLite connection and exposes
    table managers for users and rooms.
    """

    def __init__(self, path: str):

        self.path = path
        self.conn = None

        self.users = None
        self.rooms = None

    async def connect(self):
        """Open the database connection and initialize tables."""

        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row

        self.users = Users(self.conn)
        self.rooms = Rooms(self.conn)

        await self.users.init()
        await self.rooms.init()

    async def close(self):
        """Close the database connection."""

        if self.conn:
            await self.conn.close()
