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

Spectrum is an open-source call analytics SDK and UI for teams that want structured voice intelligence without building the full stack from scratch.

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

## Capability status

### Core platform

| Area | Status | Notes |
| --- | --- | --- |
| Canonical session bundle | `✓ Done` | Quality, environment, turns, events, questions, signals, transcript spans, diarization, waveform, spectrogram, and timeline tracks are modeled in one shared schema. |
| Persisted run artifacts | `✓ Done` | Analysis outputs are written under `runs/<session_id>/...` with `bundle.json` as the main read model. |
| Dataset and demo importers | `✓ Done` | Includes demo-pack support and curated local materialized dataset import paths. |
| Package structure | `✓ Done` | Split across `core`, `pipeline`, `api`, and `dashboard`. |

### Analysis capabilities

| Capability | Status | Notes |
| --- | --- | --- |
| Audio normalization | `✓ Done` | Includes normalized and telephony-rendered audio artifacts. |
| Quality scoring | `✓ Done` | SNR, noise, clipping, VAD issues, and explainability flags are supported. |
| Turn and structure analysis | `✓ Done` | Turns, pauses, overlaps, events, and response timing are part of the pipeline. |
| Transcript sentence and token spans | `✓ Done` | Sentence-level and token-level transcript artifacts are supported. |
| Human vs AI speaker roles | `✓ Done` | Includes automatic role assignment plus manual override support. |
| Waveform and spectrogram views | `✓ Done` | Both are rendered in the session workspace. |
| Prosody tracks and cue artifacts | `✓ Done` | Pitch, energy, speaking-rate tracks, and non-verbal cue outputs are present. |
| Uploaded-audio diarization strength | `~ In progress` | Works best when stronger adapters are available; degraded mode still needs improvement. |
| Non-verbal attribution on arbitrary uploads | `~ In progress` | Stronger on benchmark/demo-backed sessions than on all uploaded audio. |
| Accent / age / profile depth | `~ In progress` | Confidence-gated today; several fields remain intentionally conservative. |
| Emotion and behavior benchmarking depth | `~ In progress` | A number of signals still rely on heuristics or light model assistance. |

### Product surface

| Surface | Status | Notes |
| --- | --- | --- |
| Upload and async processing flow | `✓ Done` | Includes session creation, upload, processing, and progress reporting. |
| Overview and compare screens | `✓ Done` | Dashboard supports session browsing and side-by-side comparison. |
| Session workspace | `✓ Done` | Transcript-first and waveform-first review experiences are both present. |
| Role-aware transcript filtering | `✓ Done` | Human-only, Human + AI, and AI context views are supported. |
| Session APIs | `✓ Done` | Bundle, transcript, profile, roles, waveform, spectrogram, prosody, diarization, and cue endpoints exist. |
| Public SDK ergonomics | `~ In progress` | Internal interfaces are strong, but the external developer-facing SDK surface is not finalized yet. |
| Hosted / multi-tenant product layer | `○ Not done yet` | No auth, tenancy, or managed cloud product layer yet. |
| Privacy / governance layer | `○ Not done yet` | No finalized policy or enterprise controls yet. |

### Validation and research

| Area | Status | Notes |
| --- | --- | --- |
| Python API and pipeline tests | `✓ Done` | Core workflow behavior is covered by tests. |
| Dashboard buildability | `✓ Done` | The UI builds from the workspace. |
| Cross-region and cross-language calibration | `○ Not done yet` | Still needs broader evaluation and grounding. |
| Long-call cohort analytics | `~ In progress` | The foundation is there, but the aggregate analytics layer needs to go further. |
| Benchmark breadth | `~ In progress` | Coverage exists, but is not yet comprehensive. |

## Near-term roadmap

| Priority | Area | What comes next |
| --- | --- | --- |
| 1 | Uploaded-audio path | Harden default transcription + diarization and improve degraded-mode behavior. |
| 2 | SDK surface | Turn the current bundle and pipeline contracts into a documented developer-facing SDK. |
| 3 | Signal credibility | Replace more heuristics with stronger adapters, benchmarks, and clearer calibration. |
| 4 | Aggregate analytics | Push the overview toward a fuller multi-session voice analytics console. |
| 5 | Documentation | Publish a clearer roadmap and separate stable surfaces from experimental ones. |

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

The project is meant to grow into a proper open-source voice analytics foundation:

- clear canonical schemas
- transparent outputs
- reusable ingestion and analysis building blocks
- a lightweight but useful inspection UI
- a practical starting point for teams building interview, support, research, and voice AI analytics products

## License

[MIT](./LICENSE)
