import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import torch

from app.config import settings

logger = logging.getLogger("heartmula.inference")

_DTYPE_MAP = {
    "fp32": torch.float32,
    "float32": torch.float32,
    "fp16": torch.float16,
    "float16": torch.float16,
    "bf16": torch.bfloat16,
    "bfloat16": torch.bfloat16,
}


class ModelRunner:
    """Loads the HeartMuLa pipeline once and serializes access to the single GPU."""

    def __init__(self) -> None:
        self._pipe = None
        # A single worker serializes GPU access: only one generation runs at a time.
        self._executor = ThreadPoolExecutor(max_workers=1)

    def load(self) -> None:
        from heartlib import HeartMuLaGenPipeline

        logger.info("Loading HeartMuLaGenPipeline from %s", settings.model_path)
        self._pipe = HeartMuLaGenPipeline.from_pretrained(
            settings.model_path,
            device={
                "mula": torch.device(settings.mula_device),
                "codec": torch.device(settings.codec_device),
            },
            dtype={
                "mula": _DTYPE_MAP[settings.mula_dtype],
                "codec": _DTYPE_MAP[settings.codec_dtype],
            },
            version=settings.model_version,
            lazy_load=settings.lazy_load,
        )
        logger.info("Model loaded.")

    @property
    def is_loaded(self) -> bool:
        return self._pipe is not None

    def generate_sync(
        self,
        lyrics: str,
        tags: str,
        save_path: str,
        max_audio_length_ms: int,
        topk: int,
        temperature: float,
        cfg_scale: float,
    ) -> None:
        if self._pipe is None:
            raise RuntimeError("Model is not loaded yet")

        with tempfile.TemporaryDirectory() as tmp_dir:
            lyrics_path = Path(tmp_dir) / "lyrics.txt"
            tags_path = Path(tmp_dir) / "tags.txt"
            lyrics_path.write_text(lyrics, encoding="utf-8")
            tags_path.write_text(tags, encoding="utf-8")

            with torch.no_grad():
                self._pipe(
                    {"lyrics": str(lyrics_path), "tags": str(tags_path)},
                    max_audio_length_ms=max_audio_length_ms,
                    save_path=save_path,
                    topk=topk,
                    temperature=temperature,
                    cfg_scale=cfg_scale,
                )

    def submit_callable(self, fn, *args, **kwargs):
        """Runs fn on the single-worker executor, returns a Future."""
        return self._executor.submit(fn, *args, **kwargs)


runner = ModelRunner()
