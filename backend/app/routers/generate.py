from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.jobs import job_manager
from app.schemas import GenerateRequest, GenerateResponse, JobStatusResponse

router = APIRouter(tags=["generate"])


@router.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    max_len = req.max_audio_length_ms or settings.default_max_audio_length_ms
    if max_len > settings.max_allowed_audio_length_ms:
        raise HTTPException(
            status_code=400,
            detail=f"max_audio_length_ms must be <= {settings.max_allowed_audio_length_ms}",
        )

    tags = req.build_tags_string()
    if not tags:
        raise HTTPException(
            status_code=400,
            detail="At least one of tags/genre/bpm/instruction/prompt must be provided",
        )

    job = job_manager.create(
        lyrics=req.lyrics,
        tags=tags,
        max_audio_length_ms=max_len,
        topk=req.topk,
        temperature=req.temperature,
        cfg_scale=req.cfg_scale,
        file_format=req.file_format,
    )
    return GenerateResponse(job_id=job.job_id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: str) -> JobStatusResponse:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    audio_url = f"/api/jobs/{job_id}/audio" if job.status == "done" else None
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
        audio_url=audio_url,
    )


@router.get("/jobs/{job_id}/audio")
def get_job_audio(job_id: str):
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail=f"job is not done yet (status={job.status})")

    path = Path(job.output_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="audio file not found")

    media_type = "audio/wav" if job.file_format == "wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type, filename=path.name)
