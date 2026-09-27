"""Evidence-first entity and event graph construction."""

from collections import defaultdict
import hashlib
from itertools import combinations


def _key(mention):
    return mention.label, mention.normalized_value


def _id(label, normalized_value):
    return "entity:" + hashlib.sha256(
        f"{label}\0{normalized_value}".encode()
    ).hexdigest()[:20]


def build_entity_graph(mentions):
    nodes = {}
    by_event = defaultdict(set)

    for mention in mentions:
        key = _key(mention)
        node = nodes.setdefault(
            key,
            {
                "id": _id(*key),
                "type": "entity",
                "label": mention.label,
                "value": mention.text,
                "normalized": mention.normalized_value,
                "mention_ids": [],
                "event_ids": [],
                "extractors": [],
                "max_confidence": 0.0,
            },
        )

        if mention.mention_id not in node["mention_ids"]:
            node["mention_ids"].append(mention.mention_id)
        if mention.event_id not in node["event_ids"]:
            node["event_ids"].append(mention.event_id)

        node["extractors"] = sorted(
            set(node["extractors"])
            | set(mention.corroborated_by)
            | {mention.extractor}
        )
        node["max_confidence"] = max(
            node["max_confidence"],
            mention.score,
        )
        by_event[mention.event_id].add(key)

    edges = {}
    for event_id, keys in by_event.items():
        for left, right in combinations(sorted(keys), 2):
            ids = tuple(sorted((_id(*left), _id(*right))))
            edge = edges.setdefault(
                ids,
                {
                    "source": ids[0],
                    "target": ids[1],
                    "type": "co_occurrence",
                    "event_ids": [],
                    "weight": 0,
                },
            )
            if event_id not in edge["event_ids"]:
                edge["event_ids"].append(event_id)
                edge["weight"] += 1

    return {
        "semantics": (
            "co-occurrence is evidence of shared context, "
            "not proof of identity or relationship"
        ),
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
    }


def build_evidence_graph(events, mentions, correlations=()):
    """Create a provenance-first graph with event and entity nodes kept distinct."""

    entity_graph = build_entity_graph(mentions)
    nodes = {
        node["id"]: dict(node)
        for node in entity_graph["nodes"]
    }

    for event in events:
        nodes[event.event_id] = {
            "id": event.event_id,
            "type": "event",
            "timestamp": event.timestamp.isoformat(),
            "artifact_type": event.artifact_type,
            "source": event.source,
            "host": event.host,
            "event_code": event.event_code,
            "message": event.message,
        }

    edges = []
    seen = set()

    for mention in mentions:
        entity_id = _id(*_key(mention))
        key = (
            entity_id,
            mention.event_id,
            "mentioned_in",
            mention.mention_id,
        )
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "source": entity_id,
                "target": mention.event_id,
                "type": "mentioned_in",
                "mention_id": mention.mention_id,
                "source_field": mention.source_field,
                "extractor": mention.extractor,
                "corroborated_by": mention.corroborated_by,
                "confidence": mention.score,
                "confidence_kind": mention.confidence_kind,
                "evidence_hash": mention.evidence_hash,
            }
        )

    for link in correlations:
        edges.append(
            {
                "source": link.left_event_id,
                "target": link.right_event_id,
                "type": "correlated_with",
                "score": link.score,
                "delta_seconds": link.delta_seconds,
                "reasons": list(link.reasons),
            }
        )

    return {
        "semantics": {
            "mentioned_in": "the normalized entity was extracted from this exact evidence span",
            "correlated_with": "events met explicit correlation rules; this does not prove causality",
            "identity_rule": "entity nodes are canonicalized mentions, not verified real-world identities",
        },
        "nodes": list(nodes.values()),
        "edges": edges,
    }
