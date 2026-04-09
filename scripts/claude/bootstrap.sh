#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON:-}"

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

select_python() {
  if [[ -n "$PYTHON_BIN" ]]; then
    printf '%s\n' "$PYTHON_BIN"
    return
  fi

  local candidate
  for candidate in python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
      then
        printf '%s\n' "$candidate"
        return
      fi
    fi
  done

  fail "Could not find Python 3.12+. Set PYTHON=python3.12 or install Python 3.12+."
}

PYTHON_BIN="$(select_python)"

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit("error: Python 3.12+ is required for this repository.")
PY

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$ROOT_DIR/.venv"
fi

"$ROOT_DIR/.venv/bin/python" -m pip install -e "${ROOT_DIR}[dev]"

if [[ ! -f "$ROOT_DIR/jobflow.toml" ]]; then
  "$ROOT_DIR/scripts/claude/init-config.sh"
fi

cat <<'EOF'
Bootstrap complete.

Next steps:
1. Edit jobflow.toml and enable the sources you want.
2. For a deterministic smoke test, run:
   JOBFLOW_CONFIG=jobflow.smoke.toml ./scripts/claude/sync.sh
   JOBFLOW_CONFIG=jobflow.smoke.toml ./scripts/claude/list.sh --limit 10
3. For your real workflow, run:
   ./scripts/claude/sync.sh
   ./scripts/claude/list.sh --limit 25
   ./scripts/claude/review.sh
EOF
