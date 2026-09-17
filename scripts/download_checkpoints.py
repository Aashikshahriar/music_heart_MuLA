"""Downloads the HeartMuLa checkpoints required for the 3B pipeline into ./ckpt.

Run inside the backend container so files land on the host via the mounted
volume, e.g.:

    docker compose run --rm backend python scripts/download_checkpoints.py
"""

from huggingface_hub import snapshot_download

CKPT_ROOT = "/app/ckpt"

DOWNLOADS = [
    ("HeartMuLa/HeartMuLaGen", CKPT_ROOT),
    ("HeartMuLa/HeartMuLa-oss-3B-happy-new-year", f"{CKPT_ROOT}/HeartMuLa-oss-3B"),
    ("HeartMuLa/HeartCodec-oss-20260123", f"{CKPT_ROOT}/HeartCodec-oss"),
]


def main() -> None:
    for repo_id, local_dir in DOWNLOADS:
        print(f"Downloading {repo_id} -> {local_dir}")
        snapshot_download(repo_id=repo_id, local_dir=local_dir)
    print("All checkpoints downloaded.")


if __name__ == "__main__":
    main()
