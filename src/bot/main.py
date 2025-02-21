# src/bot/main.py
import discord
from discord.ext import commands
import json
import os

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
            msg = (
                f"**Estadísticas de {player_name} (modo squad)**\n"
                f"Tier: {stats['tier']}\n"
                f"Kills: {stats['kills']}\n"
                f"Wins: {stats['wins']}\n"
                f"ADR: {stats['adr']}\n"
                f"Partidas jugadas: {stats['roundsPlayed']}\n"
                f"Ratio de victoria: {stats['winRatio']}%\n"
            )
            await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"Ocurrió un error obteniendo stats de {player_name}: {str(e)}")

# Inicia el bot
def run_bot():
    bot.run(cfg["DISCORD_TOKEN"])

if __name__ == "__main__":
    run_bot()
