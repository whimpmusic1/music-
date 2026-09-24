import asyncio

import yt_dlp

_COMMON_OPTS = {
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "geo_bypass": True,
    "nocheckcertificate": True,
    "skip_download": True,
}

_AUDIO_OPTS = {**_COMMON_OPTS, "format": "bestaudio/best"}
_VIDEO_OPTS = {**_COMMON_OPTS, "format": "best[height<=480][ext=mp4]/best[height<=480]/best"}


def _extract(query: str, video: bool) -> dict:
    opts = _VIDEO_OPTS if video else _AUDIO_OPTS
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info and info["entries"]:
            info = info["entries"][0]
        return info


async def get_stream_info(query: str, video: bool = False) -> dict:
    """
    Resolve a search term or a direct link (YouTube, SoundCloud, etc. -
    anything yt-dlp supports) to metadata plus a direct, streamable URL
    that ffmpeg/pytgcalls can pipe straight into the voice chat, with no
    need to download the file to disk first.
    """
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, _extract, query, video)

    stream_url = info.get("url")
    if not stream_url and info.get("formats"):
        # Fallback: pick the last (usually best/progressive) format entry.
        stream_url = info["formats"][-1].get("url")

    if not stream_url:
        raise RuntimeError("yt-dlp could not resolve a playable stream for that query.")

    return {
        "title": info.get("title") or query,
        "duration": info.get("duration") or 0,
        "url": stream_url,
        "webpage_url": info.get("webpage_url"),
        "thumbnail": info.get("thumbnail"),
    }
