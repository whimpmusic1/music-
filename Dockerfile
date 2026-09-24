FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# FFmpeg is required for media processing. ca-certificates is useful for
# HTTPS requests made by yt-dlp and Telegram-related libraries.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies before copying application code for better Docker caching.
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
