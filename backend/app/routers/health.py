import torch
from fastapi import APIRouter

from app.config import settings
from app.inference import runner
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    gpu_name = None
    vram_free_mb = None
    vram_total_mb = None

    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        free_bytes, total_bytes = torch.cuda.mem_get_info(0)
        vram_free_mb = round(free_bytes / (1024 * 1024), 1)
        vram_total_mb = round(total_bytes / (1024 * 1024), 1)

    return HealthResponse(
        status="ok",
        model_loaded=runner.is_loaded,
        model_version=settings.model_version,
        mula_device=settings.mula_device,
        codec_device=settings.codec_device,
        gpu_name=gpu_name,
        vram_free_mb=vram_free_mb,
        vram_total_mb=vram_total_mb,
    )
