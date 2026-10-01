FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/root/.deno/bin:${PATH}"

# ---------------------------------------------------------
# System packages
# ---------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        git \
        curl \
        unzip && \
    rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------
# Install Deno
# yt-dlp currently recommends Deno for EJS
# ---------------------------------------------------------
RUN curl -fsSL https://deno.land/install.sh | sh

# ---------------------------------------------------------
# Python dependencies
# ---------------------------------------------------------
WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt && \
    python -m pip install -U yt-dlp-ejs

# ---------------------------------------------------------
# Install bgutil PO-token provider plugin
# ---------------------------------------------------------
RUN mkdir -p /root/yt-dlp-plugins/bgutil-ytdlp-pot-provider && \
    git clone --depth 1 \
        https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
        /tmp/bgutil-ytdlp-pot-provider && \
    cp -r /tmp/bgutil-ytdlp-pot-provider/plugin/* \
        /root/yt-dlp-plugins/bgutil-ytdlp-pot-provider/ && \
    rm -rf /tmp/bgutil-ytdlp-pot-provider

# ---------------------------------------------------------
# Project
# ---------------------------------------------------------
COPY . .

# ---------------------------------------------------------
# Start bot
# ---------------------------------------------------------
CMD ["python", "bot.py"]
