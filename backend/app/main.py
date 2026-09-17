import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.inference import runner
from app.routers import generate, health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("heartmula.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup: loading HeartMuLa model (this can take a while)...")
    try:
        runner.load()
    except Exception:
        logger.exception("Failed to load model at startup. /api/health will report model_loaded=false.")
    yield


app = FastAPI(title="HeartMuLa Test API", lifespan=lifespan)

app.include_router(health.router, prefix="/api")
app.include_router(generate.router, prefix="/api")

# Order matters: more specific mounts must be registered before the catch-all "/".
app.mount("/assets", StaticFiles(directory=settings.assets_dir), name="assets")
app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
