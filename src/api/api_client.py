# src/api/api_client.py
import requests
import json
import os

class PUBGAPIClient:
    def __init__(self, api_key, base_url, shard):
        self.api_key = api_key
        self.base_url = base_url
        self.shard = shard
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/vnd.api+json"
        }

    def get_player_id(self, player_name):
        """
        Obtiene el playerId de un jugador a partir de su nombre.
        """
        url = f"{self.base_url}/shards/{self.shard}/players?filter[playerNames]={player_name}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()  # Lanza excepción si la respuesta es 4xx o 5xx
        data = response.json()

        # Asumiendo que existe al menos un jugador:
        player_id = data["data"][0]["id"]
        return player_id

    def get_player_stats(self, player_name):
        """
        Ejemplo simple de cómo podrías obtener stats de un jugador.
        """
        # 1. Obtener el ID del jugador
        player_id = self.get_player_id(player_name)

        season_id = "division.bro.official.pc-2018-36"
        url = f"{self.base_url}/shards/{self.shard}/players/{player_id}/seasons/{season_id}/ranked"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        print(data)
        try:
            squad_stats = data["data"]["attributes"]["rankedGameModeStats"]["squad-fpp"]
            tier = squad_stats["currentTier"]["tier"] + " " + squad_stats["currentTier"]["subTier"]
            kills = squad_stats["kills"]
            wins = squad_stats["wins"]
            rounds_played = squad_stats["roundsPlayed"]
            kda = round(squad_stats["kda"], 2)
            
            # Evitar división por cero
            win_ratio = round((wins / rounds_played) * 100, 2) if rounds_played > 0 else 0
            adr = round (squad_stats['damageDealt']/ rounds_played) if rounds_played > 0 else 0

            return {
                "kills": kills,
                "tier" : tier,
                "wins": wins,
                "adr" : adr,
                "roundsPlayed": rounds_played,
                "kda": kda,
                "winRatio": win_ratio   
            }
        except KeyError:
            return {
                "error": "No se encontraron estadísticas para el modo 'squad' en esta temporada."
            }
