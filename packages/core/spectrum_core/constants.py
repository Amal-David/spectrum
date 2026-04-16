from pathlib import Path


SCHEMA_VERSION = "0.2.0"
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
RUNS_DIR = REPO_ROOT / "runs"
FIXTURES_DIR = REPO_ROOT / "fixtures"
DASHBOARD_DIR = REPO_ROOT / "packages" / "dashboard"
DEMO_PACK_PATH = REPO_ROOT / "voice_analytics_demo_pack.zip"
