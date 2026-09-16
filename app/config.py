import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MUYU API"
    app_env: str = "production"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api"
    base_url: str = "https://muyu.tams.my.id"

    # Cache TTL (in seconds)
    playlist_cache_ttl: int = 86400  # 24 hours
    stream_cache_ttl: int = 14400    # 4 hours
    cache_db_path: str = "cache.db"

    # YouTube Proxy (optional)
    ytdlp_proxy: Optional[str] = None

    # CORS origins
    cors_origins: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

