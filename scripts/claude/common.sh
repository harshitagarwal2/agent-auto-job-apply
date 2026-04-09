#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONFIG_PATH="${JOBFLOW_CONFIG:-$ROOT_DIR/jobflow.toml}"

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_config() {
  if [[ ! -f "$CONFIG_PATH" ]]; then
    fail "Missing config at $CONFIG_PATH. Run './scripts/claude/bootstrap.sh' on first setup, or './scripts/claude/init-config.sh' if the environment already exists."
  fi
}

require_managed_config_flag() {
  for arg in "$@"; do
    if [[ "$arg" == "--config" || "$arg" == --config=* ]]; then
      fail "Wrapper scripts manage --config automatically. Use JOBFLOW_CONFIG to override the default path."
    fi
  done
}

resolve_jobflow() {
  if [[ -x "$ROOT_DIR/.venv/bin/jobflow" ]]; then
    printf '%s\n' "$ROOT_DIR/.venv/bin/jobflow"
    return
  fi
  fail "Could not find the repo-local jobflow CLI at $ROOT_DIR/.venv/bin/jobflow. Run './scripts/claude/bootstrap.sh' first."
}

run_jobflow() {
  require_config
  require_managed_config_flag "$@"
  local jobflow_bin
  jobflow_bin="$(resolve_jobflow)"
  "$jobflow_bin" "$@" --config "$CONFIG_PATH"
}
