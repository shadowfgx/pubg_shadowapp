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
    print(f"Bot conectado como {bot.user}")

@bot.command(name="stats")
async def stats_command(ctx, player_name: str):
    """
    Comando de Discord para obtener estadísticas de un jugador en PUBG.
    Uso: !stats <nombredeusuario>
    """
    try:
        stats = pubg_client.get_player_stats(player_name)

        if "error" in stats:
            await ctx.send(f"Error: {stats['error']}")
        else:
            # Crea un embed con título, descripción y color
            embed = discord.Embed(
                title=f"Estadísticas de {player_name}",
                description="Modo Squad",
                color=0x1abc9c  # Un color en formato hexadecimal (este es un verde/azul "teal")
            )

            # Añade campos (name, value) y decide si serán inline o no
            embed.add_field(name="Tier", value=stats['tier'], inline=True)
            embed.add_field(name="KDA", value=stats['kda'], inline=True)
            embed.add_field(name="Kills", value=stats['kills'], inline=True)
            embed.add_field(name="ADR", value=stats['adr'], inline=True)
            embed.add_field(name="Wins", value=stats['wins'], inline=True)
            embed.add_field(name="Partidas jugadas", value=stats['roundsPlayed'], inline=True) 
            embed.add_field(name="Ratio de victoria", value=f"{stats['winRatio']}%", inline=True)

            # Puedes poner una miniatura (por ejemplo, un logo de PUBG)
            #embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/en/2/2f/PlayerUnknown%27s_Battlegrounds_cover.jpg")

            # Puedes poner un footer con un texto
            #embed.set_footer(text="Consulta generada con la API de PUBG")

            # Finalmente, envías el embed
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Ocurrió un error obteniendo stats de {player_name}: {str(e)}")

# Inicia el bot
def run_bot():
    bot.run(cfg["DISCORD_TOKEN"])

if __name__ == "__main__":
    run_bot()
