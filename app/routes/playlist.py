import logging
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    ErrorResponse,
    PlaylistParseResponse,
    PlaylistSyncResponse,
)
from app.services.youtube import youtube_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playlist", tags=["Playlist"])


@router.get(
    "/parse",
    response_model=PlaylistParseResponse,
    summary="Parse Playlist Metadata",
    description="Digunakan saat user menempelkan URL YouTube di layar Import untuk melihat preview sebelum mengimpor.",
    responses={
        status.HTTP_200_OK: {"description": "Berhasil mengekstrak metadata playlist"},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "URL playlist tidak valid"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Playlist tidak ditemukan atau bersifat privat"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Kesalahan server saat memproses playlist"},
    },
)
async def parse_playlist(
    url: str = Query(..., description="URL playlist YouTube (contoh: https://www.youtube.com/playlist?list=PL...)")
):
    clean_url = url.strip()
    if not clean_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parameter 'url' tidak boleh kosong."
        )

    try:
        result = await youtube_service.parse_playlist(clean_url)
        return result
    except ValueError as e:
        logger.warning("Playlist parse failed for %s: %s", clean_url, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Unexpected error parsing playlist %s: %s", clean_url, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memproses playlist: {str(e)}"
        )


@router.get(
    "/{playlistId}/sync",
    response_model=PlaylistSyncResponse,
    summary="Sync Playlist",
    description="Digunakan ketika user memicu sinkronisasi manual dari layar Detail Playlist untuk mendeteksi lagu baru.",
    responses={
        status.HTTP_200_OK: {"description": "Berhasil menyinkronkan playlist"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Playlist tidak ditemukan"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Kesalahan server saat sinkronisasi"},
    },
)
async def sync_playlist(
    playlistId: str
):
    clean_id = playlistId.strip()
    if not clean_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parameter 'playlistId' tidak boleh kosong."
        )

    try:
        result = await youtube_service.sync_playlist(clean_id)
        return result
    except ValueError as e:
        logger.warning("Playlist sync failed for %s: %s", clean_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Unexpected error syncing playlist %s: %s", clean_id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menyinkronkan playlist: {str(e)}"
        )

