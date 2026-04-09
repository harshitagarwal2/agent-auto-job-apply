#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

jobflow_bin="$(resolve_jobflow)"
target_path="$ROOT_DIR/jobflow.toml"

if [[ -f "$target_path" && "${1:-}" != "--force" ]]; then
  fail "Config already exists at $target_path. Re-run with --force to overwrite it."
fi

if [[ -f "$target_path" && "${1:-}" == "--force" ]]; then
  "$jobflow_bin" init-config --path "$target_path" --force
  exit 0
fi

if [[ $# -gt 0 ]]; then
  fail "init-config.sh accepts no arguments except optional --force"
fi

"$jobflow_bin" init-config --path "$target_path"
