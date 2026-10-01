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

    # Use Node for YouTube JavaScript challenges.
    "js_runtimes": {
        "node": {},
    },

    # Keep EJS available for current YouTube extraction.
    "remote_components": {
        "ejs": ["github"],
    },

    # IMPORTANT:
    # Do NOT force mweb.
    # Use YouTube TV client instead.
    "extractor_args": {
        "youtube": {
            "player_client": ["default", "web_embedded"],
        },
    },

    # Retry transient YouTube failures.
    "retries": 3,
    "fragment_retries": 3,
}


_AUDIO_OPTS = {
    **_COMMON_OPTS,
    "format": "bestaudio/best",
}


_VIDEO_OPTS = {
    **_COMMON_OPTS,
    "format": "best[height<=480][ext=mp4]/best[height<=480]/best",
}


def _extract(query: str, video: bool) -> dict:
    opts = _VIDEO_OPTS if video else _AUDIO_OPTS

    logger.info("yt-dlp extracting: %s", query)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)

        if info.get("entries"):
            info = next(
                (
                    entry
                    for entry in info["entries"]
                    if entry
                ),
                None,
            )

        if not info:
            raise RuntimeError(
                "yt-dlp returned no result for the requested media."
            )

        return info


async def get_stream_info(query: str, video: bool = False) -> dict:
    loop = asyncio.get_running_loop()

    info = await loop.run_in_executor(
        None,
        _extract,
        query,
        video,
    )

    stream_url = info.get("url")

    if not stream_url and info.get("formats"):
        audio_formats = [
            fmt
            for fmt in info["formats"]
            if (
                fmt.get("url")
                and fmt.get("acodec") not in (None, "none")
            )
        ]

        if audio_formats:
            stream_url = audio_formats[-1]["url"]
        else:
            stream_url = info["formats"][-1].get("url")

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
