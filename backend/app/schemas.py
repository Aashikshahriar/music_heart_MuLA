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


FileFormat = Literal["mp3", "wav"]


class GenerateRequest(BaseModel):
    lyrics: str

    # The underlying model only ever sees one flat "tags" text string (see
    # heartlib's music_generation.py preprocess()) - there's no structured
    # genre/bpm/instruction conditioning, and no chat-style system prompt.
    # These fields are a convenience layer: the backend folds them into a
    # single tags string before calling the pipeline. `bpm` in particular is
    # best-effort - the model's training tags (README examples: "piano",
    # "happy", "wedding") don't show any numeric tempo tokens, so there's no
    # guarantee it's a respected control.
    tags: Optional[str] = None
    genre: Optional[str] = None
    bpm: Optional[int] = Field(default=None, ge=20, le=300)
    instruction: Optional[str] = None
    prompt: Optional[str] = None

    file_format: FileFormat = "mp3"
    max_audio_length_ms: int = Field(default=0, ge=0)
    topk: int = Field(default=50, ge=1)
    temperature: float = Field(default=1.0, gt=0)
    cfg_scale: float = Field(default=1.5, ge=0)

    def build_tags_string(self) -> str:
        parts = [
            self.genre,
            f"{self.bpm}bpm" if self.bpm else None,
            self.instruction,
            self.prompt,
            self.tags,
        ]
        return ",".join(p.strip() for p in parts if p and p.strip())


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
