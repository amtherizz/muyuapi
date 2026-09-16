# API Specification for SONIK / BEAT Backend

Base URL: `https://muyu.tams.my.id/api/`

Berikut adalah daftar endpoint yang perlu kamu buat di sisi backend untuk mendukung fitur sinkronisasi YouTube dan pemutaran audio di aplikasi SONIK / BEAT.

---

## 1. Parse Playlist Metadata
Digunakan saat user menempelkan URL YouTube di layar Import untuk melihat preview sebelum mengimpor.

*   **Endpoint:** `GET /playlist/parse`
*   **Query Params:**
    *   `url`: `string` (Contoh: `https://www.youtube.com/playlist?list=PL...`)
*   **Response (200 OK):**
    ```json
    {
      "id": "PL...",
      "title": "City Pop Favorites",
      "channelTitle": "RetroVibes",
      "thumbnailUrl": "https://...",
      "trackCount": 42,
      "tracks": [
        {
          "id": "video_id_1",
          "title": "Stay With Me",
          "artist": "Miki Matsubara",
          "durationMs": 312000,
          "thumbnailUrl": "https://..."
        },
        ...
      ]
    }
    ```

---

## 2. Get Track Audio Stream
Digunakan saat aplikasi perlu memutar lagu atau mengunduh cache audio.

*   **Endpoint:** `GET /track/{videoId}/stream`
*   **Response (200 OK):**
    ```json
    {
      "videoId": "video_id_1",
      "streamUrl": "https://storage.muyu.tams.my.id/audio/...",
      "bitrate": 320,
      "format": "MP3",
      "expiresAt": 1726500000
    }
    ```
    > [!TIP]
    > Pastikan `streamUrl` adalah link langsung ke file audio (bukan halaman HTML) agar ExoPlayer bisa memutarnya.

---

## 3. Sync Playlist
Digunakan ketika user memicu sinkronisasi manual dari layar Detail Playlist untuk mendeteksi jika ada lagu baru yang ditambahkan ke playlist YouTube asli.

*   **Endpoint:** `GET /playlist/{playlistId}/sync`
*   **Response (200 OK):**
    ```json
    {
      "id": "PL...",
      "lastUpdated": 1726480000,
      "tracks": [
        {
          "id": "video_id_1",
          "title": "Stay With Me",
          ...
        },
        ...
      ]
    }
    ```

---

## Rekomendasi Teknologi Backend:
1.  **Language:** Node.js (Express), Python (FastAPI/Flask), atau Go.
2.  **YouTube Parser:** Gunakan library seperti `yt-dlp` (wrapper) atau `ytdl-core` (Node.js) untuk mengekstrak stream URL secara realtime.
3.  **Caching:** Jika memungkinkan, simpan metadata di database (PostgreSQL/Redis) agar tidak terlalu sering memanggil YouTube API (menghindari limit kuota).
