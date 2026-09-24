import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.sample to .env and fill it in."
        )
    return value


class Config:
    API_ID = int(_require("API_ID"))
    API_HASH = _require("API_HASH")
    BOT_TOKEN = _require("BOT_TOKEN")
    SESSION_STRING = _require("SESSION_STRING")

    OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
    # Safety cap so nobody accidentally streams a 4-hour video forever.
    DURATION_LIMIT_MIN = int(os.environ.get("DURATION_LIMIT_MIN", "60"))
    # Default video quality piped into the voice chat.
    VIDEO_QUALITY = os.environ.get("VIDEO_QUALITY", "SD_480p")
