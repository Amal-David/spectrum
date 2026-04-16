# Spectrum

Spectrum is an open voice analytics platform for turning raw conversations into structured emotional, behavioral, and operational signals.

The project is built around a simple idea: transcripts alone are not enough. Teams running interviews, support calls, research conversations, reminder flows, and AI voice sessions need to understand pauses, hesitation, interruptions, talk balance, response latency, non-verbal cues, emotional shifts, and quality conditions, not just the words that were said.

Think of Spectrum as Google Analytics for voice:

- a reusable analytics SDK for audio-native products
- a canonical schema for voice signals
- a lightweight UI for exploring sessions, timelines, transcript emotion, and speaker behavior

## Vision

Spectrum aims to be the open foundation for voice analytics:

- ingest raw calls or audio clips
- normalize them into a canonical session bundle
- extract quality, structure, transcript, emotion, prosody, and behavioral signals
- let downstream teams build vertical workflows on top of that foundation

That foundation should work across:

- user interviews
- hiring and screening calls
- support and ops calls
- AI voice agents
- research and discovery conversations
- any voice-first workflow where "how it was said" matters as much as "what was said"

## Current state

Spectrum is already a real working prototype, not just a concept.

Today the repo includes:

- a Python core for schemas, adapters, datasets, and run artifacts
- an analysis pipeline that produces canonical `bundle.json` session outputs
- a FastAPI backend for upload, processing, session reads, and manual speaker-role overrides
- a Next.js dashboard for overview, compare, session detail, transcript inspection, waveform-first review, and upload/progress flows
- a demo/bootstrap path for local sample sessions and dataset-backed examples

The current product direction is:

- human-centered conversation analysis
- quality-aware interpretation instead of naive emotion overclaiming
- visible explainability masks and provenance
- open, inspectable outputs instead of opaque one-score APIs

## What is already implemented

### Platform shape

- canonical session bundles with quality, environment, turns, events, questions, signals, transcript spans, profile fields, diarization, waveform, spectrogram, and timeline tracks
- persisted run artifacts under `runs/<session_id>/...`
- dataset and importer support for demo-pack and curated local materialized datasets

### Analysis pipeline

- audio normalization and telephony render generation
- quality scoring, SNR/noise heuristics, and explainability flags
- turn and structure derivation
- transcript span generation with sentence and token overlays
- confidence-gated profile display
- waveform, spectrogram, prosody tracks, and non-verbal cue artifacts
- human-vs-AI role assignment with manual override support
- OpenAI-assisted analysis path plus local fallback behavior

### Product surface

- upload and async analysis progress flow
- session overview and compare screens
- transcript-first and waveform-first session workspace
- speaker-role controls
- role-aware transcript filtering
- session APIs for bundle, transcript, profile, roles, waveform, spectrogram, prosody, diarization, and cues

### Validation

- Python tests for pipeline and API behavior
- dashboard buildable from the repo workspace

## What is not done yet

Spectrum is still early, and several important parts remain prototype-grade or incomplete.

### Model depth

- diarization for uploaded audio still depends on optional stronger adapters
- non-verbal cue attribution is strongest for benchmark/demo data and weaker for arbitrary uploads
- profile outputs such as accent and age-band are still conservative and often gated or unavailable
- many emotion and behavior signals remain heuristic or lightly model-assisted rather than deeply benchmarked

### Product maturity

- no polished package distribution story yet
- no stable SDK API surface for external developers
- no auth, multi-tenant storage, hosted service, or production deployment story
- no finalized data governance, privacy posture, or enterprise controls

### Research coverage

- cross-region, cross-language, and cross-demographic calibration is not done
- long-call analytics and aggregate cohort analytics are still early
- benchmark coverage is partial rather than comprehensive

## What should happen soon

The next useful milestones are:

1. Harden the uploaded-audio path.
   Ship a stronger default transcription + diarization stack and improve degraded-mode messaging.

2. Stabilize the SDK surface.
   Turn the current canonical bundle and pipeline interfaces into a documented developer-facing API.

3. Improve signal credibility.
   Replace more heuristics with stronger adapters, better benchmark validation, and clearer confidence calibration.

4. Expand aggregate analytics.
   Make the overview feel more like a true voice analytics console across many sessions, not just single-session inspection.

5. Document the roadmap.
   Separate what Spectrum guarantees today from what is experimental.

## Architecture

```text
spectrum/
  packages/
    api/        FastAPI service and upload/session endpoints
    core/       canonical models, dataset helpers, registry metadata
    dashboard/  Next.js UI for overview, compare, and session review
    pipeline/   normalization, analysis, importers, run persistence
  scripts/      local helpers
  tests/        API and pipeline coverage
```

## Local development

Create the Python environment and install the app:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[server,audio,demo,dev]"
```

Install dashboard dependencies:

```bash
pnpm install
```

Run the API:

```bash
uv run uvicorn spectrum_api.main:app --reload --port 8013
```

Run the dashboard:

```bash
pnpm --dir packages/dashboard dev --port 3040
```

## Repo policy

This repo is intentionally code-first.

These stay local and are not intended for source control:

- `data/` raw and cached dataset payloads
- `runs/` generated analysis outputs
- `fixtures/demo_samples/` local media
- `.env` and any local secrets
- generated build output such as `.next/`

The root `.gitignore` is configured to keep those local-only artifacts out of git while preserving safe placeholder files and lightweight manifests.

## Open source status

Spectrum is MIT licensed.

The project is meant to grow into a proper open source voice analytics foundation:

- clear canonical schemas
- transparent outputs
- reusable ingestion and analysis building blocks
- a lightweight but useful inspection UI

If you are evaluating the project today, treat it as a serious open prototype: already useful for demos, exploration, and foundational product work, but not yet the finished production voice analytics stack described by the full vision.

## License

[MIT](./LICENSE)
