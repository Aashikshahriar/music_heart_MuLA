"""Generates a batch of original Bangla songs via the local HeartMuLa test API,
saves the resulting audio locally, and writes a markdown report with timings.

Run on the HOST (not inside the container) once `docker compose up` is running
and /api/health reports model_loaded: true:

    python scripts/generate_bangla_songs.py
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "http://localhost:8080"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "bangla_songs"
REPORT_PATH = Path(__file__).resolve().parent.parent / "outputs" / "bangla_songs" / "generation_report.md"
POLL_INTERVAL_S = 3

SONGS = [
    {
        "slug": "borsha_monsoon",
        "title": "Borsha (Monsoon)",
        "mood": "Melancholic folk",
        "tags": "bengali,folk,rain,melancholic,acoustic",
        "lyrics": """[Verse]
আকাশে মেঘ জমেছে আজ
বৃষ্টি নামে ঝিরিঝিরি
নদীর জলে ঢেউ জাগে
মনটা কেমন উদাসী

[Chorus]
বর্ষা এলো প্রাণে আমার
ভিজিয়ে দিলো সব কথা
স্মৃতির পাতা খুলে গেলো
বৃষ্টি ভেজা এই বেলা

[Verse]
জানালাতে জলের ফোঁটা
মনে পড়ে পুরনো দিন
তুমি ছিলে পাশে আমার
এখন শুধু একলা চিন

[Outro]
বৃষ্টি থামুক না থামুক
মনে তুমি রয়ে যাবে""",
        "max_audio_length_ms": 60000,
    },
    {
        "slug": "bondhutto_friendship",
        "title": "Bondhutto (Friendship)",
        "mood": "Upbeat pop",
        "tags": "bengali,pop,happy,acoustic,uplifting",
        "lyrics": """[Verse]
পথে চলি হাতে হাত রেখে
হাসি আনন্দে দিন কাটে
কোনো কষ্ট নেই মনে আজ
বন্ধু তুমি পাশে থেকে

[Chorus]
বন্ধুত্বের এই গান গাই
সুখে দুখে পাশে রই
তুমি আমি একসাথে সব
জীবনটা রঙিন হই

[Verse]
ছোট্ট বেলার স্মৃতি নিয়ে
বড় হলাম দুজন মিলে
হাজার বাধা এলেও পথে
থাকবো পাশে সব সময়ে

[Outro]
বন্ধু তুমি চিরদিনের
এই গান তোমার তরে""",
        "max_audio_length_ms": 60000,
    },
    {
        "slug": "mayer_bhalobasha_mothers_love",
        "title": "Mayer Bhalobasha (Mother's Love)",
        "mood": "Emotional piano",
        "tags": "bengali,emotional,piano,soft,heartfelt",
        "lyrics": """[Verse]
মায়ের কোলে ঘুম আসতো
নরম হাতের পরশ পেয়ে
আজও মনে পড়ে সেসব
মায়ের গল্প শুনতে শুনতে

[Chorus]
মা তুমি আমার আশ্রয়
তোমার মতো কেউ নাই
তোমার আঁচল ছায়াতে
সব কষ্ট ভুলে যাই

[Verse]
কত রাত জেগে থেকেছো
আমার জন্য মা তুমি
আজ আমি বড় হলেও
তোমাকেই সব জানি আমি

[Outro]
মা গো তোমায় ভালোবাসি
এই গান শুধু তোমার জন্য""",
        "max_audio_length_ms": 60000,
    },
    {
        "slug": "gramer_sokal_village_morning",
        "title": "Gramer Sokal (Village Morning)",
        "mood": "Peaceful traditional folk",
        "tags": "bengali,folk,flute,peaceful,traditional",
        "lyrics": """[Verse]
ভোরের আলোয় গ্রাম জেগে ওঠে
পাখির ডাকে ঘুম ভাঙে
কৃষক চলে মাঠের পথে
কাঁধে নিয়ে লাঙল কোদাল

[Chorus]
গ্রামের এই শান্ত সকাল
মনটা ভরে যায় শান্তিতে
বাঁশির সুরে ভেসে বেড়াই
সবুজ মাঠের ওই প্রান্তে

[Verse]
নদীর ধারে রাখাল ছেলে
গরু চরায় দিনভর
মাটির গন্ধে ভরা বাতাস
এই তো আমার আপন ঘর

