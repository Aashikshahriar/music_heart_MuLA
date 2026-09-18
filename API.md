# HeartMuLa Test API

A small FastAPI wrapper around [HeartMuLa/heartlib](https://github.com/HeartMuLa/heartlib)'s
`HeartMuLaGenPipeline`, for locally testing lyrics+tags → music generation on a single GPU,
plus a minimal browser frontend at `/`.

Because generation is slow (the model runs at roughly real-time — a 60s clip takes ~60s+ to
produce), the API is **asynchronous**: you submit a job, poll its status, then download the
resulting audio once it's done. Only one generation runs at a time (single GPU).

## Prerequisites

- Docker Desktop installed and running, with GPU support enabled (WSL2 backend). Verify with:
  ```
  docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
  ```
  You should see your GPU listed. If this fails, GPU passthrough isn't set up in Docker Desktop
  and the container will fall back to CPU (extremely slow) or error out.
- Model checkpoints downloaded into `./ckpt` (see below) — several GB, only needs to be done once.

## 1. Build the image

```
docker compose build
```

## 2. Download checkpoints (one-time, ~6-15GB)

```
docker compose run --rm backend python scripts/download_checkpoints.py
```

This populates `./ckpt` on the host (mounted into the container), so it persists across
rebuilds. You do not need to repeat this unless you delete the `ckpt/` folder.

## 3. Start the server

```
docker compose up
```

The API + frontend are served at **http://localhost:8080**. On startup the server loads the
HeartMuLa-oss-3B pipeline into GPU memory — watch the logs for `Model loaded.` before issuing
requests; `/api/health` will report `model_loaded: false` until that finishes.

## Using the sample frontend

Open **http://localhost:8080** in a browser. It shows a health banner (model/GPU status),
a form pre-filled with sample lyrics/tags, a "Generate" button, and polls job status
automatically, rendering an `<audio>` player once the clip is ready.

## API reference

All endpoints are prefixed with `/api`.

### `GET /api/health`

Reports whether the model is loaded and current GPU/VRAM usage.

```
curl http://localhost:8080/api/health
```

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "3B",
  "mula_device": "cuda",
  "codec_device": "cuda",
  "gpu_name": "NVIDIA GeForce RTX 3060",
  "vram_free_mb": 9821.3,
  "vram_total_mb": 12288.0
}
```

### `POST /api/generate`

Submits a generation job. Returns immediately with a `job_id`.

| Field                 | Type   | Default | Notes                                          |
|-----------------------|--------|---------|-------------------------------------------------|
| `lyrics`               | string | required | Full lyrics text, sections like `[Verse]`/`[Chorus]` work well |
| `genre`                | string | optional | Real trained category, training prob. 0.95 (highest impact) |
| `timbre`               | string | optional | Real trained category, training prob. 0.5 |
| `gender`               | string | optional | Real trained category, training prob. 0.375, e.g. `male vocal` |
| `mood`                 | string | optional | Real trained category, training prob. 0.325 |
| `instrument`           | string | optional | Real trained category, training prob. 0.25 |
| `scene`                | string | optional | Real trained category, training prob. 0.2 |
| `region`               | string | optional | Real trained category, training prob. 0.125 — **the accent/locale lever**, e.g. `bangladesh` |
| `topic`                | string | optional | Real trained category, training prob. 0.1 (lowest impact) |
| `tags`                 | string | optional | Extra free-text tags, folded in alongside the above |
| `bpm`                  | int    | optional | **Not a real category — see note below** |
| `instruction`          | string | optional | Free-text catch-all, folded into tags |
| `prompt`               | string | optional | Free-text catch-all, folded into tags |
| `file_format`          | string | `mp3`   | `mp3` or `wav` |
| `max_audio_length_ms`  | int    | `60000` | Capped at `240000` (4 min, the upstream default) |
| `topk`                 | int    | `50`    | Sampling top-k |
| `temperature`          | float  | `1.0`   | Sampling temperature |
| `cfg_scale`            | float  | `1.5`   | Classifier-free guidance scale |

At least one of the tag-ish fields must be non-empty.

**Where the 8 category fields come from.** heartlib's pipeline code only ever conditions on one
flat `tags` text string (wrapped in `<tag>...</tag>`) plus `lyrics` — no chat-style system
prompt. But the HeartMuLa paper (Sec. 3.2, "Conditioning Mechanism", Table 6) reveals that
during training, tags were sampled from **8 specific categories**, each with a different
selection probability — i.e. a different real, measured impact on what the model learned to
respond to: `genre` 0.95, `timbre` 0.5, `gender` 0.375, `mood` 0.325, `instrument` 0.25,
`scene` 0.2, `region` 0.125, `topic` 0.1. This backend exposes those 8 as real fields and folds
them into one tags string, ordered by that same probability (highest-impact first). `region` is
the paper-justified way to steer locale/accent (e.g. `bangladesh`) — not a vague "make it sound
Bangladeshi" instruction string. `bpm` is **not** in this taxonomy at all — it was never a
tag category the model was trained on, so treat it as an unverified long-shot, not a control.
`tags`/`instruction`/`prompt` remain free-text catch-alls for anything outside the 8 categories.
See `HEARTMULA_ENHANCEMENTS.md` for the full writeup and more tuning suggestions.

```
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "lyrics": "[Verse]\nSample lyrics line one\nSample lyrics line two\n[Chorus]\nSinging in the sun",
    "genre": "acoustic pop",
    "gender": "female vocal",
    "region": "bangladesh",
    "mood": "warm, intimate",
    "file_format": "mp3",
    "max_audio_length_ms": 15000
  }'
