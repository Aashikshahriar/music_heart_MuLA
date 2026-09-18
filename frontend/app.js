const healthBanner = document.getElementById("health-banner");
const form = document.getElementById("generate-form");
const generateBtn = document.getElementById("generate-btn");
const statusSection = document.getElementById("status-section");
const jobIdEl = document.getElementById("job-id");
const jobStatusEl = document.getElementById("job-status");
const jobErrorEl = document.getElementById("job-error");
const player = document.getElementById("player");
const lyricsEl = document.getElementById("lyrics");
const tagsEl = document.getElementById("tags");

let pollTimer = null;

async function loadDefaults() {
  try {
    const [lyricsRes, tagsRes] = await Promise.all([
      fetch("/assets/lyrics.txt"),
      fetch("/assets/tags.txt"),
    ]);
    if (lyricsRes.ok) lyricsEl.value = await lyricsRes.text();
    if (tagsRes.ok) tagsEl.value = (await tagsRes.text()).trim();
  } catch (e) {
    // Non-fatal: user can still type their own lyrics/tags.
  }
}

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    healthBanner.className = "banner " + (data.model_loaded ? "ok" : "bad");
    const vram = data.vram_free_mb != null
      ? ` | VRAM free: ${(data.vram_free_mb / 1024).toFixed(1)} / ${(data.vram_total_mb / 1024).toFixed(1)} GB`
      : "";
    healthBanner.textContent =
      `Model loaded: ${data.model_loaded} | GPU: ${data.gpu_name || "n/a"}${vram}`;
  } catch (e) {
    healthBanner.className = "banner bad";
    healthBanner.textContent = "Could not reach backend /api/health";
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function pollJob(jobId) {
  const res = await fetch(`/api/jobs/${jobId}`);
  if (!res.ok) {
    jobStatusEl.textContent = "Failed to fetch job status";
    stopPolling();
    return;
  }
  const data = await res.json();
  jobStatusEl.textContent = `Status: ${data.status}`;

  if (data.status === "done") {
    stopPolling();
    jobErrorEl.textContent = "";
    player.src = data.audio_url;
    player.hidden = false;
    generateBtn.disabled = false;
  } else if (data.status === "error") {
    stopPolling();
    jobErrorEl.textContent = data.error || "Unknown error";
    generateBtn.disabled = false;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  stopPolling();
  generateBtn.disabled = true;
  player.hidden = true;
  jobErrorEl.textContent = "";
  statusSection.hidden = false;

  const bpmVal = document.getElementById("bpm").value;

  const body = {
    lyrics: lyricsEl.value,
    genre: document.getElementById("genre").value || undefined,
    timbre: document.getElementById("timbre").value || undefined,
    gender: document.getElementById("gender").value || undefined,
    mood: document.getElementById("mood").value || undefined,
    instrument: document.getElementById("instrument").value || undefined,
    scene: document.getElementById("scene").value || undefined,
    region: document.getElementById("region").value || undefined,
    topic: document.getElementById("topic").value || undefined,
    tags: tagsEl.value || undefined,
    bpm: bpmVal ? Number(bpmVal) : undefined,
    instruction: document.getElementById("instruction").value || undefined,
    prompt: document.getElementById("prompt").value || undefined,
    file_format: document.getElementById("file_format").value,
    max_audio_length_ms: Number(document.getElementById("max_audio_length_ms").value),
    topk: Number(document.getElementById("topk").value),
    temperature: Number(document.getElementById("temperature").value),
    cfg_scale: Number(document.getElementById("cfg_scale").value),
  };

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    jobIdEl.textContent = `Job ID: ${data.job_id}`;
    jobStatusEl.textContent = `Status: ${data.status}`;
    pollTimer = setInterval(() => pollJob(data.job_id), 2000);
  } catch (err) {
    jobErrorEl.textContent = err.message;
    generateBtn.disabled = false;
  }
});

loadDefaults();
checkHealth();
