"""Evidence-bounded AI reasoning contracts.

This module contains no model dependency. It builds deterministic evidence
packets, validates model output, calibrates structural support and converts
validated claims into derived investigative findings.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

from pensieve_timeline.case_engine import InvestigativeFinding


PACKET_SCHEMA_VERSION = "2.0"
REPORT_SCHEMA_VERSION = "2.0"

CLAIM_LEVELS = {"observation", "inference", "hypothesis"}
REPORT_KEYS = {"summary", "claims", "uncertainties", "next_questions"}
CLAIM_KEYS = {
    "level",
    "statement",
    "evidence_event_ids",
    "rationale",
    "alternatives",
    "reported_confidence",
}

LEVEL_FACTORS = {
    "observation": 1.00,
    "inference": 0.80,
    "hypothesis": 0.65,
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _bounded_text(value: Any, *, field: str, max_chars: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must not be empty")
    if len(text) > max_chars:
        raise ValueError(f"{field} exceeds {max_chars} characters")
    return text


def _event_snapshot(event, mentions, max_message_chars: int) -> dict[str, Any]:
    row = {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
        "source": event.source,
        "artifact_type": event.artifact_type,
        "event_type": event.event_type,
        "host": event.host,
        "user": event.user,
        "provider": event.provider,
        "event_code": event.event_code,
        "pid": event.pid,
        "message": event.message[:max_message_chars],
        "risk_score": event.risk_score,
        "tags": list(event.tags),
        "provenance": {
            "record_locator": event.record_locator,
            "parser": event.parser,
            "parser_version": event.parser_version,
            "time_assumption": event.time_assumption,
        },
        "entities": [
            {
                "mention_id": mention.mention_id,
                "label": mention.label,
                "text": mention.text,
                "normalized_value": mention.normalized_value,
                "confidence_kind": mention.confidence_kind,
                "extractor": mention.extractor,
                "corroborated_by": list(mention.corroborated_by),
                "evidence_hash": mention.evidence_hash,
            }
            for mention in sorted(
                mentions,
                key=lambda item: (
                    item.source_field,
                    item.start,
                    item.end,
                    item.label,
                    item.mention_id,
                ),
            )
        ],
    }
    row["event_digest"] = _sha256(row)
    return row


def build_evidence_packet_v2(
    events,
    mentions=(),
    *,
    max_events: int = 40,
    max_message_chars: int = 700,
) -> dict[str, Any]:
    """Build a deterministic read-only packet for local AI reasoning.

    Raw parser data and local source paths are intentionally excluded.
    Events are selected chronologically to avoid silently biasing the packet
    toward a risk score or an ML ranking.
    """

    if max_events < 1:
        raise ValueError("max_events must be >= 1")
    if max_message_chars < 80:
        raise ValueError("max_message_chars must be >= 80")

    event_items = sorted(
        list(events),
        key=lambda event: (event.timestamp, event.event_id),
    )
    mention_items = list(mentions)

    grouped: dict[str, list[Any]] = {}
    for mention in mention_items:
        grouped.setdefault(mention.event_id, []).append(mention)

    selected = event_items[:max_events]
    event_rows = [
        _event_snapshot(
            event,
            grouped.get(event.event_id, []),
            max_message_chars,
        )
        for event in selected
    ]

    body = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "policy": {
            "scope": "evidence-bounded",
            "read_only_evidence": True,
            "raw_excluded": True,
            "source_path_excluded": True,
            "external_enrichment": False,
            "required_citation": "event_id",
            "correlation_is_not_causation": True,
            "normalized_entity_is_not_verified_identity": True,
            "model_output_is_derived_analysis": True,
        },
        "selection": {
            "strategy": "chronological_first",
            "input_event_count": len(event_items),
            "included_event_count": len(event_rows),
            "max_events": max_events,
            "max_message_chars": max_message_chars,
        },
        "events": event_rows,
    }

    digest = _sha256(body)
    return {
        "packet_id": f"ep2:{digest[:24]}",
        "packet_sha256": digest,
        **body,
    }


def verify_evidence_packet_v2(packet: dict[str, Any]) -> str:
    """Validate packet integrity and return its canonical SHA-256."""

    if not isinstance(packet, dict):
        raise ValueError("evidence packet must be an object")
    if packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise ValueError("unsupported evidence packet schema_version")

    packet_id = packet.get("packet_id")
    packet_sha256 = packet.get("packet_sha256")
    if not isinstance(packet_id, str) or not packet_id.startswith("ep2:"):
        raise ValueError("invalid packet_id")
    if not isinstance(packet_sha256, str) or len(packet_sha256) != 64:
        raise ValueError("invalid packet_sha256")

    events = packet.get("events")
    if not isinstance(events, list):
        raise ValueError("packet.events must be a list")

    seen_ids = set()
    for row in events:
        if not isinstance(row, dict):
            raise ValueError("each packet event must be an object")
        event_id = row.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("packet event missing event_id")
        if event_id in seen_ids:
            raise ValueError(f"duplicate packet event_id: {event_id}")
        seen_ids.add(event_id)

        expected_event_digest = row.get("event_digest")
        if not isinstance(expected_event_digest, str):
            raise ValueError(f"event {event_id} missing event_digest")
        event_body = dict(row)
        event_body.pop("event_digest", None)
        actual_event_digest = _sha256(event_body)
        if actual_event_digest != expected_event_digest:
            raise ValueError(f"event digest mismatch: {event_id}")

        if "raw" in row or "source_path" in row:
            raise ValueError(f"forbidden evidence field in packet event: {event_id}")

    body = dict(packet)
    body.pop("packet_id", None)
    body.pop("packet_sha256", None)
    actual = _sha256(body)
    if actual != packet_sha256:
        raise ValueError("evidence packet digest mismatch")
    if packet_id != f"ep2:{actual[:24]}":
        raise ValueError("packet_id does not match packet digest")
    return actual


def snapshot_packet(packet: dict[str, Any]) -> str:
    """Return a whole-object fingerprint used to detect in-process mutation."""

    verify_evidence_packet_v2(packet)
    return _sha256(packet)


def _support_calibration(
    level: str,
    evidence_event_ids: list[str],
    event_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    unique_ids = list(dict.fromkeys(evidence_event_ids))
    source_families = {
        (
            event_index[event_id].get("source"),
            event_index[event_id].get("artifact_type"),
        )
        for event_id in unique_ids
    }

    evidence_count = len(unique_ids)
    source_diversity = len(source_families)
    structural = (
        0.55
        + 0.12 * min(max(evidence_count - 1, 0), 3)
        + 0.08 * min(max(source_diversity - 1, 0), 2)
    )
    score = min(0.95, structural) * LEVEL_FACTORS[level]
    score = round(max(0.0, min(0.95, score)), 3)

    if score < 0.45:
        label = "low"
    elif score < 0.70:
        label = "moderate"
    else:
        label = "high"

    return {
        "score": score,
        "label": label,
        "not_probability": True,
        "basis": {
            "evidence_event_count": evidence_count,
            "source_diversity": source_diversity,
            "claim_level_factor": LEVEL_FACTORS[level],
            "model_self_confidence_used": False,
        },
    }


def _claim_id(claim: dict[str, Any]) -> str:
    return "claim:" + _sha256(
        {
            "level": claim["level"],
            "statement": claim["statement"],
            "evidence_event_ids": sorted(claim["evidence_event_ids"]),
        }
    )[:20]


def validate_reasoning_payload(
    payload: dict[str, Any],
    packet: dict[str, Any],
    *,
    model_name: str = "unknown",
) -> dict[str, Any]:
    """Fail closed when a model emits unsupported claims or invalid citations."""

    verify_evidence_packet_v2(packet)

    if not isinstance(payload, dict):
        raise ValueError("reasoning output must be a JSON object")

    unknown = set(payload) - REPORT_KEYS
    missing = REPORT_KEYS - set(payload)
    if unknown:
        raise ValueError(
            "reasoning output contains forbidden top-level keys: "
            + ", ".join(sorted(unknown))
        )
    if missing:
        raise ValueError(
            "reasoning output missing required keys: "
            + ", ".join(sorted(missing))
        )

    summary = _bounded_text(
        payload["summary"],
        field="summary",
        max_chars=5000,
    )

    claims = payload["claims"]
    if not isinstance(claims, list):
        raise ValueError("claims must be a list")
    if len(claims) > 100:
        raise ValueError("claims exceeds maximum length of 100")

    event_index = {
        row["event_id"]: row
        for row in packet["events"]
    }
    allowed_event_ids = set(event_index)

    validated_claims = []
    for index, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            raise ValueError(f"claim {index} must be an object")

        unknown_claim_keys = set(claim) - CLAIM_KEYS
        required = {
            "level",
            "statement",
            "evidence_event_ids",
            "rationale",
            "alternatives",
        }
        missing_claim_keys = required - set(claim)
        if unknown_claim_keys:
            raise ValueError(
                f"claim {index} contains forbidden keys: "
                + ", ".join(sorted(unknown_claim_keys))
            )
        if missing_claim_keys:
            raise ValueError(
                f"claim {index} missing keys: "
                + ", ".join(sorted(missing_claim_keys))
            )

        level = str(claim["level"]).strip().casefold()
        if level not in CLAIM_LEVELS:
            raise ValueError(f"claim {index} has invalid level: {level}")

        statement = _bounded_text(
            claim["statement"],
            field=f"claim {index} statement",
            max_chars=4000,
        )
        rationale = _bounded_text(
            claim["rationale"],
            field=f"claim {index} rationale",
            max_chars=6000,
        )

        citations = claim["evidence_event_ids"]
        if (
            not isinstance(citations, list)
            or not citations
            or not all(isinstance(item, str) and item for item in citations)
        ):
            raise ValueError(
                f"claim {index} must cite one or more evidence_event_ids"
            )
        citations = list(dict.fromkeys(citations))
        invalid_ids = sorted(set(citations) - allowed_event_ids)
        if invalid_ids:
            raise ValueError(
                f"claim {index} cites event_ids outside the packet: "
                + ", ".join(invalid_ids)
            )

        alternatives = claim["alternatives"]
        if not isinstance(alternatives, list):
            raise ValueError(f"claim {index} alternatives must be a list")
        if len(alternatives) > 10:
            raise ValueError(f"claim {index} has more than 10 alternatives")

        clean_alternatives = [
            _bounded_text(
                alternative,
                field=f"claim {index} alternative",
                max_chars=2000,
            )
            for alternative in alternatives
        ]

        if level == "observation" and clean_alternatives:
            raise ValueError(
                f"claim {index}: observation must not contain alternatives"
            )
        if level == "hypothesis" and not clean_alternatives:
            raise ValueError(
                f"claim {index}: hypothesis requires at least one alternative"
            )

        reported = claim.get("reported_confidence")
        if reported is not None:
            if not isinstance(reported, (int, float)) or isinstance(reported, bool):
                raise ValueError(
                    f"claim {index} reported_confidence must be numeric"
                )
            reported = float(reported)
            if not 0.0 <= reported <= 1.0:
                raise ValueError(
                    f"claim {index} reported_confidence must be between 0 and 1"
                )

        normalized_claim = {
            "level": level,
            "statement": statement,
            "evidence_event_ids": citations,
            "rationale": rationale,
            "alternatives": clean_alternatives,
            "reported_confidence": reported,
        }
        normalized_claim["claim_id"] = _claim_id(normalized_claim)
        normalized_claim["calibrated_support"] = _support_calibration(
            level,
            citations,
            event_index,
        )
        validated_claims.append(normalized_claim)

    def clean_list(name: str, max_items: int = 50) -> list[str]:
        value = payload[name]
        if not isinstance(value, list):
            raise ValueError(f"{name} must be a list")
        if len(value) > max_items:
            raise ValueError(f"{name} exceeds maximum length of {max_items}")
        return [
            _bounded_text(item, field=name, max_chars=2000)
            for item in value
        ]

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "packet_id": packet["packet_id"],
        "packet_sha256": packet["packet_sha256"],
        "model": model_name,
        "summary": summary,
        "claims": validated_claims,
        "uncertainties": clean_list("uncertainties"),
        "next_questions": clean_list("next_questions"),
        "validation": {
            "valid": True,
            "claim_count": len(validated_claims),
            "all_claims_cited": True,
            "citation_scope": "packet_event_ids_only",
            "model_output_can_mutate_evidence": False,
            "confidence_semantics": (
                "calibrated_support is a transparent structural support score, "
                "not a probability that a claim is true"
            ),
        },
    }
    report["report_sha256"] = _sha256(report)
    return report


def report_to_findings(report: dict[str, Any], events) -> list[InvestigativeFinding]:
    """Convert only a previously validated report into derived case findings."""

    if not isinstance(report, dict) or not report.get("validation", {}).get("valid"):
        raise ValueError("reasoning report is not validated")

    findings = []
    for claim in report.get("claims", []):
        support = claim.get("calibrated_support", {})
        finding = InvestigativeFinding(
            level=claim["level"],
            statement=claim["statement"],
            evidence_event_ids=list(claim["evidence_event_ids"]),
            rationale=claim["rationale"],
            alternatives=list(claim["alternatives"]),
            confidence=float(support.get("score", 0.0)),
            status="ai_proposed",
        )
        finding.validate(events)
        findings.append(finding)
    return findings


def immutable_packet_copy(packet: dict[str, Any]) -> dict[str, Any]:
    """Return a verified deep copy for provider boundaries."""

    verify_evidence_packet_v2(packet)
    return deepcopy(packet)
