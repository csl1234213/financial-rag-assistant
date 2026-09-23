"""Deterministic semantic guard for retrieved evidence.

Structural citation checks (source/chunk/page existence) are not enough for a
financial answer.  This gate applies explicit company, period, and metric
constraints before generation.  It deliberately keeps a marked fallback when
all candidates fail so the API can report insufficient evidence honestly.
"""

from __future__ import annotations

import hashlib
import re

from agent.planning.entity_extractor import extract_companies
from agent.reasoning_models import Evidence
from core.financial_grounding import (
    any_equivalent,
    derived_growth,
    extract_normalized_numbers,
)
from core.growth_driver_evidence import (
    has_growth_driver_evidence,
    is_growth_driver_question,
)
from retrieval.periods import matches_filter, query_filters


def _authority_deduplicate(items: list[Evidence]) -> list[Evidence]:
    """Collapse byte-equivalent evidence while preferring public filings.

    A tenant may upload the same filing that is already available in the
    public corpus.  Keeping both records gives the model duplicate, sometimes
    conflicting citation identities even though the underlying text is the
    same.  This is a presentation/retrieval decision only: the tenant record
    remains stored and is retained whenever no equivalent public record exists.
    """

    def company(item: Evidence) -> str:
        return str(item.company or item.metadata.get("company", "")).casefold()

    def authority(item: Evidence) -> int:
        value = str(item.metadata.get("source_authority", "")).casefold()
        if not value:
            value = "public_filing" if item.metadata.get("tenant_id") == 0 else "tenant_upload"
        return {"public_filing": 2, "tenant_upload": 1}.get(value, 0)

    def document_fingerprint(item: Evidence) -> str | None:
        value = str(item.metadata.get("content_sha256", "")).strip().casefold()
        if re.fullmatch(r"[0-9a-f]{64}", value):
            return value
        # Older audit/index records do not expose content_sha256 in metadata,
        # but the stable public_/tenant_<id>_<sha> chunk id still carries it.
        match = re.search(r"(?:public|tenant(?:_\d+)?)_([0-9a-f]{64})(?:_|$)",
                          str(item.metadata.get("chunk_id", "")), re.I)
        return match.group(1).casefold() if match else None

    public_documents = {
        (company(item), fingerprint)
        for item in items
        if authority(item) >= 2
        for fingerprint in [document_fingerprint(item)]
        if fingerprint
    }

    def key(item: Evidence) -> tuple[str, str]:
        normalized = re.sub(r"\s+", " ", str(item.content or "")).strip().casefold()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return company(item), digest

    chosen: dict[tuple[str, str], Evidence] = {}
    order: list[tuple[str, str]] = []
    for item in items:
        fingerprint = document_fingerprint(item)
        if authority(item) < 2 and fingerprint and (company(item), fingerprint) in public_documents:
            # A private upload is the same complete filing as an indexed
            # public document.  Prefer the public document for every chunk,
            # not only chunks whose extracted text happens to be byte-equal.
            continue
        identity = key(item)
        previous = chosen.get(identity)
        if previous is None:
            chosen[identity] = item
            order.append(identity)
            continue
        if authority(item) > authority(previous):
            metadata = dict(item.metadata)
            metadata["source_authority_selection"] = "public_filing_preferred"
            chosen[identity] = Evidence(
                content=item.content,
                source=item.source,
                company=item.company,
                confidence=item.confidence,
                metadata=metadata,
            )
    return [chosen[identity] for identity in order]


