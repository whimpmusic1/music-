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

    # Use the JavaScript challenge solver.
    "js_runtimes": {
        "node": {},
    },

    # Allow yt-dlp to use the EJS challenge scripts.
    "remote_components": {
        "ejs": ["github"],
    },

    # Use YouTube's mobile-web client.
    # The bgutil plugin supplies the required PO token.
    "extractor_args": {
        "youtube": {
            "player_client": ["mweb"],
        },
        "youtubepot-bgutilhttp": {
            "base_url": "http://127.0.0.1:4416",
        },
    },
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

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)

        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        return info


async def get_stream_info(query: str, video: bool = False) -> dict:
    """
    Resolve a search term or direct supported URL into metadata
    and a directly streamable URL.

    YouTube extraction uses the mweb client together with the
    local BgUtils PO-token provider running on port 4416.
    """

    loop = asyncio.get_running_loop()

    info = await loop.run_in_executor(
        None,
        _extract,
        query,
        video,
    )

    stream_url = info.get("url")

    if not stream_url and info.get("formats"):
        # Prefer a format containing audio.
        audio_formats = [
            fmt
            for fmt in info["formats"]
            if fmt.get("url") and fmt.get("acodec") not in (None, "none")
        ]

        if audio_formats:
            stream_url = audio_formats[-1]["url"]
        else:
            stream_url = info["formats"][-1].get("url")

    if not stream_url:
        raise RuntimeError(
            "yt-dlp could not resolve a playable stream for that query."
        )

    return {
        "title": info.get("title") or query,
        "duration": info.get("duration") or 0,
        "url": stream_url,
        "webpage_url": info.get("webpage_url"),
        "thumbnail": info.get("thumbnail"),
    }
