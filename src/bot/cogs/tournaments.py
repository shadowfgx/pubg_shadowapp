import requests
from discord.ext import commands


class TournamentsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="scrape")
    async def scrape_command(self, ctx):
        """Obtiene datos del leaderboard de Twire y filtra por equipo."""
        team_name_filter = "fghjkdfas MIX"
        url = "https://tjjkdyimqrb7jjnc6m5rpefjtu.appsync-api.eu-west-1.amazonaws.com/graphql"

        try:
            response = requests.post(url, headers=self._headers(), json=self._payload())
        except requests.exceptions.RequestException as e:
            await ctx.send(f"Error al realizar la peticion: {e}")
            return

        if response.status_code != 200:
            await ctx.send(f"Error al obtener datos. Codigo de estado: {response.status_code}")
            return

        try:
            data = response.json()
            leaderboard = data["data"]["platformStats"]["leaderboard"]
        except (ValueError, KeyError):
            await ctx.send("La respuesta no tiene la estructura esperada.")
            return

        filtered_entries = [
            entry for entry in leaderboard
            if entry.get("teamName", "").lower() == team_name_filter.lower()
        ]

        if not filtered_entries:
            await ctx.send(f"No se encontraron entradas para el equipo '{team_name_filter}'.")
            return

        message = self._format_entries(filtered_entries)
        await ctx.send(f"```{message}```")

    def _headers(self):
        return {
            "accept": "*/*",
            "accept-language": "es-ES,es;q=0.9",
            "content-type": "application/json",
            "origin": "https://twire.gg",
            "referer": "https://twire.gg/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/134.0.0.0 Safari/537.36",
            "x-amz-user-agent": "aws-amplify/2.0.6",
            "x-api-key": "da2-vqpq6wms5ndbvhl2r7kvzbpmfi",
        }

    def _payload(self):
        return {
            "operationName": "PlatformStats",
            "variables": {
                "tournament": "968faa0c-948d-11eb-bab8-f2485b011165-20250319-lobby-3",
                "token": "",
                "filters": None,
                "game": "pubg",
            },
            "query": """
                query PlatformStats($tournament: String!, $token: String, $filters: TournamentStatsFilterInput, $game: String!) {
                  platformStats(tournament: $tournament, token: $token, filters: $filters, game: $game) {
                    leaderboard {
                      username
                      teamName
                      kills
                    }
                  }
                }
            """,
        }

    def _format_entries(self, entries):
        message_lines = []
        for entry in entries:
            username = entry.get("username", "Desconocido")
            team = entry.get("teamName", "Desconocido")
            kills = entry.get("kills", "N/A")
            message_lines.append(f"Usuario: {username} | Equipo: {team} | Kills: {kills}")

        message = "\n".join(message_lines)
        if len(message) > 1900:
            return message[:1900] + "\n[Mensaje recortado]"
        return message


async def setup(bot):
    await bot.add_cog(TournamentsCog(bot))
