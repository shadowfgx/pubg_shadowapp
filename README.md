# PUBG ShadowApp Discord Bot

Bot de Discord para consultar estadisticas de PUBG y gestionar listas de scrims. Usa MySQL como base de datos.

## Requisitos

- Python 3.14 o compatible
- MySQL 8 si arrancas sin Docker
- Token de bot de Discord
- Token de PUBG API

## Configuracion

Copia el ejemplo de variables:

```powershell
Copy-Item .env.example .env
```

Edita `.env` y rellena como minimo:

```env
DISCORD_TOKEN=...
PUBG_API_TOKEN=...
DB_NAME=pubg_shadowapp
DB_USER=shadowbot
DB_PASSWORD=shadowpass
```

El proyecto tambien sigue aceptando `config/.env`, pero se recomienda `.env` en la raiz.

## Arranque local con Docker

Es la forma mas simple porque levanta bot y MySQL juntos:

```powershell
docker compose up --build
```

La base de datos queda persistida en el volumen `mysql-data`. El bot crea automaticamente las tablas `users` y `scrims` al arrancar.

## Arranque local sin Docker

Crea y activa el entorno:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Arranca MySQL local y crea la base/usuario si no existen:

```sql
CREATE DATABASE pubg_shadowapp;
CREATE USER 'shadowbot'@'%' IDENTIFIED BY 'shadowpass';
GRANT ALL PRIVILEGES ON pubg_shadowapp.* TO 'shadowbot'@'%';
FLUSH PRIVILEGES;
```

Ejecuta el bot:

```powershell
python -m src.bot
```

## Despliegue productivo

Opcion simple con Docker Compose en el servidor:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
```

Para ver logs:

```powershell
docker compose logs -f bot
```

Para parar:

```powershell
docker compose down
```

No uses tokens reales en git. `.env` esta ignorado por `.gitignore`.

## Comandos Discord

```text
!register <usuario_pubg>
!stats [usuario_pubg]
!ranked [usuario_pubg]
!scrims
!notscrims
!scrape
```

`!stats` y `!ranked` abren un flujo de dos desplegables:

```text
1. Seleccionar temporada
2. Seleccionar modo disponible: Solo/Duo/Squad y FPP/TPP
```

Solo se muestran modos con partidas jugadas en esa temporada.

## Estructura del codigo

```text
src/bot/main.py              # Crea y arranca ShadowBot
src/bot/cogs/players.py      # Comandos de jugadores: register, stats
src/bot/cogs/scrims.py       # Comandos de scrims: scrims, notscrims
src/bot/cogs/tournaments.py  # Comandos de torneos/scraping: scrape
src/api/api_client.py        # Cliente de PUBG API
src/db/database.py           # Conexion MySQL y creacion de tablas
config/init.py               # Carga y valida configuracion
```

## Añadir nuevas funcionalidades

La forma recomendada es crear un nuevo cog en `src/bot/cogs/` y registrarlo en `COGS` dentro de `src/bot/main.py`.

Ejemplo minimo:

```python
from discord.ext import commands


class ExampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping_command(self, ctx):
        await ctx.send("pong")


async def setup(bot):
    await bot.add_cog(ExampleCog(bot))
```

Los cogs pueden usar dependencias compartidas desde `self.bot`:

```python
self.bot.db
self.bot.pubg_client
self.bot.config
self.bot.project_root
```