```

```json
{ "job_id": "a1b2c3d4e5f6", "status": "queued" }
```

### `GET /api/jobs/{job_id}`

Poll this until `status` is `done` or `error`.

```
curl http://localhost:8080/api/jobs/a1b2c3d4e5f6
```

```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "done",
  "created_at": 1758100000.1,
  "started_at": 1758100000.4,
  "finished_at": 1758100016.9,
  "error": null,
  "audio_url": "/api/jobs/a1b2c3d4e5f6/audio"
}
```

Status values: `queued` → `running` → `done` | `error`.

### `GET /api/jobs/{job_id}/audio`

Streams the generated `.mp3` once the job is `done` (returns `409` if not ready yet).

```
curl -o output.mp3 http://localhost:8080/api/jobs/a1b2c3d4e5f6/audio
```

## End-to-end curl example

```bash
JOB_ID=$(curl -s -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"lyrics": "[Verse]\nTesting one two three", "tags": "piano,happy", "max_audio_length_ms": 15000}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

echo "Job: $JOB_ID"

# Poll every 3s until done
while true; do
  STATUS=$(curl -s http://localhost:8080/api/jobs/$JOB_ID | python -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "status: $STATUS"
  [ "$STATUS" = "done" ] || [ "$STATUS" = "error" ] && break
  sleep 3
done

curl -o output.mp3 http://localhost:8080/api/jobs/$JOB_ID/audio
```

## Troubleshooting

- **CUDA out of memory**: lower `max_audio_length_ms`, or set `LAZY_LOAD: "true"` in
  `docker-compose.yml` (loads HeartMuLa/HeartCodec on demand and frees them after each
  generation, trading latency for VRAM headroom).
- **Generation feels slow**: expected — the model runs at roughly real-time (RTF ≈ 1.0), so a
  60-second clip takes on the order of a minute.
- **`docker run --gpus all ... nvidia-smi` fails**: Docker Desktop's WSL2 GPU support isn't
  enabled. Check Settings → Resources → WSL Integration, and that you have a recent NVIDIA
  driver. Restart Docker Desktop after changes.
- **`/api/health` shows `model_loaded: false` indefinitely**: check `docker compose logs
  backend` — most often this means the checkpoints in `./ckpt` aren't in the expected
  structure (see step 2), or the container couldn't allocate GPU memory.
