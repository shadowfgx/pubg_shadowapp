# Usa Python 3.11 como base
FROM python:3.11

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los archivos de requerimientos y el código fuente
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Configurar las variables de entorno para producción
ENV DISCORD_TOKEN=${DISCORD_TOKEN}
ENV PUBG_API_KEY=${PUBG_API_KEY}

# Comando para ejecutar el bot
CMD ["python", "src/bot/main.py"]
