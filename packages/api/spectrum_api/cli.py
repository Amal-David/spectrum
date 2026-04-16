from __future__ import annotations

import argparse
import sys
import uuid
import webbrowser
from pathlib import Path

from spectrum_pipeline.importers import import_demo_pack
from spectrum_pipeline.openai_provider import load_local_env
from spectrum_pipeline.service import ProcessSessionOptions, create_session_result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spectrum developer workflow helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze one local audio file into a session bundle")
    analyze.add_argument("audio_file", help="Path to a local WAV/MP3/M4A file")
    analyze.add_argument("--analysis-mode", choices=["voice_profile", "conversation_analytics", "full"], default="full")
    analyze.add_argument("--title", help="Optional session title override")
    analyze.add_argument("--language", help="Optional language hint")
    analyze.add_argument("--dashboard-url", default="http://127.0.0.1:3000", help="Dashboard base URL for --open")
    analyze.add_argument("--open", action="store_true", help="Open the resulting session in the browser")

    demo = subparsers.add_parser("demo", help="Import bundled demo sessions")
    demo.add_argument("--dashboard-url", default="http://127.0.0.1:3000", help="Dashboard base URL for --open")
    demo.add_argument("--open", action="store_true", help="Open the dashboard after importing the demo pack")

    serve = subparsers.add_parser("serve", help="Run the Spectrum API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    return parser


def _open(url: str, should_open: bool) -> None:
    if should_open:
        webbrowser.open(url)


def _cmd_analyze(args: argparse.Namespace) -> int:
    load_local_env()
    audio_path = Path(args.audio_file).expanduser().resolve()
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")

    job_id = str(uuid.uuid4())
    metadata = {
        "title": args.title or audio_path.stem.replace("_", " ").replace("-", " ").title(),
    }
    if args.language:
        metadata["language_hint"] = args.language

    result = create_session_result(
        job_id=job_id,
        analysis_mode=args.analysis_mode,
        original_path=audio_path,
        options=ProcessSessionOptions(metadata=metadata),
    )
    session_url = f"{args.dashboard_url.rstrip('/')}/sessions/{job_id}"
    print(f"Analyzed {audio_path.name} into session {job_id}")
    print(f"Bundle saved at runs/{job_id}/bundle.json")
    print(f"Open session: {session_url}")
    if not result.transcript.strip():
        print("Transcript is currently empty for this run. Open the session to inspect readiness and degraded-mode caveats.")
    _open(session_url, args.open)
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    load_local_env()
    bundles = import_demo_pack()
    print(f"Imported {len(bundles)} demo sessions.")
    print(f"Open workspace: {args.dashboard_url.rstrip('/')}")
    _open(args.dashboard_url.rstrip("/"), args.open)
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    load_local_env()
    import uvicorn

    uvicorn.run("spectrum_api.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "demo":
        return _cmd_demo(args)
    if args.command == "serve":
        return _cmd_serve(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
