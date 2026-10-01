import asyncio
import logging

import yt_dlp


logger = logging.getLogger(__name__)


_COMMON_OPTS = {
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "geo_bypass": True,
    "nocheckcertificate": True,
    "skip_download": True,

    # YouTube JavaScript challenge solving.
    "js_runtimes": {
        "node": {},
    },

    # Allow yt-dlp to obtain EJS challenge components.
    "remote_components": {
        "ejs": ["github"],
    },

    # Let yt-dlp use several supported YouTube clients
    # instead of forcing only mweb.
    "extractor_args": {
        "youtube": {
            "player_client": [
                "web",
                "mweb",
                "android_vr",
            ],
        },

        # Local BgUtils PO-token provider.
        "youtubepot-bgutilhttp": {
            "base_url": "http://127.0.0.1:4416",
        },
    },

    # Give YouTube requests reasonable retry behavior.
    "retries": 3,
    "fragment_retries": 3,

    # Network timeout.
    "socket_timeout": 20,
}


_AUDIO_OPTS = {
    **_COMMON_OPTS,

    # Audio only.
    "format": "bestaudio/best",
}


_VIDEO_OPTS = {
    **_COMMON_OPTS,

    # Kept for compatibility, although your current bot is audio-only.
    "format": (
        "best[height<=480][ext=mp4]/"
        "best[height<=480]/"
        "best"
    ),
}


def _extract(query: str, video: bool) -> dict:
    opts = _VIDEO_OPTS if video else _AUDIO_OPTS

    logger.info("Resolving media: %s", query)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)

        if not info:
            raise RuntimeError(
                "yt-dlp returned no information for the requested media."
            )

        # ytsearch returns an entries list.
        if "entries" in info:
            entries = info.get("entries") or []

            if not entries:
                raise RuntimeError(
                    "YouTube search returned no playable results."
                )

            info = entries[0]

        return info


def _get_stream_url(info: dict) -> str | None:
    """
    Get the direct media URL from yt-dlp metadata.

    Prefer yt-dlp's selected URL. If that is unavailable,
    search through the returned formats for an audio stream.
    """

    stream_url = info.get("url")

    if stream_url:
        return stream_url

    formats = info.get("formats") or []

    # Prefer formats that contain audio.
    audio_formats = [
        fmt
        for fmt in formats
        if (
            fmt.get("url")
            and fmt.get("acodec") not in (None, "none")
        )
    ]

    if audio_formats:
        # Prefer the highest bitrate audio format available.
        audio_formats.sort(
            key=lambda fmt: (
                fmt.get("abr") or 0,
                fmt.get("tbr") or 0,
            )
        )

        return audio_formats[-1]["url"]

    # Last-resort format.
    for fmt in reversed(formats):
        if fmt.get("url"):
            return fmt["url"]

    return None


async def get_stream_info(
    query: str,
    video: bool = False,
) -> dict:
    """
    Resolve a search term or direct supported URL into:

        title
        duration
        direct stream URL
        webpage URL
        thumbnail

    yt-dlp runs in a worker thread so it does not block
    the Telegram/PyTgCalls asyncio event loop.
    """

    loop = asyncio.get_running_loop()

    info = await loop.run_in_executor(
        None,
        _extract,
        query,
        video,
    )

    stream_url = _get_stream_url(info)

    if not stream_url:
        raise RuntimeError(
            "yt-dlp could not resolve a playable stream."
        )

    return {
        "title": info.get("title") or query,
        "duration": info.get("duration") or 0,
        "url": stream_url,
        "webpage_url": info.get("webpage_url"),
        "thumbnail": info.get("thumbnail"),
    }
