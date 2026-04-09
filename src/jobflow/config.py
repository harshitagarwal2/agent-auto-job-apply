from __future__ import annotations

import importlib
from pathlib import Path

try:  # pragma: no cover - editor/runtime compatibility fallback
    tomllib = importlib.import_module("tomllib")
except ModuleNotFoundError:  # pragma: no cover
    tomllib = importlib.import_module("tomli")

from jobflow.domain import AppConfig


DEFAULT_CONFIG_PATH = Path("jobflow.toml")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "jobflow.example.toml"

_FALLBACK_EXAMPLE_CONFIG = """[database]
path = ".local/jobflow.sqlite3"

[profile]
role_keywords = ["software engineer", "product manager", "program manager", "business analyst"]
allowed_countries = ["US", "USA", "United States"]
preferred_locations = ["Remote", "United States", "USA"]

[apply]
allow_live_submit = false
default_source_tag = "jobflow-local"

[[sources]]
name = "example-greenhouse"
family = "greenhouse"
enabled = false
company = "Example Co"
board_token = "example"

  [sources.policy]
  discovery_enabled = true
  apply_mode = "dry_run_only"
  allow_live_apply = false
"""


def _load_example_config() -> str:
    if EXAMPLE_CONFIG_PATH.exists():
        return EXAMPLE_CONFIG_PATH.read_text()
    return _FALLBACK_EXAMPLE_CONFIG


EXAMPLE_CONFIG = _load_example_config()


def load_config(
    path: Path | None = None, *, allow_missing: bool = True
) -> tuple[AppConfig, Path]:
    config_path = (path or DEFAULT_CONFIG_PATH).expanduser()
    if not config_path.exists():
        if allow_missing:
            return AppConfig(), config_path.parent.resolve()
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    return AppConfig.model_validate(raw), config_path.parent.resolve()
