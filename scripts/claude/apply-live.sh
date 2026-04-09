#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

job_id=""
confirm_job_id=""
args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --job-id)
      [[ $# -ge 2 ]] || fail "--job-id requires a value"
      job_id="$2"
      args+=("$1" "$2")
      shift 2
      ;;
    --confirm-job-id)
      [[ $# -ge 2 ]] || fail "--confirm-job-id requires a value"
      confirm_job_id="$2"
      args+=("$1" "$2")
      shift 2
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

[[ -n "$job_id" ]] || fail "apply-live requires --job-id <job-id>"
[[ -n "$confirm_job_id" ]] || fail "apply-live requires --confirm-job-id <job-id>"
[[ "$job_id" == "$confirm_job_id" ]] || fail "--confirm-job-id must exactly match --job-id"

run_jobflow apply-live "${args[@]}"
