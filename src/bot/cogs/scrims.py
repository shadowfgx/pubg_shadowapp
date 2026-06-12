import datetime

import discord
from discord.ext import commands


class ScrimsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="scrims")
    async def scrims_command(self, ctx):
        """Apunta al autor a las scrims del dia."""
        user_id = ctx.author.id
        username = ctx.author.name

        registered_user = await self.bot.db.fetch("SELECT pubg_username FROM users WHERE discord_id = %s", user_id)
        if not registered_user:
            await ctx.send(f"{username}, no has registrado tu PUBG username. Usa `!register <nombre>`.")
            return

        pubg_username = registered_user[0]["pubg_username"]
        today_str = self._today()
        new_order = await self._next_order(today_str)

        try:
            await self.bot.db.execute(
                "INSERT INTO scrims (discord_id, pubg_username, scrim_date, orden) VALUES (%s, %s, %s, %s)",
                user_id,
                pubg_username,
                today_str,
                new_order,
            )
            await ctx.send(f"{username}, te has apuntado a scrims de hoy ({today_str}).")
        except Exception as e:
            if "Duplicate entry" in str(e):
                await ctx.send(f"{username}, ya estabas apuntado a las scrims de hoy.")
            else:
                await ctx.send(f"Ocurrio un error apuntandote: {e}")
                return

        await self._send_scrims_list(ctx, today_str)

    @commands.command(name="notscrims")
    async def notscrims_command(self, ctx):
        """Da de baja al autor de las scrims del dia."""
        user_id = ctx.author.id
        username = ctx.author.name

        registered_user = await self.bot.db.fetch("SELECT pubg_username FROM users WHERE discord_id = %s", user_id)
        if not registered_user:
            await ctx.send(f"{username}, no estas registrado en la base de datos.")
            return

        today_str = self._today()
        result = await self.bot.db.execute(
            "DELETE FROM scrims WHERE discord_id = %s AND scrim_date = %s",
            user_id,
            today_str,
        )

        if result == 0:
            await ctx.send(f"{username}, no estabas apuntado para hoy.")
        else:
            await ctx.send(f"{username}, te has dado de baja de scrims para hoy ({today_str}).")

        await self._send_scrims_list(ctx, today_str)

    def _today(self):
        return datetime.datetime.now().strftime("%d/%m/%Y")

    async def _next_order(self, today_str):
        max_order = await self.bot.db.fetch(
            "SELECT COALESCE(MAX(orden), 0) AS max_orden FROM scrims WHERE scrim_date = %s",
            today_str,
        )
        return max_order[0]["max_orden"] + 1

    async def _send_scrims_list(self, ctx, today_str):
        scrims_today = await self.bot.db.fetch(
            "SELECT pubg_username, orden FROM scrims WHERE scrim_date = %s ORDER BY orden ASC",
            today_str,
        )

        if not scrims_today:
            await ctx.send(f"No hay nadie inscrito para hoy ({today_str}).")
            return

        embed = discord.Embed(
            title=f"Scrims de hoy - {today_str}",
            description="Jugadores inscritos",
            color=0x1abc9c,
        )
        players_list = "\n".join([f"`{row['orden']}.` **{row['pubg_username']}**" for row in scrims_today])
        embed.add_field(name="Inscritos", value=players_list, inline=False)
        embed.set_footer(text="Shadowapp al servicio")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ScrimsCog(bot))
