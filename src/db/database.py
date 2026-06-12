import aiomysql
import asyncio

class Database:
    def __init__(self, config):
        self.config = config
        self.pool = None

    async def connect(self, retries=10, delay=3):
        """ Crea el pool de conexiones a MySQL con los datos del .env. """
        for attempt in range(1, retries + 1):
            try:
                self.pool = await aiomysql.create_pool(
                    host=self.config["DB_HOST"],
                    port=int(self.config["DB_PORT"]),
                    user=self.config["DB_USER"],
                    password=self.config["DB_PASSWORD"],
                    db=self.config["DB_NAME"],
                    autocommit=False,
                )
                print(f"Conectado a MySQL en {self.config['DB_HOST']}:{self.config['DB_PORT']}")
                return
            except Exception:
                if attempt == retries:
                    raise
                print(f"MySQL no esta listo. Reintentando ({attempt}/{retries})...")
                await asyncio.sleep(delay)

    async def close(self):
        """ Cierra el pool de conexiones. """
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            print("Conexion MySQL cerrada")

    async def execute(self, query, *args):
        """
        Ejecuta una consulta que NO retorna filas (INSERT, UPDATE, DELETE, DDL).
        Devuelve el resultado de cur.execute(), generalmente "OK" o el número de filas afectadas.
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Convertimos args a tupla para evitar problemas de placeholders en MySQL
                result = await cur.execute(query, tuple(args))
                await conn.commit()
                return result

    async def fetch(self, query, *args):
        """
        Ejecuta una consulta que retorna filas (SELECT).
        Devuelve una lista de diccionarios (aiomysql.DictCursor).
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, tuple(args))
                return await cur.fetchall()

    async def setup_users_table(self):
        """
        Crea la tabla 'users' si no existe.
        Contiene (discord_id, username, pubg_username).
        """
        await self.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                discord_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255) NOT NULL,
                pubg_username VARCHAR(255)
            )
        """)
        print("Tabla 'users' verificada o creada.")

    async def setup_scrims_table(self):
        """
        Crea la tabla 'scrims' si no existe.
        Almacena la fecha como VARCHAR(10) (dd/mm/yyyy).
        Asegura que un usuario no pueda inscribirse
        más de una vez el mismo día con UNIQUE KEY en (discord_id, scrim_date).
        """
        await self.execute("""
            CREATE TABLE IF NOT EXISTS scrims (
                id INT AUTO_INCREMENT PRIMARY KEY,
                discord_id BIGINT NOT NULL,
                pubg_username VARCHAR(255) NOT NULL,
                scrim_date VARCHAR(10) NOT NULL,
                orden INT NOT NULL,
                UNIQUE KEY unique_scrim (discord_id, scrim_date)
            )
        """)
        print("Tabla 'scrims' verificada o creada.")


    async def setup_all_tables(self):
        """
        (Opcional) Llama a los métodos de creación de tablas 
        para evitar llamar uno a uno en tu `on_ready`.
        """
        await self.setup_users_table()
        await self.setup_scrims_table()
        print("Todas las tablas fueron verificadas o creadas.")
