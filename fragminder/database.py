import aiosqlite

__all__ = ['fmdb']

class fmdb (object):

    @classmethod
    async def open(cls, filename):
        res = cls(await aiosqlite.connect(filename))
        await res._init()
        return res

    def __init__(self, connection):
        self._conn = connection
        self._conn.row_factory = aiosqlite.Row

    async def _init(self):
        await self._run_ddl()
    
    async def _run_ddl(self):
        await self._conn.execute("""
            create table if not exists user_t (
                user_id integer primary key autoincrement,
                discord_name text unique not null,
                steam_id integer not null
            )
        """)

        await self._conn.execute("""
            create table if not exists weapon_t (
                weapon_id integer primary key autoincrement,
                user_id integer not null,
                name text not null,
                asset_id text not null unique,
                last_check integer null,
                foreign key (user_id) references user_t (user_id),
                unique (user_id, name)
            )
        """)

        await self._conn.execute("""
            create table if not exists watch_t (
                watch_id integer primary key autoincrement,
                weapon_id integer not null,
                count integer not null,
                foreign key (weapon_id) references weapon_t (weapon_id),
                unique (weapon_id, count)
            )
        """)

        await self._conn.commit()

    async def add_user(self, discord_name, steam_id):
        await self._conn.execute("insert into user_t (discord_name, steam_id) values (?, ?)", (discord_name, steam_id))
        await self._conn.commit()

    async def add_weapon(self, user_id, asset_id, name):
        await self._conn.execute("insert into weapon_t (user_id, asset_id, name) values (?, ?, ?)", (user_id, asset_id, name))
        await self._conn.commit()

    async def add_watch(self, weapon_id, count):
        await self._conn.execute("insert into watch_t (weapon_id, count) values (?, ?)", (weapon_id, count))
        await self._conn.commit()

    async def get_users(self):
        res = []
        async with self._conn.execute("select * from user_t") as c:
            async for row in c:
                res.append((row['user_id'], row['discord_name'], row['steam_id']))
        return res

    async def get_user_id(self, discord_name):
        async with self._conn.execute("select * from user_t where discord_name = ?", (discord_name,)) as c:
            async for row in c:
                return row['user_id']
        return None

    async def get_weapon_id(self, user_id, name):
        async with self._conn.execute("select * from weapon_t where name = ? and user_id = ?", (name, user_id)) as c:
            async for row in c:
                return row['weapon_id']
        return None

    async def get_user_weapons(self, user_id):
        res = []
        async with self._conn.execute("select * from weapon_t where user_id = ?", (user_id,)) as c:
            async for row in c:
                res.append((row['weapon_id'], row['name']))
        return res
