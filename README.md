# HeartMuLa Local Test Stack

A Dockerized FastAPI backend + minimal browser frontend for locally testing
[HeartMuLa/heartlib](https://github.com/HeartMuLa/heartlib)'s lyrics+tags → music generation
model (HeartMuLa-oss-3B) on a single consumer GPU.

Tested on: RTX 3060 12GB, 32GB system RAM, Windows 11 + Docker Desktop (WSL2 backend).

## What's in here

```
heartlib/          # upstream repo, `git clone`d locally (gitignored, not tracked here)
docker/Dockerfile  # python:3.10-slim + torch(cu121) + heartlib + backend
docker-compose.yml # backend service definition, GPU reservation, volumes
backend/           # FastAPI app (model loading, job queue, /api/* routes)
scripts/           # one-off checkpoint download script
frontend/          # static HTML/JS/CSS test console served by the backend
assets/            # sample lyrics.txt / tags.txt (copied from heartlib)
ckpt/              # downloaded model checkpoints (gitignored, several GB)
outputs/           # generated .mp3 files (gitignored)
API.md             # full API reference + curl examples + troubleshooting
```

See [API.md](./API.md) for the complete endpoint reference and test walkthrough.

## Prerequisites

- Docker Desktop, running, with GPU support enabled (WSL2 backend on Windows).
  Verify with:
  ```
  docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
  ```
  You should see your GPU listed.
- ~15-20GB free disk space (Docker image + checkpoints).
- A Hugging Face account is **not** required for these public checkpoints.

## Implementation / setup steps

1. **Clone the upstream model repo** (not tracked in this repo, pulled in at build time):
   ```
   git clone https://github.com/HeartMuLa/heartlib.git
   ```

2. **Build the backend image**:
   ```
   docker compose build
   ```

3. **Download the checkpoints** (one-time, ~10-15GB total, lands in `./ckpt` on the host):
   ```
   docker compose run --rm backend python /app/scripts/download_checkpoints.py
   ```

4. **Start the server**:
   ```
   docker compose up
   ```
   Wait for `Model loaded.` in the logs, then open **http://localhost:8080** for the
   sample frontend, or hit `http://localhost:8080/api/health` to confirm the model
   and GPU are ready.

5. **Test generation** — either through the browser UI, or via curl (see
   [API.md](./API.md) for the full request/response reference and an end-to-end example).

To stop the stack: `docker compose down`. Checkpoints and generated audio persist in
`./ckpt` and `./outputs` across restarts/rebuilds since they're bind-mounted volumes.

## Rebuilding after code changes

```
docker compose up --build
```

## Pushing this repo to a remote

This directory has been initialized as a git repo but has no remote configured yet.
Once you've created an (empty) repository on GitHub/GitLab/etc.:

```bash
git add .
git commit -m "Initial commit: HeartMuLa test backend, frontend, and docs"
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

For subsequent changes:

```bash
git add .
git commit -m "<describe your change>"
git push
```

Notes:
- `heartlib/` is gitignored (it's the upstream project, cloned separately per the setup
  steps above, not vendored into this repo).
- `ckpt/` and `outputs/` are gitignored — checkpoints are multi-GB and regenerable via
  step 3 above; don't try to commit them.
