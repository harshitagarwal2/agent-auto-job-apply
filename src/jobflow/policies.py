from __future__ import annotations

from jobflow.domain import (
    ApplyConfig,
    ApplyMode,
    ResolvedSourcePolicy,
    SourceConfig,
    SourceFamily,
)


class PolicyViolation(RuntimeError):
    """Raised when a source family or config blocks application behavior."""


APPLY_CAPABLE_FAMILIES = {SourceFamily.GREENHOUSE, SourceFamily.LEVER}


def resolve_policy(
    source: SourceConfig, apply_config: ApplyConfig
) -> ResolvedSourcePolicy:
    apply_capable_family = source.family in APPLY_CAPABLE_FAMILIES
    effective_apply_mode = source.policy.apply_mode or default_apply_mode_for_family(
        source.family
    )
    dry_run_apply_allowed = apply_capable_family and effective_apply_mode in {
        ApplyMode.DRY_RUN_ONLY,
        ApplyMode.LIVE_OPT_IN,
    }
    live_apply_allowed = (
        apply_capable_family
        and effective_apply_mode == ApplyMode.LIVE_OPT_IN
        and source.policy.allow_live_apply
        and apply_config.allow_live_submit
    )

    return ResolvedSourcePolicy(
        discovery_enabled=source.enabled and source.policy.discovery_enabled,
        dry_run_apply_allowed=dry_run_apply_allowed,
        live_apply_allowed=live_apply_allowed,
        apply_capable_family=apply_capable_family,
        effective_apply_mode=effective_apply_mode,
    )


def default_apply_mode_for_family(family: SourceFamily) -> ApplyMode:
    if family in APPLY_CAPABLE_FAMILIES:
        return ApplyMode.DRY_RUN_ONLY
    return ApplyMode.DISABLED


def ensure_can_apply(
    source: SourceConfig, apply_config: ApplyConfig, *, dry_run: bool
) -> None:
    resolved = resolve_policy(source, apply_config)
    if not resolved.apply_capable_family:
        raise PolicyViolation(
            f"{source.family.value} is discovery-only/manual in v1 and cannot be submitted through this workflow"
        )

    if dry_run and not resolved.dry_run_apply_allowed:
        raise PolicyViolation(f"dry-run apply is disabled for source '{source.name}'")

    if not dry_run and not resolved.live_apply_allowed:
        raise PolicyViolation(
            "live apply is disabled unless global config, source policy, and provider credentials are all enabled"
        )
