import requests


class PUBGAPIClient:
    def __init__(self, api_key, base_url, shard):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.shard = shard
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/vnd.api+json",
        }

    def get_seasons(self, limit=25):
        url = f"{self.base_url}/shards/{self.shard}/seasons"
        data = self._get(url)

        seasons = []
        for season in data.get("data", []):
            attributes = season.get("attributes", {})
            seasons.append({
                "id": season["id"],
                "is_current": attributes.get("isCurrentSeason", False),
                "is_offseason": attributes.get("isOffseason", False),
            })

        seasons.sort(key=lambda item: (item["is_current"], item["id"]), reverse=True)
        return seasons[:limit]

    def get_player_id(self, player_name):
        url = f"{self.base_url}/shards/{self.shard}/players?filter[playerNames]={player_name}"
        data = self._get(url)
        return data["data"][0]["id"]

    def get_normal_season_stats(self, player_name, season_id):
        player_id = self.get_player_id(player_name)
        url = f"{self.base_url}/shards/{self.shard}/players/{player_id}/seasons/{season_id}"
        data = self._get(url)
        return data["data"]["attributes"].get("gameModeStats", {})

    def get_ranked_season_stats(self, player_name, season_id):
        player_id = self.get_player_id(player_name)
        url = f"{self.base_url}/shards/{self.shard}/players/{player_id}/seasons/{season_id}/ranked"
        data = self._get(url)
        return data["data"]["attributes"].get("rankedGameModeStats", {})

    def format_normal_stats(self, season_stats, player_name, season_id, game_mode):
        stats = season_stats.get(game_mode)
        if not stats:
            return {"error": f"No se encontraron estadisticas normales para {game_mode} en esta temporada."}

        return self._normal_stats_response(stats, player_name, season_id, game_mode)

    def format_ranked_stats(self, season_stats, player_name, season_id, game_mode):
        stats = season_stats.get(game_mode)
        if not stats:
            return {"error": f"No se encontraron estadisticas ranked para {game_mode} en esta temporada."}

        return self._ranked_stats_response(stats, player_name, season_id, game_mode)

    def _get(self, url):
        response = requests.get(url, headers=self.headers, timeout=20)
        response.raise_for_status()
        return response.json()

    def _normal_stats_response(self, stats, player_name, season_id, game_mode):
        rounds_played = stats.get("roundsPlayed", 0)
        wins = stats.get("wins", 0)
        kills = stats.get("kills", 0)
        assists = stats.get("assists", 0)
        losses = stats.get("losses", 0)
        damage_dealt = stats.get("damageDealt", 0)
        headshot_kills = stats.get("headshotKills", 0)

        return {
            "type": "normal",
            "player_name": player_name,
            "season_id": season_id,
            "game_mode": game_mode,
            "kills": kills,
            "assists": assists,
            "deaths": losses,
            "kda": round((kills + assists) / losses, 2) if losses > 0 else kills + assists,
            "adr": round(damage_dealt / rounds_played) if rounds_played > 0 else 0,
            "damageDealt": round(damage_dealt),
            "wins": wins,
            "top10s": stats.get("top10s", 0),
            "roundsPlayed": rounds_played,
            "winRatio": round((wins / rounds_played) * 100, 2) if rounds_played > 0 else 0,
            "headshotKills": headshot_kills,
            "headshotRatio": round((headshot_kills / kills) * 100, 2) if kills > 0 else 0,
            "longestKill": round(stats.get("longestKill", 0), 1),
            "dbnos": stats.get("dBNOs", stats.get("dbnos", 0)),
        }

    def _ranked_stats_response(self, stats, player_name, season_id, game_mode):
        rounds_played = stats.get("roundsPlayed", 0)
        wins = stats.get("wins", 0)
        kills = stats.get("kills", 0)
        assists = stats.get("assists", 0)
        deaths = stats.get("deaths", 0)
        damage_dealt = stats.get("damageDealt", 0)
        headshot_kills = stats.get("headshotKills", 0)
        tier_data = stats.get("currentTier", {})
        tier = f"{tier_data.get('tier', 'Unranked')} {tier_data.get('subTier', '')}".strip()

        return {
            "type": "ranked",
            "player_name": player_name,
            "season_id": season_id,
            "game_mode": game_mode,
            "tier": tier,
            "rankPoints": stats.get("currentRankPoint", 0),
            "kills": kills,
            "assists": assists,
            "deaths": deaths,
            "kda": round(stats.get("kda", 0), 2),
            "adr": round(damage_dealt / rounds_played) if rounds_played > 0 else 0,
            "damageDealt": round(damage_dealt),
            "wins": wins,
            "roundsPlayed": rounds_played,
            "winRatio": round((wins / rounds_played) * 100, 2) if rounds_played > 0 else 0,
            "headshotKills": headshot_kills,
            "headshotRatio": round((headshot_kills / kills) * 100, 2) if kills > 0 else 0,
            "dbnos": stats.get("dBNOs", stats.get("dbnos", 0)),
        }
