import os
import json
from dotenv import load_dotenv

def load_config():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, ".."))

    # Permite usar .env en la raiz del proyecto, manteniendo compatibilidad con config/.env.
    load_dotenv(os.path.join(root_dir, ".env"))
    load_dotenv(os.path.join(base_dir, ".env"))

    config_json_path = os.path.join(base_dir, "config.json")
    with open(config_json_path, "r", encoding="utf-8") as f:
        file_config = json.load(f)

    config = {
        "PUBG_API_TOKEN": os.getenv("PUBG_API_TOKEN"),
        "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN"),
        "DB_HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "DB_PORT": os.getenv("DB_PORT", "3306"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "PUBG_API_URL": os.getenv("PUBG_API_URL", file_config["pubg_api_url"]),
        "PUBG_SHARD": os.getenv("PUBG_SHARD", file_config["pubg_shard"]),
    }

    required = ["PUBG_API_TOKEN", "DISCORD_TOKEN", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if not config[key]]
    if missing:
        raise RuntimeError(
            "Faltan variables de entorno requeridas: "
            + ", ".join(missing)
            + ". Crea un archivo .env en la raiz usando .env.example como referencia."
        )

    return config
