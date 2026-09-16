# MUYU API - Backend Service untuk SONIK / BEAT

Backend API berbasis Python (FastAPI & `yt-dlp`) yang dirancang untuk mendukung sinkronisasi playlist YouTube dan pemutaran audio pada aplikasi Android **SONIK / BEAT** (kompatibel dengan ExoPlayer).

Dokumentasi spesifikasi mengacu pada [`api_specification.artifact.md`](./api_specification.artifact.md).

---

## 🚀 Fitur Utama

- **Fast & Asynchronous:** Dibangun di atas FastAPI & Uvicorn untuk performa tinggi dan latency rendah.
- **YouTube Extraction Engine:** Menggunakan `yt-dlp` terbaru untuk mengekstrak metadata playlist dan stream link audio secara andal.
- **ExoPlayer Compatibility:** Mengembalikan direct audio stream URL (M4A/AAC/Opus/MP3) dan menyediakan endpoint audio proxy dengan dukungan HTTP `Range` request (seek, buffer, resume).
- **Dual Routing:** Mendukung endpoint dengan prefix `/api/...` (sesuai Base URL `https://muyu.tams.my.id/api/`) maupun root `/...` untuk kemudahan konfigurasi reverse-proxy.
- **SQLite Cache with TTL:** Metadata playlist dan stream link disimpan dalam database lokal SQLite ber-TTL untuk mencegah rate-limit kuota dari YouTube dan mempercepat response (waktu respons cache < 1ms).
- **Interactive API Docs:** Swagger UI otomatis di `/docs` dan ReDoc di `/redoc`.
- **Ready for Production:** Dilengkapi Dockerfile (dengan `ffmpeg`), docker-compose, dan contoh konfigurasi Nginx.

---

## 📡 Daftar Endpoint API

### 1. Parse Playlist Metadata
Digunakan saat user menempelkan URL YouTube di layar Import untuk melihat preview sebelum mengimpor.

- **URL:** `GET /api/playlist/parse?url={playlist_url}`
- **Contoh:** `GET /api/playlist/parse?url=https://www.youtube.com/playlist?list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj`
- **Response `(200 OK)`:**
```json
{
  "id": "PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",
  "title": "Pop Music Playlist - Timeless Pop Songs",
  "channelTitle": "by Redlist - Just Hits",
  "thumbnailUrl": "https://i.ytimg.com/vi/ekr2nIex040/hqdefault.jpg",
  "trackCount": 200,
  "tracks": [
    {
      "id": "ekr2nIex040",
      "title": "ROSÉ & Bruno Mars - APT. (Official Music Video)",
      "artist": "ROSÉ",
      "durationMs": 174000,
      "thumbnailUrl": "https://i.ytimg.com/vi/ekr2nIex040/hqdefault.jpg"
    }
  ]
}
```

---

### 2. Get Track Audio Stream
Digunakan saat aplikasi perlu memutar lagu atau mengunduh cache audio.

- **URL:** `GET /api/track/{videoId}/stream`
- **Contoh:** `GET /api/track/dQw4w9WgXcQ/stream`
- **Response `(200 OK)`:**
```json
{
  "videoId": "dQw4w9WgXcQ",
  "streamUrl": "https://rr2---sn-poqvn5u-jb3r.googlevideo.com/videoplayback?...",
  "bitrate": 129,
  "format": "M4A",
  "expiresAt": 1789556137
}
```

#### Catatan Pemutaran ExoPlayer:
Aplikasi Android SONIK / BEAT dapat langsung mengoper `streamUrl` ke MediaItem ExoPlayer:
```kotlin
val mediaItem = MediaItem.fromUri(trackStreamResponse.streamUrl)
player.setMediaItem(mediaItem)
player.prepare()
player.play()
```
> [!TIP]
> Jika koneksi perangkat pengguna mengalami pembatasan akses langsung ke domain YouTube / googlevideo, backend ini juga menyediakan endpoint audio proxy langsung di:
> `GET /api/track/{videoId}/audio` yang mendukung HTTP Range request.

---

### 3. Sync Playlist
Digunakan ketika user memicu sinkronisasi manual dari layar Detail Playlist untuk mendeteksi jika ada lagu baru yang ditambahkan ke playlist YouTube asli.

- **URL:** `GET /api/playlist/{playlistId}/sync`
- **Contoh:** `GET /api/playlist/PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj/sync`
- **Response `(200 OK)`:**
```json
{
  "id": "PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj",
  "lastUpdated": 1789534675,
  "tracks": [
    {
      "id": "ekr2nIex040",
      "title": "ROSÉ & Bruno Mars - APT. (Official Music Video)",
      "artist": "ROSÉ",
      "durationMs": 174000,
      "thumbnailUrl": "https://i.ytimg.com/vi/ekr2nIex040/hqdefault.jpg"
    }
  ]
}
```

---

## 🛠️ Panduan Menjalankan Secara Lokal

### 1. Prasyarat
- Python 3.10+
- `ffmpeg` terpasang di sistem (`sudo apt install ffmpeg`)

### 2. Instalasi
```bash
# Clone repository
git clone <repo-url>
cd muyuapi

# Buat virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependensi
pip install -r requirements.txt

# Salin konfigurasi environment
cp .env.example .env
```

### 3. Menjalankan Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Akses dokumentasi Swagger UI di: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐳 Panduan Menjalankan dengan Docker

### Menggunakan Docker Compose
```bash
docker compose up -d --build
```
Cek logs:
```bash
docker compose logs -f
```

---

## 🧪 Menjalankan Pengujian (Testing)

Proyek ini telah dilengkapi dengan unit test dan integration test menggunakan `pytest`:

```bash
# Menjalankan seluruh test
.venv/bin/pytest -v
```

---

## 🌐 Konfigurasi Nginx Reverse Proxy (Domain: `muyu.tams.my.id`)

Berikut adalah contoh konfigurasi Nginx untuk mengarahkan domain `muyu.tams.my.id` ke backend MUYU API:

```nginx
server {
    server_name muyu.tams.my.id;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Buffer and timeout settings for audio streaming
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

