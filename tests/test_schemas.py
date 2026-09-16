from app.models.schemas import (
    PlaylistParseResponse,
    PlaylistSyncResponse,
    TrackItem,
    TrackStreamResponse,
)


def test_track_item_schema():
    track = TrackItem(
        id="video_id_1",
        title="Stay With Me",
        artist="Miki Matsubara",
        durationMs=312000,
        thumbnailUrl="https://i.ytimg.com/vi/video_id_1/hqdefault.jpg",
    )
    assert track.id == "video_id_1"
    assert track.title == "Stay With Me"
    assert track.artist == "Miki Matsubara"
    assert track.durationMs == 312000
    assert track.thumbnailUrl == "https://i.ytimg.com/vi/video_id_1/hqdefault.jpg"


def test_playlist_parse_response_schema():
    data = {
        "id": "PL12345",
        "title": "City Pop Favorites",
        "channelTitle": "RetroVibes",
        "thumbnailUrl": "https://i.ytimg.com/vi/video_id_1/hqdefault.jpg",
        "trackCount": 1,
        "tracks": [
            {
                "id": "video_id_1",
                "title": "Stay With Me",
                "artist": "Miki Matsubara",
                "durationMs": 312000,
                "thumbnailUrl": "https://i.ytimg.com/vi/video_id_1/hqdefault.jpg",
            }
        ],
    }
    resp = PlaylistParseResponse(**data)
    assert resp.id == "PL12345"
    assert resp.trackCount == 1
    assert len(resp.tracks) == 1
    assert resp.tracks[0].title == "Stay With Me"


def test_track_stream_response_schema():
    data = {
        "videoId": "video_id_1",
        "streamUrl": "https://storage.muyu.tams.my.id/audio/sample.mp3",
        "bitrate": 320,
        "format": "MP3",
        "expiresAt": 1726500000,
    }
    resp = TrackStreamResponse(**data)
    assert resp.videoId == "video_id_1"
    assert resp.bitrate == 320
    assert resp.format == "MP3"
    assert resp.expiresAt == 1726500000


def test_playlist_sync_response_schema():
    data = {
        "id": "PL12345",
        "lastUpdated": 1726480000,
        "tracks": [
            {
                "id": "video_id_1",
                "title": "Stay With Me",
                "artist": "Miki Matsubara",
                "durationMs": 312000,
                "thumbnailUrl": "https://i.ytimg.com/vi/video_id_1/hqdefault.jpg",
            }
        ],
    }
    resp = PlaylistSyncResponse(**data)
    assert resp.id == "PL12345"
    assert resp.lastUpdated == 1726480000
    assert len(resp.tracks) == 1

