from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_path: str = "/app/ckpt"
    model_version: str = "3B"

    mula_device: str = "cuda"
    codec_device: str = "cuda"
    mula_dtype: str = "bf16"
    codec_dtype: str = "fp32"
    lazy_load: bool = False

    output_dir: str = "/app/outputs"
    default_max_audio_length_ms: int = 60_000
    max_allowed_audio_length_ms: int = 240_000

    frontend_dir: str = "/app/frontend"
    assets_dir: str = "/app/assets"


settings = Settings()
