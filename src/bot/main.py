# src/bot/main.py
import discord
from discord.ext import commands
import json
import datetime
import os, sys
import requests

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
from src.db.database import db

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
    await db.connect()
    await db.setup_all_tables()
    print(f"Bot conectado como {bot.user} y base de datos lista.")

@bot.command(name="register")
async def register_command(ctx, pubg_username: str):
    """
    Comando para registrar el nombre de usuario de PUBG.
    Uso: !register <nombredeusuario>
    """
    user_id = ctx.author.id
    username = ctx.author.name

    existing_user = await db.fetch("SELECT * FROM users WHERE discord_id = %s", user_id)

    if existing_user:
        await db.execute("UPDATE users SET pubg_username = %s WHERE discord_id = %s", pubg_username, user_id)
        await ctx.send(f"{username}, tu usuario de PUBG ha sido actualizado a {pubg_username}.")
    else:
        await db.execute("INSERT INTO users (discord_id, username, pubg_username) VALUES (%s, %s, %s)", user_id, username, pubg_username)
        await ctx.send(f"{username}, has sido registrado como tu usuario de PUBG {pubg_username}.")

@bot.command(name="stats")
async def stats_command(ctx, player_name: str = None):
    """
    Comando de Discord para obtener estadísticas de un jugador en PUBG.
    Uso:
      !stats <nombredeusuario>   -> obtiene stats de ese usuario
      !stats                     -> si no se pasa nombre, busca en la DB el nombre registrado del autor
    """
    # Obtenemos el ID y nombre de Discord del usuario que ejecutó el comando
    user_id = ctx.author.id
    username = ctx.author.name

    # Si no recibimos un nombre de usuario en el comando...
    if player_name is None:
        # Revisamos en la DB si el usuario está registrado
        existing_user = await db.fetch("SELECT * FROM users WHERE discord_id = %s", user_id)
        if not existing_user:
            await ctx.send(f"{username}, no has registrado tu usuario de PUBG. Usa `!register <nombredeusuario>`.")
            return
        # Tomamos el nombre de PUBG de la base de datos
        player_name = existing_user[0]["pubg_username"]

    # Ahora, hacemos la petición a la API usando el player_name
    try:
        stats = pubg_client.get_player_stats(player_name)

        if "error" in stats:
            await ctx.send(f"Error: {stats['error']}")
        else:
            # Creamos un embed con las estadísticas
            embed = discord.Embed(
                title=f"Estadísticas de {player_name} \n",
                description="Modo Squad",
                color=0x1abc9c
            )
            embed.add_field(name="Tier", value=stats['tier'], inline=True)
            embed.add_field(name="KDA", value=stats['kda'], inline=True)
            embed.add_field(name="Kills", value=stats['kills'], inline=True)
            embed.add_field(name="ADR", value=stats['adr'], inline=True)
            embed.add_field(name="Wins", value=stats['wins'], inline=True)
            embed.add_field(name="Partidas jugadas", value=stats['roundsPlayed'], inline=True)
            embed.add_field(name="Ratio de victoria", value=f"{stats['winRatio']}%", inline=True)

                # ────────── AÑADIMOS LA IMAGEN DE RANGO ──────────
            # Suponiendo que el tier venga en formato "Platinum 5", "Silver 3", etc.
            rank_filename = stats['tier'].replace(" ", "-") + ".png"  # "Platinum-5.png"
            rank_path = os.path.join("assets", "Insignias", rank_filename)

            # Si no existe la imagen, usamos un fallback
            if not os.path.exists(rank_path):
                rank_path = os.path.join("assets", "Insignias", "Unranked.png")

            # Enviamos la imagen como adjunto y la usamos como thumbnail
            file = discord.File(rank_path, filename=os.path.basename(rank_path))
            embed.set_thumbnail(url=f"attachment://{os.path.basename(rank_path)}")

            await ctx.send(file=file, embed=embed)
    except Exception as e:
        await ctx.send(f"Ocurrió un error obteniendo stats de {player_name}: {str(e)}")