[Outro]
এই গ্রাম আমার প্রাণের টানে
বারবার ফিরে আসি""",
        "max_audio_length_ms": 60000,
    },
    {
        "slug": "pohela_boishakh_festival",
        "title": "Pohela Boishakh (New Year Festival)",
        "mood": "Energetic celebration",
        "tags": "bengali,festive,dhol,energetic,celebration",
        "lyrics": """[Verse]
নতুন বছর এলো আজ
সাজলো সবাই রঙিন সাজে
পথে পথে গানের সুর
ঢাকের বাদ্যি বাজে বাজে

[Chorus]
এসো হে বৈশাখ এসো
নতুন আশা নিয়ে এসো
পুরনো সব দুঃখ ভুলে
আনন্দে আজ মেতে উঠো

[Verse]
ইলিশ পান্তা খাওয়ার ধুম
মেলা বসে গ্রামে গ্রামে
হাসি খুশি সবার মুখে
নতুন বছর এই দিনে

[Outro]
শুভ নববর্ষ সবাইকে
আনন্দে ভরুক জীবনটা""",
        "max_audio_length_ms": 60000,
    },
]


def http_json(method, path, payload=None, timeout=30):
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(path, dest: Path, timeout=60):
    url = f"{BASE_URL}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        dest.write_bytes(resp.read())


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    slugs_filter = set(sys.argv[1:]) or None
    songs = [s for s in SONGS if slugs_filter is None or s["slug"] in slugs_filter]

    health = http_json("GET", "/api/health")
    print(f"Health check: {health}")
    if not health.get("model_loaded"):
        print("WARNING: model_loaded is false. Generation requests will fail.")

    for song in songs:
        print(f"\n=== Submitting: {song['title']} ===")
        submit_t0 = time.time()
        resp = http_json(
            "POST",
            "/api/generate",
            {
                "lyrics": song["lyrics"],
                "tags": song["tags"],
                "max_audio_length_ms": song["max_audio_length_ms"],
            },
        )
        job_id = resp["job_id"]
        print(f"job_id={job_id} status={resp['status']}")

        status = resp["status"]
        error = None
        while status in ("queued", "running"):
            time.sleep(POLL_INTERVAL_S)
            job = http_json("GET", f"/api/jobs/{job_id}")
            status = job["status"]
            elapsed = time.time() - submit_t0
            print(f"  [{elapsed:6.1f}s] status={status}")
            if status == "error":
                error = job.get("error")

        submit_t1 = time.time()
        duration_s = submit_t1 - submit_t0

        output_path = None
        if status == "done":
            output_path = OUTPUT_DIR / f"{song['slug']}.mp3"
            download_file(f"/api/jobs/{job_id}/audio", output_path)
            print(f"  Saved -> {output_path} ({duration_s:.1f}s total)")
        else:
            print(f"  FAILED: {error}")

        results.append(
            {
                **song,
                "job_id": job_id,
                "status": status,
                "error": error,
                "duration_s": round(duration_s, 1),
                "output_path": str(output_path) if output_path else None,
            }
        )

    write_report(results)
    print(f"\nReport written to {REPORT_PATH}")


def write_report(results):
    lines = [
        "# Bangla Song Generation Report",
        "",
        f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"Total songs: {len(results)}",
        f"Total wall-clock time: {sum(r['duration_s'] for r in results):.1f}s "
        f"({sum(r['duration_s'] for r in results) / 60:.1f} min)",
        "",
        "| # | Title | Mood | Tags | Length (ms) | Duration (s) | Status | File |",
        "|---|-------|------|------|-------------|---------------|--------|------|",
    ]
    for i, r in enumerate(results, 1):
        file_display = Path(r["output_path"]).name if r["output_path"] else "-"
        lines.append(
            f"| {i} | {r['title']} | {r['mood']} | {r['tags']} | "
            f"{r['max_audio_length_ms']} | {r['duration_s']} | {r['status']} | {file_display} |"
        )

    lines.append("")
    lines.append("## Details")
    for r in results:
        lines.append("")
        lines.append(f"### {r['title']} (`{r['job_id']}`)")
        lines.append(f"- Status: {r['status']}")
        lines.append(f"- Generation duration: {r['duration_s']}s")
        lines.append(f"- Tags: `{r['tags']}`")
        lines.append(f"- Output: `{r['output_path']}`" if r["output_path"] else "- Output: none (failed)")
        if r["error"]:
            lines.append(f"- Error: {r['error']}")
        lines.append("- Lyrics:")
        lines.append("```")
        lines.append(r["lyrics"])
        lines.append("```")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