def filter_evidence_for_query(question: str, evidence: list[Evidence]) -> list[Evidence]:
    """Return semantically compatible evidence, or an explicit fallback."""

    # A flattened table with several periods and financial rows but no
    # verified cell-to-header mapping is retained for parser diagnostics only.
    # It must not enter the generation context, including through the
    # unverified fallback path.
    evidence = [
        item
        for item in evidence
        if str(item.metadata.get("content_type", "")).casefold() != "unverified_table"
    ]
    if not evidence:
        return []

    expected_companies = {name.casefold() for name in extract_companies(question)}
    filters = query_filters(question)
    growth_driver_request = is_growth_driver_question(question)
    accepted: list[Evidence] = []
    rejected: list[Evidence] = []

    for item in evidence:
        metadata = dict(item.metadata)
        company = str(item.company or metadata.get("company", "")).casefold()
        if expected_companies and company not in expected_companies:
            rejected.append(item)
            continue
        failed_filters = {
            key for key, value in filters.items()
            if not matches_filter(item.content, metadata, key, value)
        }
        # Causal questions need narrative evidence that often has no financial
        # metric label (e.g. management's AI-factory commentary). Preserve a
        # passage explicitly recognized as a growth driver when only the
        # metric filter fails; issuer and period constraints remain binding.
        if (
            growth_driver_request
            and has_growth_driver_evidence(item.content)
        ):
            failed_filters.discard("metric")
        if failed_filters:
            rejected.append(item)
            continue
        metadata.update(
            {
                "semantic_support": "supported",
                "semantic_support_reason": "company/period/metric constraints matched",
            }
        )
        accepted.append(
            Evidence(
                content=item.content,
                source=item.source,
                company=item.company,
                confidence=item.confidence,
                metadata=metadata,
            )
        )

    if accepted:
        return _authority_deduplicate(accepted)
    if not rejected:
        return []

    # Preserve the strongest retrieved record but label it explicitly.  This
    # prevents a silent empty-citation response when a parser missed a filing
    # period or a source contains narrative text without a table header.
    fallback = max(rejected, key=lambda item: item.confidence)
    metadata = dict(fallback.metadata)
    metadata.update(
        {
            "semantic_support": "unverified",
            "semantic_support_reason": "no candidate matched all explicit query constraints",
        }
    )
    return _authority_deduplicate([
        Evidence(
            content=fallback.content,
            source=fallback.source,
            company=fallback.company,
            confidence=fallback.confidence,
            metadata=metadata,
        )
    ])


def validate_answer_evidence(
    question: str,
    answer: str,
    evidence: list[Evidence],
) -> list[Evidence]:
    """Apply a deterministic claim-to-evidence numeric support check."""

    candidates = filter_evidence_for_query(question, evidence)
    answer_numbers = extract_normalized_numbers(answer)
    if not answer_numbers:
        return candidates

    supported: list[Evidence] = []
    for item in candidates:
        evidence_numbers = extract_normalized_numbers(item.content)
        direct_support = any_equivalent(answer_numbers, evidence_numbers)
        derived_support = False
        if any(
            marker in answer.casefold()
            for marker in ("growth", "increase", "decrease", "yoy", "qoq", "同比", "环比", "增长")
        ) and len(evidence_numbers) >= 2:
            derived = derived_growth(evidence_numbers[0], evidence_numbers[1])
            derived_support = bool(
                derived
                and any_equivalent(answer_numbers, [derived])
            )
        if direct_support or derived_support:
            metadata = dict(item.metadata)
            metadata.update(
                {
                    "claim_support": "supported",
                    "claim_support_reason": "answer numeric claim appears in evidence",
                }
            )
            supported.append(
                Evidence(
                    content=item.content,
                    source=item.source,
                    company=item.company,
                    confidence=item.confidence,
                    metadata=metadata,
                )
            )

    if supported:
        return supported
    fallback = candidates[0] if candidates else None
    if fallback is None:
        return []
    metadata = dict(fallback.metadata)
    metadata.update(
        {
            "claim_support": "unverified",
            "claim_support_reason": "numeric claims were not found in retrieved evidence",
        }
    )
    return [
        Evidence(
            content=fallback.content,
            source=fallback.source,
            company=fallback.company,
            confidence=fallback.confidence,
            metadata=metadata,
        )
    ]
