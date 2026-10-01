import asyncio
import os

import yt_dlp


# ---------------------------------------------------------
# YouTube configuration
# ---------------------------------------------------------
# Current yt-dlp guidance recommends the mweb client together
# with a PO-token provider.
#
# bgutil is installed as a yt-dlp plugin by the Dockerfile.
# ---------------------------------------------------------

BGUTIL_SCRIPT_PATH = os.environ.get(
    "BGUTIL_SCRIPT_PATH",
    "/root/yt-dlp-plugins/bgutil-ytdlp-pot-provider/server/build/generate_once.js",
)


_COMMON_OPTS = {
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "geo_bypass": True,
    "nocheckcertificate": True,
    "skip_download": True,

    # Allow yt-dlp to use its external JavaScript challenge solver.
    "js_runtimes": {
        "deno": {},
    },

    # Allow the installed EJS package to be used.
    "remote_components": {
        "ejs": "github",
    },
}


_YOUTUBE_EXTRACTOR_ARGS = {
    "youtube": {
        # Current recommended client when using a PO-token provider.
        "player_client": "mweb",
    },

    # bgutil PO-token generation script.
    "youtubepot-bgutilscript": {
        "script_path": BGUTIL_SCRIPT_PATH,
    },
}


_AUDIO_OPTS = {
    **_COMMON_OPTS,
    "format": "bestaudio/best",
    "extractor_args": _YOUTUBE_EXTRACTOR_ARGS,
}


_VIDEO_OPTS = {
    **_COMMON_OPTS,
    "format": "best[height<=480][ext=mp4]/best[height<=480]/best",
    "extractor_args": _YOUTUBE_EXTRACTOR_ARGS,
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
    Resolve a search term or direct URL using yt-dlp.

    For YouTube:
        - mweb client is used
        - bgutil supplies the PO token
        - yt-dlp-ejs handles JavaScript challenges
        - Deno provides the JavaScript runtime

    The resulting direct media URL is passed to PyTgCalls.
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
        # Select the last available format as fallback.
        for fmt in reversed(info["formats"]):
            if fmt.get("url"):
                stream_url = fmt["url"]
                break

    if not stream_url:
        raise RuntimeError(
            "yt-dlp could not resolve a playable stream for this query."
        )

    return {
        "title": info.get("title") or query,
        "duration": info.get("duration") or 0,
        "url": stream_url,
        "webpage_url": info.get("webpage_url"),
        "thumbnail": info.get("thumbnail"),
    }
