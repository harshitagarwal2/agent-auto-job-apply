from __future__ import annotations

from datetime import datetime, timezone

from jobflow.domain import CanonicalJob, RankedJob, SearchProfile, WorkplaceType


def rank_job(job: CanonicalJob, profile: SearchProfile) -> RankedJob:
    title = job.title.lower()
    location = (job.location_text or "").lower()
    description = (job.description or "").lower()
    score = 0.0
    reasons: list[str] = []

    for keyword in profile.role_keywords:
        if keyword.lower() in title:
            score += 40
            reasons.append(f"title matches '{keyword}'")

    for keyword in profile.exclude_keywords:
        if keyword.lower() in title or keyword.lower() in description:
            score -= 30
            reasons.append(f"penalized by excluded keyword '{keyword}'")

    if _looks_us(job.location_country, location, profile.allowed_countries):
        score += 15
        reasons.append("US-friendly location")
    else:
        score -= 20
        reasons.append("location not clearly US-focused")

    if job.workplace_type == WorkplaceType.REMOTE or any(
        preferred.lower() in location for preferred in profile.preferred_locations
    ):
        score += 10
        reasons.append("preferred location/remote signal")

    if job.posted_at is not None:
        age_days = (datetime.now(timezone.utc) - job.posted_at).days
        if age_days <= 7:
            score += 10
            reasons.append("posted within 7 days")
        elif age_days <= 30:
            score += 5
            reasons.append("posted within 30 days")

    if not reasons:
        reasons.append("baseline match")

    return RankedJob(score=score, reasons=reasons)


def _looks_us(
    location_country: str | None,
    location_text: str,
    allowed_countries: list[str],
) -> bool:
    country = (location_country or "").lower()
    if any(country == allowed.lower() for allowed in allowed_countries):
        return True

    return any(token.lower() in location_text for token in allowed_countries)
