from typing import Literal, Optional

from pydantic import BaseModel, Field

JobStatusLiteral = Literal["queued", "running", "done", "error"]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    mula_device: str
    codec_device: str
    gpu_name: Optional[str] = None
    vram_free_mb: Optional[float] = None
    vram_total_mb: Optional[float] = None


class GenerateRequest(BaseModel):
    lyrics: str
    tags: str
    max_audio_length_ms: int = Field(default=0, ge=0)
    topk: int = Field(default=50, ge=1)
    temperature: float = Field(default=1.0, gt=0)
    cfg_scale: float = Field(default=1.5, ge=0)


class GenerateResponse(BaseModel):
    job_id: str
    status: JobStatusLiteral


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatusLiteral
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None
    audio_url: Optional[str] = None
