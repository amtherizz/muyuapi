import logging
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
import httpx

from app.config import settings
from app.models.schemas import ErrorResponse, TrackStreamResponse
from app.services.youtube import youtube_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/track", tags=["Track"])


@router.get(
    "/{videoId}/stream",
    response_model=TrackStreamResponse,
    summary="Get Track Audio Stream",
    description="Digunakan saat aplikasi perlu memutar lagu atau mengunduh cache audio.",
    responses={
        status.HTTP_200_OK: {"description": "Berhasil mendapatkan URL audio stream"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Track tidak ditemukan atau tidak tersedia"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "Kesalahan server saat memproses audio stream"},
    },
)
async def get_track_stream(videoId: str):
    clean_id = videoId.strip()
    if not clean_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parameter 'videoId' tidak boleh kosong."
        )

    try:
        result = await youtube_service.get_track_stream(clean_id)
        return result
    except ValueError as e:
        logger.warning("Stream resolution failed for video %s: %s", clean_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Unexpected error getting stream for %s: %s", clean_id, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengambil audio stream: {str(e)}"
        )


@router.api_route(
    "/{videoId}/audio",
    methods=["GET", "HEAD"],
    summary="Audio Proxy Stream for ExoPlayer",
    description="Stream audio langsung dengan dukungan HTTP Range requests agar ExoPlayer dapat memutar audio secara mulus.",
)
async def proxy_audio_stream(
    videoId: str,
    request: Request,
    range: Optional[str] = Header(None)
):
    """
    Proxies the audio stream directly to ExoPlayer with HTTP Range request support.
    This prevents playback issues related to YouTube client IP / User-Agent restrictions.
    """
    clean_id = videoId.strip()
    try:
        stream_info = await youtube_service.get_track_stream(clean_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    target_url = stream_info.streamUrl
    headers = {}
    if range:
        headers["Range"] = range

    # Set content type based on format
    fmt = stream_info.format.upper()
    if fmt == "MP3":
        content_type = "audio/mpeg"
    elif fmt == "M4A":
        content_type = "audio/mp4"
    elif fmt == "OPUS":
        content_type = "audio/ogg"
    else:
        content_type = "audio/mp4"

    client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)

    try:
        req = client.build_request("GET", target_url, headers=headers)
        upstream_resp = await client.send(req, stream=True)

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": upstream_resp.headers.get("Content-Type", content_type),
        }
        if "Content-Range" in upstream_resp.headers:
            resp_headers["Content-Range"] = upstream_resp.headers["Content-Range"]
        if "Content-Length" in upstream_resp.headers:
            resp_headers["Content-Length"] = upstream_resp.headers["Content-Length"]

        media_type = upstream_resp.headers.get("Content-Type", content_type)
        if request.method == "HEAD":
            await upstream_resp.aclose()
            await client.aclose()
            return Response(
                status_code=upstream_resp.status_code,
                headers=resp_headers,
                media_type=media_type,
            )

        async def stream_generator():
            try:
                async for chunk in upstream_resp.aiter_bytes(chunk_size=65536):
                    yield chunk
            finally:
                await upstream_resp.aclose()
                await client.aclose()

        return StreamingResponse(
            stream_generator(),
            status_code=upstream_resp.status_code,
            headers=resp_headers,
            media_type=media_type,
        )
    except Exception as e:
        await client.aclose()
        logger.error("Error during audio proxy stream for %s: %s", clean_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gagal melakukan streaming audio: {str(e)}"
        )
