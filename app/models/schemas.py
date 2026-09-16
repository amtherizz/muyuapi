from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class TrackItem(BaseModel):
    id: str = Field(..., description="ID video YouTube (contoh: dQw4w9WgXcQ)")
    title: str = Field(..., description="Judul lagu / video")
    artist: str = Field(..., description="Nama artis atau uploader")
    durationMs: int = Field(..., description="Durasi lagu dalam milidetik")
    thumbnailUrl: str = Field(..., description="URL thumbnail gambar lagu")


class PlaylistParseResponse(BaseModel):
    id: str = Field(..., description="ID playlist YouTube")
    title: str = Field(..., description="Judul playlist")
    channelTitle: str = Field(..., description="Nama channel pemilik playlist")
    thumbnailUrl: str = Field(..., description="URL thumbnail representasi playlist")
    trackCount: int = Field(..., description="Jumlah lagu dalam playlist")
    tracks: List[TrackItem] = Field(..., description="Daftar lagu dalam playlist")


class TrackStreamResponse(BaseModel):
    videoId: str = Field(..., description="ID video YouTube")
    streamUrl: str = Field(..., description="Direct link ke audio stream (dapat diputar oleh ExoPlayer)")
    bitrate: int = Field(..., description="Bitrate audio dalam kbps (contoh: 128, 160, 320)")
    format: str = Field(..., description="Format container/codec audio (contoh: MP3, M4A, OPUS)")
    expiresAt: int = Field(..., description="Unix timestamp kedaluwarsa URL audio")


class PlaylistSyncResponse(BaseModel):
    id: str = Field(..., description="ID playlist YouTube")
    lastUpdated: int = Field(..., description="Unix timestamp sinkronisasi")
    tracks: List[TrackItem] = Field(..., description="Daftar lagu terbaru dalam playlist")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Deskripsi singkat kesalahan")
    detail: Optional[str] = Field(None, description="Detail error teknis")

