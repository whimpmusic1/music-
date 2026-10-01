
import asyncio

import yt_dlp


# YouTube has increasingly started challenging the normal web client,
# especially from cloud/server IP addresses such as Railway.
#
# Try clients that are less dependent on the normal YouTube web session.
# web_embedded is kept as a fallback because it does not require a PO token,
# although it only works for videos that YouTube exposes to the embedded client.
_YOUTUBE_EXTRACTOR_ARGS = {
    "youtube": {
        "player_client": "android,web_embedded",
    }
}


_COMMON_OPTS = {
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "geo_bypass": True,
    "nocheckcertificate": True,
    "skip_download": True,

    # Use the YouTube clients above instead of the normal default client set.
    "extractor_args": _YOUTUBE_EXTRACTOR_ARGS,

    # Give yt-dlp a little time between retries when YouTube temporarily
    # rejects a request.
    "retries": 3,
    "fragment_retries": 3,
}


_AUDIO_OPTS = {
    **_COMMON_OPTS,
    "format": "bestaudio/best",
}


_VIDEO_OPTS = {
    **_COMMON_OPTS,
    "format": (
        "best[height<=480][ext=mp4]/"
        "best[height<=480]/"
        "best"
    ),
}


def _extract(query: str, video: bool) -> dict:
    opts = _VIDEO_OPTS if video else _AUDIO_OPTS

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)

        if "entries" in info:
            entries = info.get("entries") or []

            if not entries:
                raise RuntimeError(
                    "YouTube search returned no playable results."
                )

            info = entries[0]

        return info


async def get_stream_info(query: str, video: bool = False) -> dict:
    """
    Resolve a search term or direct URL to a playable stream.

    Audio mode is intended for the music bot and returns a direct audio
    stream URL without downloading the media to disk.
    """

    loop = asyncio.get_running_loop()

    info = await loop.run_in_executor(
        None,
        _extract,
        query,
        video,
    )

    if not info:
        raise RuntimeError(
            "yt-dlp returned no information for this query."
        )

    stream_url = info.get("url")

    # Some YouTube clients return formats instead of a top-level URL.
    if not stream_url:
        formats = info.get("formats") or []

        if video:
            # Prefer an MP4 video format when available.
            video_formats = [
                f
                for f in formats
                if f.get("url")
                and f.get("ext") == "mp4"
                and f.get("height")
                and f.get("height") <= 480
            ]

            if video_formats:
                stream_url = video_formats[-1]["url"]

        if not stream_url:
            # Prefer audio-only formats.
            audio_formats = [
                f
                for f in formats
                if f.get("url")
                and (
                    f.get("vcodec") == "none"
                    or f.get("acodec") != "none"
                )
            ]

            if audio_formats:
                stream_url = audio_formats[-1]["url"]

        if not stream_url and formats:
            for fmt in reversed(formats):
                if fmt.get("url"):
                    stream_url = fmt["url"]
                    break

    if not stream_url:
        raise RuntimeError(
            "YouTube returned metadata but no playable stream URL. "
            "The video may require authentication or a PO token."
        )

    return {
        "title": info.get("title") or query,
        "duration": info.get("duration") or 0,
        "url": stream_url,
        "webpage_url": info.get("webpage_url"),
        "thumbnail": info.get("thumbnail"),
    }

