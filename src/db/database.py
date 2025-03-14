import aiomysql
from config.init import load_config

cfg = load_config()

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await aiomysql.create_pool(
            host=cfg["DB_HOST"],
            port=int(cfg["DB_PORT"]),
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            db=cfg["DB_NAME"]
        )
        print("✅ Conectado a la base de datos MySQL en Cybrancee")

    async def close(self):
        self.pool.close()
        await self.pool.wait_closed()
        print("❌ Conexión cerrada")

    async def execute1(self, query, *args):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                await conn.commit()

    async def execute(self, query, *args):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, tuple(args))  # ✅ Convierte los argumentos en una tupla correctamente
                await conn.commit()

           


    async def fetch1(self, query, *args):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, args)
                return await cur.fetchall()
            
    async def fetch(self, query, *args):
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, tuple(args))  # ✅ Convierte los argumentos en una tupla correctamente
                return await cur.fetchall()


            
    async def setup_database(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        discord_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(255) NOT NULL,
                        pubg_username VARCHAR(255)
                    )
                """)
                await conn.commit()
        print("✅ Tabla 'users' verificada o creada.")


db = Database()
