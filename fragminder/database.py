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
            create table if not exists guild_t (
                guild_id integer primary key,
                channel_id integer null
            )
        """)

        await self._conn.execute("""
            create table if not exists user_t (
                user_id integer primary key autoincrement,
                guild_id integer not null references guild_t (guild_id),
                discord_id integer not null,
                steam_id integer not null,
                unique (guild_id, discord_id)
            )
        """)

        await self._conn.execute("""
            create table if not exists weapon_t (
                weapon_id integer primary key autoincrement,
                user_id integer not null,
                name text not null,
                asset_id integer not null unique,
                last_count integer null,
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

    async def add_or_update_guild(self, guild_id, channel_id=None):
        if channel_id:
            await self._conn.execute("replace into guild_t (guild_id, channel_id) values (?, ?)", (guild_id, channel_id))
        else:
            await self._conn.execute("insert into guild_t (guild_id) values (?) on conflict do nothing", (guild_id,))
        await self._conn.commit()

    async def add_user(self, guild_id, discord_id, steam_id):
        await self._conn.execute("insert into user_t (guild_id, discord_id, steam_id) values (?, ?, ?)", (guild_id, discord_id, steam_id))
        await self._conn.commit()

    async def add_weapon(self, user_id, asset_id, name):
        await self._conn.execute("insert into weapon_t (user_id, asset_id, name) values (?, ?, ?)", (user_id, asset_id, name))
        await self._conn.commit()

    async def add_watch(self, weapon_id, count):
        await self._conn.execute("insert into watch_t (weapon_id, count) values (?, ?)", (weapon_id, count))
        await self._conn.commit()

    async def get_guild(self, guild_id):
        async with self._conn.execute("select * from guild_t where guild_id = ?", (guild_id, )) as c:
            async for row in c:
                return row['channel_id']

    async def get_users(self):
        res = []
        async with self._conn.execute("select * from user_t") as c:
            async for row in c:
                res.append((row['guild_id'], row['user_id'], row['discord_id'], row['steam_id']))
        return res

    async def get_user_id(self, guild_id, discord_id):
        async with self._conn.execute("select * from user_t where guild_id = ? and discord_id = ?", (guild_id, discord_id,)) as c:
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
                res.append((row['weapon_id'], row['name'], row['last_count']))
        return res

    async def get_user_watches(self, user_id):
        res = []
        async with self._conn.execute("""\
            select watch_id, weapon_t.weapon_id, asset_id, count, name, last_count, last_check
            from watch_t
            left join weapon_t on watch_t.weapon_id = weapon_t.weapon_id
            where weapon_t.user_id = ?\
        """, (user_id,)) as c:
            async for row in c:
                res.append((row['watch_id'], row['weapon_id'], row['name'], row['asset_id'], row['count'], row['last_count'], row['last_check']))
        return res

    async def update_weapon(self, weapon_id, last_count, last_check):
        await self._conn.execute("""\
            update weapon_t
            set last_count = ?, last_check = ?
            where weapon_id = ?
        """, (last_count, last_check, weapon_id))
        await self._conn.commit()

    async def get_watch_id(self, user_id, name, count):
        async with self._conn.execute("""\
            select watch_id
            from watch_t
            left join weapon_t on watch_t.weapon_id = weapon_t.weapon_id
            where name = ? and count = ? and user_id = ?
        """, (name, count, user_id)) as c:
            async for row in c:
                return row['watch_id']
        return None

    async def remove_watch(self, watch_id):
        await self._conn.execute("delete from watch_t where watch_id = ?", (watch_id,))
        await self._conn.commit()

    async def rename_weapon(self, weapon_id, name):
        await self._conn.execute("update weapon_t set name = ? where weapon_id = ?", (name, weapon_id))
        await self._conn.commit()