@bot.command(name="scrims")
async def scrims_command(ctx):
    """
    Comando para apuntarse a las scrims del día.
    Uso: !scrims
    """
    user_id = ctx.author.id
    username = ctx.author.name
    
    # 1) Verifica si está en la tabla users
    registered_user = await db.fetch("SELECT pubg_username FROM users WHERE discord_id = %s", user_id)
    if not registered_user:
        await ctx.send(f"{username}, no has registrado tu PUBG username. Usa `!register <nombre>`.")  
        return
    
    pubg_username = registered_user[0]["pubg_username"]
    
    # 2) Fecha de hoy en formato dd/mm/yyyy
    today_str = datetime.datetime.now().strftime("%d/%m/%Y")
    
    # 3) Buscar el máximo orden de hoy
    max_order = await db.fetch(
        "SELECT COALESCE(MAX(orden), 0) AS max_orden FROM scrims WHERE scrim_date = %s",
        today_str
    )
    new_order = max_order[0]["max_orden"] + 1  # Ej: si no hay nadie, será 1
    
    # 4) Insertar con el nuevo orden
    try:
        await db.execute(
            "INSERT INTO scrims (discord_id, pubg_username, scrim_date, orden) VALUES (%s, %s, %s, %s)",
            user_id, pubg_username, today_str, new_order
        )
        await ctx.send(f"{username}, te has apuntado a scrims de hoy ({today_str}).")
    except Exception as e:
        if "Duplicate entry" in str(e):
            await ctx.send(f"{username}, ya estabas apuntado a las scrims de hoy.")
        else:
            await ctx.send(f"Ocurrió un error apuntándote: {e}")
            return
    
    # 5) Mostrar la lista de inscritos de HOY con un embed
    scrims_today = await db.fetch(
        "SELECT pubg_username, orden FROM scrims WHERE scrim_date = %s ORDER BY orden ASC",
        today_str
    )
    
    if scrims_today:
        # Construimos un embed similar al de !stats
        embed = discord.Embed(
            title=f"Scrims de hoy - {today_str}",
            description="Jugadores inscritos",
            color=0x1abc9c
        )
        
        # Para formar una lista: "1) userA\n2) userB\n..."
        # Tomamos orden y pubg_username
        players_list = "\n".join(
            [f"`{row['orden']}.` **{row['pubg_username']}**" for row in scrims_today]
        )
        
        # Añadimos un campo con esa lista
        embed.add_field(name="Inscritos", value=players_list, inline=False)
        
        # Footer opcional
        embed.set_footer(text="Shadowapp al servicio")
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"No hay nadie inscrito para hoy ({today_str}).")



@bot.command(name="notscrims")
async def notscrims_command(ctx):
    user_id = ctx.author.id
    username = ctx.author.name
    
    registered_user = await db.fetch("SELECT pubg_username FROM users WHERE discord_id = %s", user_id)
    if not registered_user:
        await ctx.send(f"{username}, no estás registrado en la base de datos.")
        return
    
    today_str = datetime.datetime.now().strftime("%d/%m/%Y")
    
    result = await db.execute(
        "DELETE FROM scrims WHERE discord_id = %s AND scrim_date = %s",
        user_id, today_str
    )
    
    if "0 rows" in str(result):
        await ctx.send(f"{username}, no estabas apuntado para hoy.")
    else:
        await ctx.send(f"{username}, te has dado de baja de scrims para hoy ({today_str}).")
    
    # Lista de inscritos después de eliminar
    scrims_today = await db.fetch(
        "SELECT pubg_username, orden FROM scrims WHERE scrim_date = %s ORDER BY orden ASC",
        today_str
    )
    
    if scrims_today:
        embed = discord.Embed(
            title=f"Scrims de hoy - {today_str}",
            description="Jugadores inscritos",
            color=0x1abc9c
        )
        players_list = "\n".join(
            [f"`{row['orden']}.` **{row['pubg_username']}**" for row in scrims_today]
        )
        embed.add_field(name="Inscritos", value=players_list, inline=False)
        embed.set_footer(text="Shadowapp al servicio")
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"No hay nadie inscrito para hoy ({today_str}).")

