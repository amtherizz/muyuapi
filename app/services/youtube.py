import asyncio
import re
import time
from urllib.parse import parse_qs, urlparse
from typing import Any, Dict, List, Optional
import yt_dlp

from app.config import settings
from app.models.schemas import (
    PlaylistParseResponse,
    PlaylistSyncResponse,
    TrackItem,
    TrackStreamResponse,
)
from app.services.cache import cache_service


class YouTubeService:
    """Service to interact with YouTube via yt-dlp."""

    def __init__(self):
        self._default_ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "ignoreerrors": True,
            "no_color": True,
        }
        if settings.ytdlp_proxy:
            self._default_ydl_opts["proxy"] = settings.ytdlp_proxy

    def extract_playlist_id(self, url_or_id: str) -> str:
        """Extracts playlist ID from a URL or returns the raw ID."""
        url_or_id = url_or_id.strip()
        if not ("http://" in url_or_id or "https://" in url_or_id):
            return url_or_id

        parsed = urlparse(url_or_id)
        qs = parse_qs(parsed.query)
        if "list" in qs and qs["list"]:
            return qs["list"][0]

        # In case URL pattern is like /playlist?list=ID
        match = re.search(r"list=([a-zA-Z0-9_-]+)", url_or_id)
        if match:
            return match.group(1)

        return url_or_id

    def extract_video_id(self, url_or_id: str) -> str:
        """Extracts video ID from a URL or returns the raw ID."""
        url_or_id = url_or_id.strip()
        if not ("http://" in url_or_id or "https://" in url_or_id):
            return url_or_id

        parsed = urlparse(url_or_id)
        qs = parse_qs(parsed.query)
        if "v" in qs and qs["v"]:
            return qs["v"][0]

        # youtu.be/<id>
        if "youtu.be" in parsed.netloc:
            return parsed.path.lstrip("/").split("?")[0]

        # /shorts/<id> or /embed/<id>
        parts = parsed.path.split("/")
        if len(parts) >= 3 and parts[1] in ("shorts", "embed", "v"):
            return parts[2]

        return url_or_id

    def _get_best_thumbnail(self, thumbnails: Optional[List[Dict[str, Any]]]) -> str:
        if not thumbnails:
            return ""
        # Choose highest resolution or last available thumbnail
        return thumbnails[-1].get("url", "")

    def _sync_extract_playlist(self, target_url: str) -> Dict[str, Any]:
        opts = dict(self._default_ydl_opts)
        opts["extract_flat"] = "in_playlist"
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(target_url, download=False)

    def _sync_extract_track_stream(self, video_url: str) -> Dict[str, Any]:
        opts = dict(self._default_ydl_opts)
        opts["extract_flat"] = False
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(video_url, download=False)

    async def parse_playlist(self, url_or_id: str, force_refresh: bool = False) -> PlaylistParseResponse:
        playlist_id = self.extract_playlist_id(url_or_id)
        cache_key = f"playlist:{playlist_id}"

        if not force_refresh:
            cached = cache_service.get(cache_key)
            if cached:
                return PlaylistParseResponse(**cached)

        target_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        info = await asyncio.to_thread(self._sync_extract_playlist, target_url)

        if not info:
            raise ValueError(f"Playlist with ID '{playlist_id}' could not be loaded or is private/unavailable.")

        playlist_title = info.get("title") or "YouTube Playlist"
        channel_title = (
            info.get("channel")
            or info.get("uploader")
            or info.get("channel_follower_count")
            or "Unknown Channel"
        )
        thumbnail_url = self._get_best_thumbnail(info.get("thumbnails"))

        entries = info.get("entries") or []
        tracks: List[TrackItem] = []

        for entry in entries:
            if not entry:
                continue
            video_id = entry.get("id")
            if not video_id:
                continue

            track_title = entry.get("title") or "Unknown Track"
            # Attempt to get artist or fallback to uploader/channel
            artist = (
                entry.get("artist")
                or entry.get("uploader")
                or entry.get("channel")
                or channel_title
            )
            # Duration in ms
            duration = entry.get("duration")
            duration_ms = int(duration * 1000) if duration is not None else 0

            track_thumb = (
                self._get_best_thumbnail(entry.get("thumbnails"))
                or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            )

            tracks.append(
                TrackItem(
                    id=video_id,
                    title=track_title,
                    artist=artist,
                    durationMs=duration_ms,
                    thumbnailUrl=track_thumb,
                )
            )

        if not thumbnail_url and tracks:
            thumbnail_url = tracks[0].thumbnailUrl

        result = PlaylistParseResponse(
            id=playlist_id,
            title=playlist_title,
            channelTitle=str(channel_title),
            thumbnailUrl=thumbnail_url or "",
            trackCount=len(tracks),
            tracks=tracks,
        )

        # Cache result
        cache_service.set(cache_key, result.model_dump(), settings.playlist_cache_ttl)

        return result

    async def get_track_stream(self, video_id: str) -> TrackStreamResponse:
        clean_id = self.extract_video_id(video_id)
        cache_key = f"stream:{clean_id}"

        cached = cache_service.get(cache_key)
        if cached:
            return TrackStreamResponse(**cached)

        video_url = f"https://www.youtube.com/watch?v={clean_id}"
        info = await asyncio.to_thread(self._sync_extract_track_stream, video_url)

        if not info:
            raise ValueError(f"Track with ID '{clean_id}' could not be loaded or is unavailable.")

        stream_url = info.get("url")
        if not stream_url:
            raise ValueError(f"No direct audio stream URL found for track '{clean_id}'.")

        # Determine bitrate (default 128 if not found)
        abr = info.get("abr") or info.get("tbr")
        bitrate = int(abr) if abr else 128

        # Determine format
        audio_ext = info.get("ext", "m4a").upper()
        # Normalization (e.g. webm -> OPUS, m4a -> M4A)
        if audio_ext == "WEBM":
            audio_format = "OPUS"
        elif audio_ext in ("M4A", "MP4"):
            audio_format = "M4A"
        elif audio_ext == "MP3":
            audio_format = "MP3"
        else:
            audio_format = audio_ext

        # Parse expiresAt from URL query parameters (expire=...)
        now = int(time.time())
        expires_at = now + settings.stream_cache_ttl

        try:
            parsed_stream = urlparse(stream_url)
            qs = parse_qs(parsed_stream.query)
            if "expire" in qs and qs["expire"]:
                expires_at = int(qs["expire"][0])
        except Exception:
            pass

        result = TrackStreamResponse(
            videoId=clean_id,
            streamUrl=stream_url,
            bitrate=bitrate,
            format=audio_format,
            expiresAt=expires_at,
        )

        # Cache with TTL up to expiration time minus 300s margin
        ttl = max(60, expires_at - now - 300)
        cache_service.set(cache_key, result.model_dump(), ttl)

        return result

    async def sync_playlist(self, playlist_id: str) -> PlaylistSyncResponse:
        clean_id = self.extract_playlist_id(playlist_id)
        # Force refresh playlist from YouTube
        parsed = await self.parse_playlist(clean_id, force_refresh=True)

        return PlaylistSyncResponse(
            id=parsed.id,
            lastUpdated=int(time.time()),
            tracks=parsed.tracks,
        )


youtube_service = YouTubeService()

