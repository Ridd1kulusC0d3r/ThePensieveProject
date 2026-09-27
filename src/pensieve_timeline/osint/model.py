"""Evidence-bound entity mention model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json

from pensieve_timeline.osint.normalize import confidence_kind, normalize_label, normalize_value


def _id(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:24]


@dataclass(slots=True)
class EntityMention:
    event_id: str
    text: str
    label: str
    start: int
    end: int
    score: float
    extractor: str
    source_field: str = "message"
    context: str = ""
    normalized_value: str = ""
    confidence_kind: str = ""
    evidence_hash: str = ""
    corroborated_by: list[str] = field(default_factory=list)
    mention_id: str = ""

    def __post_init__(self) -> None:
        self.label = normalize_label(self.label)
        self.text = str(self.text)
        self.start = int(self.start)
        self.end = int(self.end)
        self.score = float(self.score)

        if self.start < 0 or self.end <= self.start:
            raise ValueError("entity offsets must satisfy 0 <= start < end")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("entity score must be between 0 and 1")

        if not self.normalized_value:
            self.normalized_value = normalize_value(self.label, self.text)
        if not self.confidence_kind:
            self.confidence_kind = confidence_kind(self.extractor)
        if not self.corroborated_by:
            self.corroborated_by = [self.extractor]
        else:
            self.corroborated_by = sorted(set(self.corroborated_by))

        if not self.evidence_hash:
            self.evidence_hash = hashlib.sha256(
                json.dumps(
                    {
                        "event_id": self.event_id,
                        "source_field": self.source_field,
                        "start": self.start,
                        "end": self.end,
                        "text": self.text,
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()

        if not self.mention_id:
            self.mention_id = _id(
                {
                    "event_id": self.event_id,
                    "label": self.label,
                    "normalized_value": self.normalized_value,
                    "start": self.start,
                    "end": self.end,
                    "source_field": self.source_field,
                }
            )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
