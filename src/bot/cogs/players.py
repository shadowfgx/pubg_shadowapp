import os

import discord
from discord.ext import commands


class PlayersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="register")
    async def register_command(self, ctx, pubg_username: str):
        """Registra o actualiza el usuario de PUBG del autor."""
        user_id = ctx.author.id
        username = ctx.author.name

        existing_user = await self.bot.db.fetch("SELECT * FROM users WHERE discord_id = %s", user_id)

        if existing_user:
            await self.bot.db.execute(
                "UPDATE users SET pubg_username = %s WHERE discord_id = %s",
                pubg_username,
                user_id,
            )
            await ctx.send(f"{username}, tu usuario de PUBG ha sido actualizado a {pubg_username}.")
            return

        await self.bot.db.execute(
            "INSERT INTO users (discord_id, username, pubg_username) VALUES (%s, %s, %s)",
            user_id,
            username,
            pubg_username,
        )
        await ctx.send(f"{username}, has sido registrado como tu usuario de PUBG {pubg_username}.")

    @commands.command(name="stats")
    async def stats_command(self, ctx, player_name: str = None):
        """Muestra estadisticas ranked squad-fpp de PUBG."""
        user_id = ctx.author.id
        username = ctx.author.name

        if player_name is None:
            existing_user = await self.bot.db.fetch("SELECT * FROM users WHERE discord_id = %s", user_id)
            if not existing_user:
                await ctx.send(f"{username}, no has registrado tu usuario de PUBG. Usa `!register <nombredeusuario>`.")
                return
            player_name = existing_user[0]["pubg_username"]

        try:
            stats = self.bot.pubg_client.get_player_stats(player_name)

            if "error" in stats:
                await ctx.send(f"Error: {stats['error']}")
                return

            embed = discord.Embed(
                title=f"Estadisticas de {player_name} \n",
                description="Modo Squad",
                color=0x1abc9c,
            )
            embed.add_field(name="Tier", value=stats["tier"], inline=True)
            embed.add_field(name="KDA", value=stats["kda"], inline=True)
            embed.add_field(name="Kills", value=stats["kills"], inline=True)
            embed.add_field(name="ADR", value=stats["adr"], inline=True)
            embed.add_field(name="Wins", value=stats["wins"], inline=True)
            embed.add_field(name="Partidas jugadas", value=stats["roundsPlayed"], inline=True)
            embed.add_field(name="Ratio de victoria", value=f"{stats['winRatio']}%", inline=True)

            rank_path = self._rank_image_path(stats["tier"])
            file = discord.File(rank_path, filename=os.path.basename(rank_path))
            embed.set_thumbnail(url=f"attachment://{os.path.basename(rank_path)}")

            await ctx.send(file=file, embed=embed)
        except Exception as e:
            await ctx.send(f"Ocurrio un error obteniendo stats de {player_name}: {str(e)}")

    def _rank_image_path(self, tier):
        insignias_dir = os.path.join(self.bot.project_root, "assets", "Insignias")
        rank_filename = tier.replace(" ", "-") + ".png"
        rank_path = os.path.join(insignias_dir, rank_filename)

        if os.path.exists(rank_path):
            return rank_path

        tier_name = tier.split(" ", 1)[0]
        tier_path = os.path.join(insignias_dir, f"{tier_name}.png")
        if os.path.exists(tier_path):
            return tier_path

        return os.path.join(insignias_dir, "Unranked.png")


async def setup(bot):
    await bot.add_cog(PlayersCog(bot))
