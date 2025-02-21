# config/init.py

import os
from dotenv import load_dotenv

def load_config():
    # Carga variables del archivo .env
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, '.env')
    load_dotenv(env_path)

    # Retorna un diccionario con las credenciales
    config = {
        "PUBG_API_TOKEN": os.getenv("PUBG_API_TOKEN"),
        "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN")
    }
    return config
