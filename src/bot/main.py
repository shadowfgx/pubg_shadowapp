import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv("config/.env")
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

bot.run(TOKEN)
