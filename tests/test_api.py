import pytest
from unittest.mock import AsyncMock, patch
import httpx
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.schemas import PlaylistParseResponse, PlaylistSyncResponse, TrackItem, TrackStreamResponse
from app.services.cache import cache_service


@pytest.fixture(autouse=True)
def clean_cache():
    # Use in-memory or clean test keys before test
    cache_service.delete("playlist:PLtest123")
    cache_service.delete("stream:video_id_1")
    yield
    cache_service.delete("playlist:PLtest123")
    cache_service.delete("stream:video_id_1")


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_parse_playlist_missing_url():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/playlist/parse")
    # FastAPI returns 422 for missing required query param
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_parse_playlist_success():
    mock_playlist = PlaylistParseResponse(
        id="PLtest123",
        title="City Pop Favorites",
        channelTitle="RetroVibes",
        thumbnailUrl="https://i.ytimg.com/vi/video_id_1/hqdefault.jpg",
        trackCount=1,
        tracks=[
            TrackItem(
                id="video_id_1",
                title="Stay With Me",
                artist="Miki Matsubara",
                durationMs=312000,
                thumbnailUrl="https://i.ytimg.com/vi/video_id_1/hqdefault.jpg",
            )
        ],
    )

    with patch("app.services.youtube.youtube_service.parse_playlist", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = mock_playlist

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/playlist/parse?url=https://www.youtube.com/playlist?list=PLtest123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "PLtest123"
        assert data["title"] == "City Pop Favorites"
        assert data["channelTitle"] == "RetroVibes"
        assert data["trackCount"] == 1
        assert len(data["tracks"]) == 1
        assert data["tracks"][0]["id"] == "video_id_1"
        assert data["tracks"][0]["durationMs"] == 312000


@pytest.mark.asyncio
async def test_get_track_stream_success():
    mock_stream = TrackStreamResponse(
        videoId="video_id_1",
        streamUrl="https://storage.muyu.tams.my.id/audio/stream.m4a",
        bitrate=320,
        format="M4A",
        expiresAt=1726500000,
    )

    with patch("app.services.youtube.youtube_service.get_track_stream", new_callable=AsyncMock) as mock_get_stream:
        mock_get_stream.return_value = mock_stream

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/track/video_id_1/stream")

        assert response.status_code == 200
        data = response.json()
        assert data["videoId"] == "video_id_1"
        assert data["streamUrl"] == "https://storage.muyu.tams.my.id/audio/stream.m4a"
        assert data["bitrate"] == 320
        assert data["format"] == "M4A"
        assert data["expiresAt"] == 1726500000


@pytest.mark.asyncio
async def test_sync_playlist_success():
    mock_sync = PlaylistSyncResponse(
        id="PLtest123",
        lastUpdated=1726480000,
        tracks=[
            TrackItem(
                id="video_id_1",
                title="Stay With Me",
                artist="Miki Matsubara",
                durationMs=312000,
                thumbnailUrl="https://i.ytimg.com/vi/video_id_1/hqdefault.jpg",
            )
        ],
    )

    with patch("app.services.youtube.youtube_service.sync_playlist", new_callable=AsyncMock) as mock_sync_fn:
        mock_sync_fn.return_value = mock_sync

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/playlist/PLtest123/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "PLtest123"
        assert data["lastUpdated"] == 1726480000
        assert len(data["tracks"]) == 1


@pytest.mark.asyncio
async def test_cache_service():
    test_key = "test_key"
    test_val = {"foo": "bar"}

    cache_service.set(test_key, test_val, ttl_seconds=10)
    cached = cache_service.get(test_key)
    assert cached == test_val

    cache_service.delete(test_key)
    assert cache_service.get(test_key) is None


@pytest.mark.asyncio
async def test_audio_proxy_endpoint():
    mock_stream = TrackStreamResponse(
        videoId="video_id_1",
        streamUrl="https://storage.muyu.tams.my.id/audio/stream.m4a",
        bitrate=320,
        format="M4A",
        expiresAt=1726500000,
    )

    with patch("app.services.youtube.youtube_service.get_track_stream", new_callable=AsyncMock) as mock_get_stream:
        mock_get_stream.return_value = mock_stream

        # Mock httpx response for proxy
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.headers = httpx.Headers({"content-type": "audio/mp4", "content-length": "1000"})

        async def dummy_iter(chunk_size=None):
            yield b"dummy audio chunk"

        mock_resp.aiter_bytes = dummy_iter
        mock_resp.aclose = AsyncMock()

        with patch("httpx.AsyncClient.send", return_value=mock_resp):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # Test GET
                res_get = await ac.get("/api/track/video_id_1/audio")
                assert res_get.status_code == 200
                assert "audio/mp4" in res_get.headers.get("content-type", "")

                # Test HEAD
                res_head = await ac.head("/api/track/video_id_1/audio")
                assert res_head.status_code == 200
                assert "audio/mp4" in res_head.headers.get("content-type", "")

