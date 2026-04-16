# Spectrum

Spectrum is the root workspace for the audio conversation analyzer we have been building.

It includes:

- `packages/core` for canonical schemas, dataset metadata, adapter registry, and shared models
- `packages/pipeline` for audio normalization, transcription, quality scoring, diarization-aware analysis, and bundle generation
- `packages/api` for the FastAPI backend used by uploads and session APIs
- `packages/dashboard` for the Next.js dashboard and session inspection UI
- `scripts` for local helper commands

## Repo policy

This repo is intended to stay code-first.

The following stay local and should not be committed:

- `data/`
- `runs/`
- `fixtures/demo_samples/`
- `.env`
- generated build output such as `.next/`
- large artifacts such as `.zip` and `.pdf`

Those rules are enforced in the root `.gitignore`.

## Local setup

Create the Python environment and install the app:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[server,audio,demo,dev]"
```

Install the dashboard workspace:

```bash
pnpm install
```

## Run locally

Start the API:

```bash
uv run uvicorn spectrum_api.main:app --reload --port 8013
```

Start the dashboard:

```bash
pnpm --dir packages/dashboard dev --port 3040
```

## Demo workflow

Analyze a file through the UI or generate local runs under `runs/`.

Useful local routes:

- dashboard: `http://127.0.0.1:3040`
- API health: `http://127.0.0.1:8013/healthz`

## Project structure

```text
spectrum/
  packages/
    api/
    core/
    dashboard/
    pipeline/
  scripts/
  tests/
  README.md
  pyproject.toml
  package.json
```

`spectrum_repo/` is no longer part of the canonical app layout.
