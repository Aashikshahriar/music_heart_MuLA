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
    # heartlib's music_generation.py preprocess()), but the HeartMuLa paper
    # (Sec. 3.2, Table 6) reveals that tags are drawn from 8 real trained
    # categories, each with a different training selection probability
    # (i.e. a different real impact on generation):
    #   genre 0.95, timbre 0.5, gender 0.375, mood 0.325, instrument 0.25,
    #   scene 0.2, region 0.125, topic 0.1
    # `region` is the paper-justified lever for accent/locale (e.g.
    # "bangladesh"), NOT a generic "instruction" hint. There is no BPM
    # category anywhere in this taxonomy, confirming bpm is unsupported.
    # These fields are folded into one tags string before calling the
    # pipeline, ordered by training probability (highest first) since more
    # influential categories were more consistently paired with the model's
    # target audio during training.
    genre: Optional[str] = None
    timbre: Optional[str] = None
    gender: Optional[str] = None
    mood: Optional[str] = None
    instrument: Optional[str] = None
    scene: Optional[str] = None
    region: Optional[str] = None
    topic: Optional[str] = None

    # Free-text catch-all, and legacy/experimental fields not in the paper's
    # taxonomy. bpm is very likely a no-op - kept only for experimentation.
    tags: Optional[str] = None
    instruction: Optional[str] = None
    prompt: Optional[str] = None
    bpm: Optional[int] = Field(default=None, ge=20, le=300)

    file_format: FileFormat = "mp3"
    max_audio_length_ms: int = Field(default=0, ge=0)
    topk: int = Field(default=50, ge=1)
    temperature: float = Field(default=1.0, gt=0)
    cfg_scale: float = Field(default=1.5, ge=0)

    def build_tags_string(self) -> str:
        parts = [
            self.genre,
            self.timbre,
            self.gender,
            self.mood,
            self.instrument,
            self.scene,
            self.region,
            self.topic,
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
