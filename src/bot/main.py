# src/bot/main.py
import discord
from discord.ext import commands
import json
import os, sys

# --- INYECCIÓN DEL PATH RAÍZ ---
current_dir = os.path.dirname(os.path.abspath(__file__))  # .../src/bot
# Subimos 2 niveles para llegar a la raíz del proyecto
# 1er nivel: .../src
# 2do nivel: .../TU_PROYECTO
root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, root_dir)
# --------------------------------

from src.api.api_client import PUBGAPIClient
from config.init import load_config
from src.db.database import db

# Carga variables de entorno / config
cfg = load_config()

# Crea intents (requerido por Discord)
intents = discord.Intents.default() 
intents.message_content = True  # ¡Importante habilitarlo!

# Crea el bot con un prefijo
bot = commands.Bot(command_prefix="!", intents=intents)

# Instancia del cliente PUBG
import json

# Carga de config.json para obtener la URL base y shard
base_dir = os.path.dirname(os.path.abspath(__file__))
config_json_path = os.path.join(base_dir, "..", "..", "config", "config.json")

with open(config_json_path, "r") as f:
    config_data = json.load(f)

pubg_client = PUBGAPIClient(
    api_key=cfg["PUBG_API_TOKEN"],
    base_url=config_data["pubg_api_url"],
    shard=config_data["pubg_shard"]
)

@bot.event
async def on_ready():
    await db.connect()
    await db.setup_database()
    print(f"Bot conectado como {bot.user} y base de datos lista.")

@bot.command(name="register")
async def register_command(ctx, pubg_username: str):
    """
    Comando para registrar el nombre de usuario de PUBG.
    Uso: !register <nombredeusuario>
    """
    user_id = ctx.author.id
    username = ctx.author.name

    existing_user = await db.fetch("SELECT * FROM users WHERE discord_id = %s", user_id)

    if existing_user:
        await db.execute("UPDATE users SET pubg_username = %s WHERE discord_id = %s", pubg_username, user_id)
        await ctx.send(f"{username}, tu nombre de PUBG ha sido actualizado a {pubg_username}.")
    else:
        await db.execute("INSERT INTO users (discord_id, username, pubg_username) VALUES (%s, %s, %s)", user_id, username, pubg_username)
        await ctx.send(f"{username}, has sido registrado con el nombre de PUBG {pubg_username}.")

@bot.command(name="stats")
async def stats_command(ctx, player_name: str = None):
    """
    Comando de Discord para obtener estadísticas de un jugador en PUBG.
    Uso:
      !stats <nombredeusuario>   -> obtiene stats de ese usuario
      !stats                     -> si no se pasa nombre, busca en la DB el nombre registrado del autor
    """
    # Obtenemos el ID y nombre de Discord del usuario que ejecutó el comando
    user_id = ctx.author.id
    username = ctx.author.name

    # Si no recibimos un nombre de usuario en el comando...
    if player_name is None:
        # Revisamos en la DB si el usuario está registrado
        existing_user = await db.fetch("SELECT * FROM users WHERE discord_id = %s", user_id)
        if not existing_user:
            await ctx.send(f"{username}, no has registrado tu PUBG username. Usa `!register <nombredeusuario>`.")
            return
        # Tomamos el nombre de PUBG de la base de datos
        player_name = existing_user[0]["pubg_username"]

    # Ahora, hacemos la petición a la API usando el player_name
    try:
        stats = pubg_client.get_player_stats(player_name)

        if "error" in stats:
            await ctx.send(f"Error: {stats['error']}")
        else:
            # Creamos un embed con las estadísticas
            embed = discord.Embed(
                title=f"Estadísticas de {player_name} \n",
                description="Modo Squad",
                color=0x1abc9c
            )
            embed.add_field(name="Tier", value=stats['tier'], inline=True)
            embed.add_field(name="KDA", value=stats['kda'], inline=True)
            embed.add_field(name="Kills", value=stats['kills'], inline=True)
            embed.add_field(name="ADR", value=stats['adr'], inline=True)
            embed.add_field(name="Wins", value=stats['wins'], inline=True)
            embed.add_field(name="Partidas jugadas", value=stats['roundsPlayed'], inline=True)
            embed.add_field(name="Ratio de victoria", value=f"{stats['winRatio']}%", inline=True)

                # ────────── AÑADIMOS LA IMAGEN DE RANGO ──────────
            # Suponiendo que el tier venga en formato "Platinum 5", "Silver 3", etc.
            rank_filename = stats['tier'].replace(" ", "-") + ".png"  # "Platinum-5.png"
            rank_path = os.path.join("assets", "Insignias", rank_filename)

            # Si no existe la imagen, usamos un fallback
            if not os.path.exists(rank_path):
                rank_path = os.path.join("assets", "Insignias", "Unranked.png")

            # Enviamos la imagen como adjunto y la usamos como thumbnail
            file = discord.File(rank_path, filename=os.path.basename(rank_path))
            embed.set_thumbnail(url=f"attachment://{os.path.basename(rank_path)}")

            await ctx.send(file=file, embed=embed)
    except Exception as e:
        await ctx.send(f"Ocurrió un error obteniendo stats de {player_name}: {str(e)}")



# Inicia el bot
def run_bot():
    bot.run(cfg["DISCORD_TOKEN"])

if __name__ == "__main__":
    run_bot()
