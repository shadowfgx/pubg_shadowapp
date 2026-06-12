import os

import discord
from discord.ext import commands


GAME_MODE_LABELS = {
    "solo": "Solo TPP",
    "solo-fpp": "Solo FPP",
    "duo": "Duo TPP",
    "duo-fpp": "Duo FPP",
    "squad": "Squad TPP",
    "squad-fpp": "Squad FPP",
}

GAME_MODE_ORDER = ("solo", "solo-fpp", "duo", "duo-fpp", "squad", "squad-fpp")


class SeasonSelect(discord.ui.Select):
    def __init__(self, cog, ctx, player_name, stats_type, seasons):
        self.cog = cog
        self.ctx = ctx
        self.player_name = player_name
        self.stats_type = stats_type

        options = [
            discord.SelectOption(label=cog._season_label(season)[:100], value=season["id"])
            for season in seasons
        ]
        super().__init__(placeholder="1. Selecciona una temporada", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Este selector no es para ti.", ephemeral=True)
            return

        season_id = self.values[0]
        await interaction.response.defer()

        try:
            if self.stats_type == "ranked":
                season_stats = self.cog.bot.pubg_client.get_ranked_season_stats(self.player_name, season_id)
            else:
                season_stats = self.cog.bot.pubg_client.get_normal_season_stats(self.player_name, season_id)
        except Exception as e:
            await interaction.followup.send(f"No pude obtener las stats de esa temporada: {str(e)}")
            return

        available_modes = self.cog.available_game_modes(season_stats)
        if not available_modes:
            await interaction.followup.send("No hay modos con partidas jugadas para esa temporada.")
            return

        view = GameModeSelectView(
            self.cog,
            self.ctx,
            self.player_name,
            self.stats_type,
            season_id,
            season_stats,
            available_modes,
        )
        await interaction.followup.send("Selecciona el modo de juego:", view=view)


class GameModeSelect(discord.ui.Select):
    def __init__(self, cog, ctx, player_name, stats_type, season_id, season_stats, available_modes):
        self.cog = cog
        self.ctx = ctx
        self.player_name = player_name
        self.stats_type = stats_type
        self.season_id = season_id
        self.season_stats = season_stats

        options = [
            discord.SelectOption(label=GAME_MODE_LABELS.get(mode, mode), value=mode)
            for mode in available_modes
        ]
        super().__init__(placeholder="2. Selecciona FPP/TPP y modo", min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Este selector no es para ti.", ephemeral=True)
            return

        game_mode = self.values[0]

        if self.stats_type == "ranked":
            stats = self.cog.bot.pubg_client.format_ranked_stats(
                self.season_stats,
                self.player_name,
                self.season_id,
                game_mode,
            )
        else:
            stats = self.cog.bot.pubg_client.format_normal_stats(
                self.season_stats,
                self.player_name,
                self.season_id,
                game_mode,
            )

        if "error" in stats:
            await interaction.response.send_message(f"Error: {stats['error']}")
            return

        embed, file = self.cog.build_stats_response(stats)
        if file is None:
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(file=file, embed=embed)


class SeasonSelectView(discord.ui.View):
    def __init__(self, cog, ctx, player_name, stats_type, seasons):
        super().__init__(timeout=120)
        self.add_item(SeasonSelect(cog, ctx, player_name, stats_type, seasons))


class GameModeSelectView(discord.ui.View):
    def __init__(self, cog, ctx, player_name, stats_type, season_id, season_stats, available_modes):
        super().__init__(timeout=120)
        self.add_item(GameModeSelect(cog, ctx, player_name, stats_type, season_id, season_stats, available_modes))


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
        """Muestra selectores de temporada y modo para estadisticas normales."""
        await self._send_season_selector(ctx, player_name, "normal")

    @commands.command(name="ranked")
    async def ranked_command(self, ctx, player_name: str = None):
        """Muestra selectores de temporada y modo para estadisticas ranked."""
        await self._send_season_selector(ctx, player_name, "ranked")

    async def _send_season_selector(self, ctx, player_name, stats_type):
        player_name = await self._resolve_player_name(ctx, player_name)
        if player_name is None:
            return

        try:
            seasons = self.bot.pubg_client.get_seasons()
        except Exception as e:
            await ctx.send(f"No pude obtener la lista de temporadas: {str(e)}")
            return

        if not seasons:
            await ctx.send("No se encontraron temporadas disponibles.")
            return

        label = "ranked" if stats_type == "ranked" else "normales"
        view = SeasonSelectView(self, ctx, player_name, stats_type, seasons)
        await ctx.send(f"Selecciona la temporada para ver stats {label} de **{player_name}**:", view=view)

    async def _resolve_player_name(self, ctx, player_name):
        if player_name is not None:
            return player_name

        existing_user = await self.bot.db.fetch("SELECT * FROM users WHERE discord_id = %s", ctx.author.id)
        if not existing_user:
            await ctx.send(f"{ctx.author.name}, no has registrado tu usuario de PUBG. Usa `!register <nombredeusuario>`.")
            return None

        return existing_user[0]["pubg_username"]

    def available_game_modes(self, season_stats):
        modes = [mode for mode in GAME_MODE_ORDER if self._has_played(season_stats.get(mode, {}))]
        extra_modes = [mode for mode in season_stats if mode not in GAME_MODE_ORDER and self._has_played(season_stats.get(mode, {}))]
        return modes + extra_modes

    def build_stats_response(self, stats):
        if stats["type"] == "ranked":
            return self._ranked_embed(stats)
        return self._normal_embed(stats)

    def _normal_embed(self, stats):
        embed = discord.Embed(
            title=f"Stats normales de {stats['player_name']}",
            description=f"{GAME_MODE_LABELS.get(stats['game_mode'], stats['game_mode'])} | {stats['season_id']}",
            color=0x3498db,
        )
        embed.add_field(name="Resumen", value=self._summary(stats), inline=False)
        embed.add_field(name="Combate", value=self._combat_stats(stats), inline=True)
        embed.add_field(name="Partidas", value=self._match_stats(stats, include_top10=True), inline=True)
        embed.add_field(name="Daño", value=self._damage_stats(stats, include_longest=True), inline=True)
        embed.set_footer(text="Stats normales PUBG")
        return embed, None

    def _ranked_embed(self, stats):
        embed = discord.Embed(
            title=f"Stats ranked de {stats['player_name']}",
            description=f"{GAME_MODE_LABELS.get(stats['game_mode'], stats['game_mode'])} | {stats['season_id']}",
            color=0x1abc9c,
        )
        embed.add_field(name="Rango", value=f"**{stats['tier']}**\n{self._fmt(stats['rankPoints'])} RP", inline=True)
        embed.add_field(name="Resumen", value=self._summary(stats), inline=True)
        embed.add_field(name="Combate", value=self._combat_stats(stats), inline=True)
        embed.add_field(name="Partidas", value=self._match_stats(stats), inline=True)
        embed.add_field(name="Daño", value=self._damage_stats(stats), inline=True)
        embed.set_footer(text="Stats ranked PUBG")

        rank_path = self._rank_image_path(stats["tier"])
        file = discord.File(rank_path, filename=os.path.basename(rank_path))
        embed.set_thumbnail(url=f"attachment://{os.path.basename(rank_path)}")
        return embed, file

    def _has_played(self, stats):
        return stats.get("roundsPlayed", 0) > 0

    def _summary(self, stats):
        return (
            f"KDA: **{stats['kda']}**\n"
            f"ADR: **{self._fmt(stats['adr'])}**\n"
            f"Winrate: **{stats['winRatio']}%**"
        )

    def _combat_stats(self, stats):
        return (
            f"Kills: **{self._fmt(stats['kills'])}**\n"
            f"Assists: **{self._fmt(stats.get('assists', 0))}**\n"
            f"Deaths: **{self._fmt(stats.get('deaths', 0))}**\n"
            f"DBNOs: **{self._fmt(stats.get('dbnos', 0))}**\n"
            f"Headshots: **{self._fmt(stats.get('headshotKills', 0))}** ({stats.get('headshotRatio', 0)}%)"
        )

    def _match_stats(self, stats, include_top10=False):
        lines = [
            f"Partidas: **{self._fmt(stats['roundsPlayed'])}**",
            f"Wins: **{self._fmt(stats['wins'])}**",
            f"Winrate: **{stats['winRatio']}%**",
        ]
        if include_top10:
            lines.append(f"Top 10: **{self._fmt(stats.get('top10s', 0))}**")
        return "\n".join(lines)

    def _damage_stats(self, stats, include_longest=False):
        lines = [
            f"Total: **{self._fmt(stats.get('damageDealt', 0))}**",
            f"ADR: **{self._fmt(stats['adr'])}**",
        ]
        if include_longest:
            lines.append(f"Longest kill: **{stats.get('longestKill', 0)} m**")
        return "\n".join(lines)

    def _fmt(self, value):
        if isinstance(value, float):
            return f"{value:,.2f}".replace(",", ".")
        return f"{value:,}".replace(",", ".")

    def _season_label(self, season):
        label = season["id"].replace("division.bro.official.", "")
        if season["is_current"]:
            label = f"Actual - {label}"
        if season["is_offseason"]:
            label = f"Offseason - {label}"
        return label

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
