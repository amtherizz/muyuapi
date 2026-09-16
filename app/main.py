from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.playlist import router as playlist_router
from app.routes.track import router as track_router
from app.services.cache import cache_service

# Setup logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("muyuapi")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: prune expired cache items
    logger.info("Memulai %s di environment: %s", settings.app_name, settings.app_env)
    cache_service.prune_expired()
    yield
    # Shutdown
    logger.info("Menghentikan %s...", settings.app_name)


app = FastAPI(
    title="MUYU API - SONIK / BEAT Backend",
    description="Backend API untuk mendukung fitur sinkronisasi YouTube dan pemutaran audio di aplikasi SONIK / BEAT.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0"
    }

# Mount routers with configured API prefix (e.g. /api)
prefix = settings.api_prefix.rstrip("/")
if prefix:
    app.include_router(playlist_router, prefix=prefix)
    app.include_router(track_router, prefix=prefix)

# Also mount at root without prefix for direct / reverse-proxy flexibility
app.include_router(playlist_router)
app.include_router(track_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

