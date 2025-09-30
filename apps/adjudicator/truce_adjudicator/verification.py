"""Verification helpers including deterministic cache management."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from threading import Lock
from typing import Dict, Iterable, List, Optional, Sequence
from uuid import UUID

from .models import Claim, Evidence, TimeWindow, VerificationRecord, VerdictType

DEFAULT_PROVIDERS: List[str] = [
    "gpt-5",
    "claude-sonnet-4-20250514",
]

_cache: Dict[str, VerificationRecord] = {}
_cache_lock = Lock()


def reset_cache() -> None:
    """Clear the in-memory verification cache (primarily for tests)."""
    with _cache_lock:
        _cache.clear()


def normalize_claim_text(text: str) -> str:
    """Normalize claim text for hashing."""
    return " ".join(text.lower().split())


def compute_sources_hash(evidence: Sequence[Evidence]) -> str:
    """Compute deterministic SHA256 hash for a set of evidence."""
    if not evidence:
        return "no-sources"

    digest = sha256()
    for item in sorted(evidence, key=lambda ev: ev.id):
        published = item.published_at.isoformat() if item.published_at else ""
        record = "|".join(
            [
                str(item.id),
                item.url or "",
                item.publisher or "",
                item.snippet or "",
                published,
            ]
        )
        digest.update(record.encode("utf-8"))
    return digest.hexdigest()


def build_cache_key(
    claim_text: str,
    time_window: TimeWindow,
    providers: Sequence[str],
    sources_hash: str,
) -> str:
    """Construct deterministic cache key matching feature spec."""
    normalized_text = normalize_claim_text(claim_text)
    start = time_window.start.isoformat() if time_window.start else "null"
    end = time_window.end.isoformat() if time_window.end else "null"
    provider_fingerprint = "|".join(sorted(providers)) if providers else ""

    material = "|".join(
        [normalized_text, start, end, provider_fingerprint, sources_hash]
    )
    return sha256(material.encode("utf-8")).hexdigest()


def get_cached_verification(cache_key: str) -> Optional[VerificationRecord]:
    """Return cached verification record if present."""
    with _cache_lock:
        record = _cache.get(cache_key)
        return record.model_copy() if record else None


def store_verification(cache_key: str, record: VerificationRecord) -> None:
    """Persist verification record in cache."""
    with _cache_lock:
        _cache[cache_key] = record.model_copy()


def filter_evidence_by_time_window(
    evidence: Sequence[Evidence],
    start: Optional[datetime],
    end: Optional[datetime],
) -> List[Evidence]:
    """Filter evidence list according to provided time window."""
    if not start and not end:
        return list(evidence)

    filtered: List[Evidence] = []
    for item in evidence:
        published = item.published_at
        if published is None:
            filtered.append(item)
            continue

        if start and published < start:
            continue
        if end and published > end:
            continue

        filtered.append(item)
    return filtered


def _determine_verdict(claim: Claim) -> VerdictType:
    """Simple aggregation to derive verdict from model assessments."""
    if not claim.model_assessments:
        return VerdictType.UNCERTAIN

    support = sum(1 for assessment in claim.model_assessments if assessment.verdict == VerdictType.SUPPORTS)
    refute = sum(1 for assessment in claim.model_assessments if assessment.verdict == VerdictType.REFUTES)

    if support > refute:
        return VerdictType.SUPPORTS
    if refute > support:
        return VerdictType.REFUTES
    if support == refute and support > 0:
        return VerdictType.MIXED
    return VerdictType.UNCERTAIN


def create_verification_record(
    claim: Claim,
    claim_slug: str,
    evidence: Sequence[Evidence],
    providers: Sequence[str],
    time_window: TimeWindow,
    sources_hash: str,
) -> VerificationRecord:
    """Create a verification record instance for persistence and response reuse."""
    evidence_ids: List[UUID] = [item.id for item in evidence]

    return VerificationRecord(
        claim_slug=claim_slug,
        verdict=_determine_verdict(claim),
        providers=list(providers),
        evidence_ids=evidence_ids,
        sources_hash=sources_hash,
        time_window=time_window,
    )
