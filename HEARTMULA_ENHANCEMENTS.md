# Enhancing HeartMuLa Generation (and Bangladeshi-Accent Music Specifically)

Based on a close read of the HeartMuLa paper (Sections 2.3.4 and 3), cross-checked against
`heartlib`'s actual released pipeline code (`src/heartlib/pipelines/music_generation.py`), here's
what genuinely helps quality/control versus what's a myth, and concrete steps for this repo.

## 1. What the paper actually tells us about conditioning

Section 3.2 ("Conditioning Mechanism") is the single most useful part of the paper for our
purposes. It says tags are not a flat bag of words — they're sampled from **8 categories**
during training, each with a different selection probability (Table 6):

| Category   | Training selection probability | What it means for us |
|------------|--------------------------------|------------------------|
| Genre      | 0.95 | Almost always present during training — the single most reliable lever |
| Timbre     | 0.5  | Frequently present — real, moderate-strength control |
| Gender     | 0.375 | Real control for vocal gender (e.g. "male vocal") |
| Mood       | 0.325 | Real control, moderate strength |
| Instrument | 0.25 | Real control, moderate-low strength |
| Scene      | 0.2  | Real control, weaker |
| **Region** | 0.125 | Real control, weak but present — **this is the accent/locale lever** |
| Topic      | 0.1  | Weakest of the 8 — lyrical theme, minimal steering power |

Two important negative findings fall out of this table:
- **There is no BPM/tempo category anywhere in the taxonomy.** Any numeric tempo tag
  (`"120bpm"`, etc.) that we or a user passes in has no dedicated embedding path — it's just
  free tokens the model has never been deliberately trained to associate with tempo. Don't rely
  on it.
- **There is no free-form "instruction" or "prompt" category either.** Natural-language style
  instructions (e.g. "make the vocal breathy and intimate") were never a training signal in
  their own right — anything typed there just becomes more text tokens jammed into the same
  `<tag>` span, with no guarantee the model attends to it the way an instruction-tuned LLM would.

The paper also describes a third conditioning signal beyond tags and lyrics: **reference audio**
(`Cmuq`, a MuQ-MuLan embedding of a 10-second reference clip), used as a global style cue.
**This is not available to us** — `heartlib`'s public `preprocess()` explicitly does
`raise NotImplementedError` the moment `ref_audio` is passed, and the README lists reference
audio conditioning under unreleased TODOs. So no amount of backend cleverness gets us this
channel; it simply isn't in the shipped weights' usable inference path.

## 2. What this means for our backend/frontend (already implemented)

`backend/app/schemas.py`'s `GenerateRequest` now exposes the 8 real categories as first-class
fields (`genre`, `timbre`, `gender`, `mood`, `instrument`, `scene`, `region`, `topic`), folded
into the final tags string **in probability order** (highest-impact category first) — the
frontend's advanced-options panel mirrors this with the probabilities shown next to each label.
`bpm`/`instruction`/`prompt`/`tags` remain as an explicitly-labeled "not part of the paper's
taxonomy" section, since removing them entirely would lose a useful free-text escape hatch, but
they should not be your primary lever for anything.

## 3. Generating better Bangladeshi-accent music

Given the constraints above, here's the actual, paper-grounded approach — no reference-audio
shortcut exists, so it comes down to tags + lyrics:

1. **Set `region` explicitly.** Try `bangladesh` first; if results don't move enough, experiment
   with related values like `bengal`, `south asia`, or `dhaka` — we don't know the exact string
   vocabulary the training data used, so this needs empirical A/B testing on your own machine
   (see the experiment log format in section 4).
2. **Write lyrics in natural, colloquial Bangla**, not overly formal/literary Bangla — the
   lyrics themselves (tokenized by the Llama-3.2 tokenizer per the paper) are the primary carrier
   of language/phonetic identity, arguably more than any tag. Regional colloquialisms, if you
   want a distinctly Bangladeshi (vs. West Bengal/Kolkata) flavor, matter here.
3. **Pair `region` with `genre` values associated with Bangladesh**, e.g. `bangla folk`,
   `baul`, `bangladeshi pop` — since `genre` has by far the highest training probability (0.95),
   it likely does more work than `region` alone in steering toward a recognizable regional sound.
4. **Use `gender` deliberately** (`male vocal` / `female vocal`) — cheap, real, and removes one
   axis of randomness from your A/B comparisons.
5. **Keep `mood`/`instrument`/`scene` culturally consistent** — e.g. `instrument: harmonium,
   tabla, dotara` and `scene: village, riverside` for a folk feel, reinforcing (not fighting)
   the `region`/`genre` signal.
6. **Try a higher `cfg_scale`** (e.g. `2.0`-`2.5` instead of the default `1.5`). Classifier-free
   guidance strengthens adherence to the conditioning signal (tags + lyrics) at some cost to
   naturalness — since our accent-steering signal is a relatively low-probability category
   (`region` at 0.125), pushing `cfg_scale` up is a reasonable way to make the model lean on it
   harder. This is a general inference-time knob, not paper-verified for this specific purpose,
   so treat it as an experiment too.
7. **Don't expect a dramatic, reliable effect.** `region` sits at 0.125 selection probability —
   meaning during training, the vast majority of examples the model saw did *not* have a region
   tag at all. It's a real signal, but a weak one. Manage expectations accordingly, and lean on
   lyrics + genre + instrument as the heavier levers.

## 4. Suggested experiment log format

Since none of this is guaranteed, track what you actually try so you build real intuition
instead of re-guessing each time. Suggested columns: `region value`, `genre value`, `cfg_scale`,
`gender`, `output file`, `your subjective rating`, `notes`. A plain markdown table in
`outputs/bangla_songs/` works fine — no tooling needed for this.

## 5. Other things this repo could add later (not yet implemented)

- **`ref_audio` conditioning**: only possible once heartlib's upstream implements it (currently
  `NotImplementedError`) — nothing to do on our side until then.
- **Structural lyrics markers**: the paper confirms `[intro]`, `[verse]`, `[chorus]` structural
  markers are preserved through tokenization and materially help the model track song structure
  — we're already using this convention in all sample lyrics in this repo, so no change needed,
  just keep using it consistently for any new lyrics you write.
- **Category-aware validation**: right now the 8 fields are free-text strings with no
  validation against a known vocabulary (we don't have access to the training tag vocabulary).
  If HeartMuLa ever publishes their tag list, this backend could validate/autocomplete against
  it for more predictable results.
