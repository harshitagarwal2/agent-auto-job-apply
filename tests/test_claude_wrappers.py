from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_wrapper_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts/claude").mkdir(parents=True)
    (root / ".venv/bin").mkdir(parents=True)

    for relative in [
        "scripts/claude/common.sh",
        "scripts/claude/bootstrap.sh",
        "scripts/claude/init-config.sh",
        "scripts/claude/sync.sh",
        "scripts/claude/list.sh",
        "scripts/claude/review.sh",
        "scripts/claude/apply-dry-run.sh",
        "scripts/claude/apply-live.sh",
    ]:
        source = REPO_ROOT / relative
        target = root / relative
        target.write_text(source.read_text())
        target.chmod(source.stat().st_mode)

    fake_jobflow = root / ".venv/bin/jobflow"
    fake_jobflow.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"\n'
        'LOG="$ROOT_DIR/jobflow_invocations.log"\n'
        'printf \'%s\\n\' "$*" >> "$LOG"\n'
        'if [[ "${1:-}" == "init-config" ]]; then\n'
        "  shift\n"
        '  target=""\n'
        "  while [[ $# -gt 0 ]]; do\n"
        '    case "$1" in\n'
        '      --path) target="$2"; shift 2 ;;\n'
        "      --force) shift ;;\n"
        "      *) shift ;;\n"
        "    esac\n"
        "  done\n"
        '  printf \'[database]\\npath = ".local/jobflow.sqlite3"\\n\' > "${target:?}"\n'
        "  exit 0\n"
        "fi\n"
    )
    fake_jobflow.chmod(fake_jobflow.stat().st_mode | stat.S_IXUSR)
    return root


def _run(repo_root: Path, *args: str, env: dict[str, str] | None = None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        args,
        cwd=repo_root,
        text=True,
        capture_output=True,
        env=merged_env,
        check=False,
    )


def test_sync_wrapper_fails_closed_without_config(tmp_path: Path) -> None:
    repo_root = _copy_wrapper_tree(tmp_path)

    result = _run(repo_root, "./scripts/claude/sync.sh")

    assert result.returncode == 1
    assert "Missing config" in result.stderr
    assert "bootstrap.sh" in result.stderr


def test_list_wrapper_rejects_config_override(tmp_path: Path) -> None:
    repo_root = _copy_wrapper_tree(tmp_path)
    (repo_root / "jobflow.toml").write_text(
        '[database]\npath = ".local/jobflow.sqlite3"\n'
    )

    result = _run(repo_root, "./scripts/claude/list.sh", "--config=foo")

    assert result.returncode == 1
    assert "Wrapper scripts manage --config automatically" in result.stderr


def test_sync_wrapper_uses_jobflow_config_override(tmp_path: Path) -> None:
    repo_root = _copy_wrapper_tree(tmp_path)
    custom_config = repo_root / "custom.toml"
    custom_config.write_text('[database]\npath = ".local/jobflow.sqlite3"\n')

    result = _run(
        repo_root,
        "./scripts/claude/sync.sh",
        env={"JOBFLOW_CONFIG": str(custom_config)},
    )

    assert result.returncode == 0
    assert "sync --config" in (repo_root / "jobflow_invocations.log").read_text()
    assert str(custom_config) in (repo_root / "jobflow_invocations.log").read_text()


def test_init_config_wrapper_creates_jobflow_toml(tmp_path: Path) -> None:
    repo_root = _copy_wrapper_tree(tmp_path)

    result = _run(repo_root, "./scripts/claude/init-config.sh")

    assert result.returncode == 0
    assert (repo_root / "jobflow.toml").exists()
    assert "init-config --path" in (repo_root / "jobflow_invocations.log").read_text()


def test_bootstrap_wrapper_sets_up_repo_and_creates_config(tmp_path: Path) -> None:
    repo_root = _copy_wrapper_tree(tmp_path)
    template_venv = repo_root / ".venv-template"
    (repo_root / ".venv").rename(template_venv)

    fake_python = repo_root / "fake-python3.12"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ "${1:-}" == "-" ]]; then\n'
        "  cat >/dev/null\n"
        "  exit 0\n"
        "fi\n"
        'if [[ "${1:-}" == "-m" && "${2:-}" == "venv" ]]; then\n'
        '  target="${3:?}"\n'
        '  mkdir -p "$target/bin"\n'
        '  cp "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/.venv-template/bin/jobflow" "$target/bin/jobflow"\n'
        "  cat > \"$target/bin/python\" <<'EOF'\n"
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "exit 0\n"
        "EOF\n"
        'chmod +x "$target/bin/python" "$target/bin/jobflow"\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "${1:-}" == "-m" && "${2:-}" == "pip" ]]; then\n'
        "  exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

    result = _run(
        repo_root,
        "./scripts/claude/bootstrap.sh",
        env={"PYTHON": str(fake_python)},
    )

    assert result.returncode == 0, result.stderr
    assert (repo_root / ".venv/bin/jobflow").exists()
    assert (repo_root / "jobflow.toml").exists()
    assert "Bootstrap complete." in result.stdout


def test_apply_live_wrapper_blocks_mismatched_confirmation_before_invocation(
    tmp_path: Path,
) -> None:
    repo_root = _copy_wrapper_tree(tmp_path)
    (repo_root / "jobflow.toml").write_text(
        '[database]\npath = ".local/jobflow.sqlite3"\n'
    )

    result = _run(
        repo_root,
        "./scripts/claude/apply-live.sh",
        "--job-id",
        "job-1",
        "--confirm-job-id",
        "job-2",
    )

    assert result.returncode == 1
    assert "must exactly match" in result.stderr
    assert not (repo_root / "jobflow_invocations.log").exists()
