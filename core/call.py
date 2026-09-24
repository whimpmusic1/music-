import logging

from pytgcalls import PyTgCalls
from pytgcalls import filters as fl
from pytgcalls.types import AudioQuality, MediaStream, StreamEnded, VideoQuality

from config import Config
from core.clients import assistant
from core.queue import MusicQueue

logger = logging.getLogger(__name__)

_QUALITY_MAP = {
    "SD_240p": VideoQuality.SD_240p,
    "SD_360p": VideoQuality.SD_360p,
    "SD_480p": VideoQuality.SD_480p,
    "HD_720p": VideoQuality.HD_720p,
    "HD_1080p": VideoQuality.HD_1080p,
    "FHD_1080p": VideoQuality.FHD_1080p,
}


class Call:
    """Thin PyTgCalls wrapper with a per-chat FIFO music queue."""

    def __init__(self, assistant_client):
        self.pytgcalls = PyTgCalls(assistant_client)
        self.queues: dict[int, MusicQueue] = {}
        self._register_handlers()

    def get_queue(self, chat_id: int) -> MusicQueue:
        if chat_id not in self.queues:
            self.queues[chat_id] = MusicQueue()
        return self.queues[chat_id]

    def _register_handlers(self):
        # Use the current PyTgCalls stream-end filter instead of checking
        # update class names manually. This catches normal stream completion.
        @self.pytgcalls.on_update(fl.stream_end())
        async def _on_stream_end(client, update: StreamEnded):
            chat_id = update.chat_id
            logger.info("Stream ended in chat %s", chat_id)
            await self._play_next(chat_id)

    def _build_stream(self, url: str, video: bool) -> MediaStream:
        video_quality = _QUALITY_MAP.get(
            Config.VIDEO_QUALITY,
            VideoQuality.SD_480p,
        )

        if video:
            return MediaStream(
                url,
                audio_parameters=AudioQuality.HIGH,
                video_parameters=video_quality,
            )

        return MediaStream(
            url,
            audio_parameters=AudioQuality.HIGH,
            video_flags=MediaStream.Flags.IGNORE,
        )

    async def start(self):
        await self.pytgcalls.start()

    async def _stream(self, chat_id: int, track: dict):
        """Start a stream and expose real PyTgCalls errors to the caller."""
        stream = self._build_stream(track["url"], track["video"])

        try:
            await self.pytgcalls.play(chat_id, stream)
            logger.info(
                "Started %s stream in chat %s: %s",
                "video" if track["video"] else "audio",
                chat_id,
                track["title"],
            )
        except Exception:
            # Do not call play() a second time for every possible exception.
            # A second blind play() can hide the real Telegram/PyTgCalls error.
            logger.exception(
                "Failed to start stream in chat %s: %s",
                chat_id,
                track["title"],
            )
            raise

    async def _play_next(self, chat_id: int):
        queue = self.get_queue(chat_id)
        next_track = queue.advance()

        if next_track is None:
            await self.leave(chat_id)
            return

        try:
            await self._stream(chat_id, next_track)
        except Exception:
            logger.exception("Failed to play next track in chat %s", chat_id)
            await self.leave(chat_id)

    async def add_and_play(self, chat_id: int, track: dict) -> str:
        """Add a track; start it immediately if the queue was idle."""
        queue = self.get_queue(chat_id)
        was_empty = queue.current() is None
        queue.add(track)

        if was_empty:
            try:
                await self._stream(chat_id, track)
            except Exception:
                # Remove the failed first track so the queue is not left in a
                # false "currently playing" state.
                queue.clear()
                raise
            return "playing"

        return "queued"

    async def skip(self, chat_id: int):
        await self._play_next(chat_id)

    async def pause(self, chat_id: int):
        await self.pytgcalls.pause(chat_id)

    async def resume(self, chat_id: int):
        await self.pytgcalls.resume(chat_id)

    async def leave(self, chat_id: int):
        self.queues.pop(chat_id, None)
        try:
            await self.pytgcalls.leave_call(chat_id)
        except Exception as e:
            logger.debug(
                "leave_call for %s failed (probably already left): %s",
                chat_id,
                e,
            )


call = Call(assistant)
