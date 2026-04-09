#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

args=("$@")
if [[ ${#args[@]} -eq 0 ]]; then
  args=(--limit 25)
fi

run_jobflow list "${args[@]}"
