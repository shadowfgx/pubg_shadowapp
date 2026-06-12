import os

import discord
from discord.ext import commands

from config.init import load_config
from src.api.api_client import PUBGAPIClient
from src.db.database import Database


COGS = (
    "src.bot.cogs.players",
    "src.bot.cogs.scrims",
    "src.bot.cogs.tournaments",
)


class ShadowBot(commands.Bot):
    def __init__(self, config, project_root):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        self.config = config
        self.project_root = project_root
        self.db = Database(config)
        self.pubg_client = PUBGAPIClient(
            api_key=config["PUBG_API_TOKEN"],
            base_url=config["PUBG_API_URL"],
            shard=config["PUBG_SHARD"],
        )

    async def setup_hook(self):
        await self.db.connect()
        await self.db.setup_all_tables()

        for cog in COGS:
            await self.load_extension(cog)

    async def close(self):
        await self.db.close()
        await super().close()

    async def on_ready(self):
        print(f"Bot conectado como {self.user} y base de datos lista.")


def create_bot():
    config = load_config()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return ShadowBot(config=config, project_root=project_root)


def run_bot():
    bot = create_bot()
    bot.run(bot.config["DISCORD_TOKEN"])


if __name__ == "__main__":
    run_bot()