@bot.command(name="scrape")
async def scrape_command(ctx):
    """
    Comando para obtener datos del leaderboard a través de la petición interna (GraphQL)
    y filtrar los jugadores cuyo campo 'teamName' coincida con la constante definida.
    """
    TEAM_NAME_FILTER = "fghjkdfas MIX"  # Cambia este valor según lo que necesites filtrar

    # Endpoint interno de la API GraphQL
    url = "https://tjjkdyimqrb7jjnc6m5rpefjtu.appsync-api.eu-west-1.amazonaws.com/graphql"

    # Encabezados necesarios para emular la petición real
    headers = {
        "accept": "*/*",
        "accept-language": "es-ES,es;q=0.9",
        "content-type": "application/json",
        "origin": "https://twire.gg",
        "priority": "u=1, i",
        "referer": "https://twire.gg/",
        "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Brave";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "x-amz-user-agent": "aws-amplify/2.0.6",
        "x-api-key": "da2-vqpq6wms5ndbvhl2r7kvzbpmfi"
    }

    # Cuerpo de la petición (payload) con la consulta GraphQL
    payload = {
        "operationName": "PlatformStats",
        "variables": {
            "tournament": "968faa0c-948d-11eb-bab8-f2485b011165-20250319-lobby-3",
            "token": "",
            "filters": None,
            "game": "pubg"
        },
        "query": (
            "query PlatformStats($tournament: String!, $token: String, $filters: TournamentStatsFilterInput, $game: String!) {"
            "\n  platformStats(tournament: $tournament, token: $token, filters: $filters, game: $game) {"
            "\n    tournamentName"
            "\n    groupName"
            "\n    matchName"
            "\n    lastMatchName"
            "\n    leaderboard {"
            "\n      username"
            "\n      teamName"
            "\n      teamLogo"
            "\n      kills"
            "\n      assists"
            "\n      kd"
            "\n      kda"
            "\n      kas"
            "\n      killsKnocks"
            "\n      deaths"
            "\n      diedFirst"
            "\n      diedSecond"
            "\n      diedThird"
            "\n      diedForth"
            "\n      damageDealt"
            "\n      arDamage"
            "\n      dmrDamage"
            "\n      srDamage"
            "\n      smgDamage"
            "\n      shotgunDamage"
            "\n      lmgDamage"
            "\n      pistolDamage"
            "\n      avgDamageDealt"
            "\n      damageTaken"
            "\n      avgDamageTaken"
            "\n      dbnos"
            "\n      knocked"
            "\n      revives"
            "\n      revived"
            "\n      headshotKills"
            "\n      killSteals"
            "\n      killsStolenFrom"
            "\n      swimDistance"
            "\n      walkDistance"
            "\n      rideDistance"
            "\n      longestKill"
            "\n      timeSurvived"
            "\n      avgTimeSurvived"
            "\n      killStreaks"
            "\n      heals"
            "\n      boosts"
            "\n      vehicleDestroys"
            "\n      healthRecovered"
            "\n      grenadePickup"
            "\n      grenadeDrop"
            "\n      grenadeThrow"
            "\n      grenadeDamage"
            "\n      molotovPickup"
            "\n      molotovDrop"
            "\n      molotovThrow"
            "\n      molotovDamage"
            "\n      smokebombPickup"
            "\n      smokebombDrop"
            "\n      smokebombThrow"
            "\n      flashbangPickup"
            "\n      flashbangDrop"
            "\n      flashbangThrow"
            "\n      damageTakenFromBlueZone"
            "\n      damageTakenFromEnemy"
            "\n      damageDealtDamageTaken"
            "\n      numOfMatches"
            "\n      attacker"
            "\n      finisher"
            "\n      utility"
            "\n      survivor"
            "\n      teammate"
            "\n      stealer"
            "\n      twr"
            "\n      __typename"
            "\n    }"
            "\n    overlayDesign"
            "\n    overlayColor"
            "\n    prodTournamentId"
            "\n    __typename"
            "\n  }"
            "\n}"
        )
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
    except requests.exceptions.RequestException as e:
        await ctx.send(f"Error al realizar la petición: {e}")
        return

    if response.status_code != 200:
        await ctx.send(f"Error al obtener datos. Código de estado: {response.status_code}")
        return

    try:
        data = response.json()
    except ValueError:
        await ctx.send("La respuesta no está en formato JSON.")
        return

    try:
        leaderboard = data["data"]["platformStats"]["leaderboard"]
    except KeyError:
        await ctx.send("La estructura del JSON no es la esperada.")
        return

    # Filtramos por 'teamName' (comparación sin distinguir mayúsculas/minúsculas)
    filtered_entries = [
        entry for entry in leaderboard
        if entry.get("teamName", "").lower() == TEAM_NAME_FILTER.lower()
    ]

    if not filtered_entries:
        await ctx.send(f"No se encontraron entradas para el equipo '{TEAM_NAME_FILTER}'.")
        return

    # Construimos un mensaje con algunos datos relevantes de cada entrada filtrada
    message_lines = []
    for entry in filtered_entries:
        username = entry.get("username", "Desconocido")
        team = entry.get("teamName", "Desconocido")
        kills = entry.get("kills", "N/A")
        message_lines.append(f"Usuario: {username} | Equipo: {team} | Kills: {kills}")

    message = "\n".join(message_lines)
    if len(message) > 1900:
        message = message[:1900] + "\n[Mensaje recortado]"

    await ctx.send(f"```{message}```")



# Inicia el bot
def run_bot():
    bot.run(cfg["DISCORD_TOKEN"])

if __name__ == "__main__":
    run_bot()
