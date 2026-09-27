"""Canonical forensic event model."""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib, json
from typing import Any

def parse_timestamp(value: str | datetime) -> tuple[datetime, str]:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("timestamp vazio")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"timestamp não suportado: {value!r}") from exc
    assumption = "explicit_timezone"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        assumption = "assumed_utc"
    return dt.astimezone(timezone.utc), assumption

def _stable_id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(raw).hexdigest()[:24]

@dataclass(slots=True)
class ForensicEvent:
    timestamp: datetime
    source: str
    artifact_type: str
    message: str
    host: str | None = None
    user: str | None = None
    event_type: str | None = None
    provider: str | None = None
    event_code: str | None = None
    record_locator: str | None = None
    source_path: str | None = None
    parser: str = "unknown"
    parser_version: str = "0"
    time_assumption: str = "explicit_timezone"
    pid: str | None = None
    tags: list[str] = field(default_factory=list)
    risk_score: int = 0
    raw: dict[str, Any] = field(default_factory=dict)
    event_id: str = ""

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
            self.time_assumption = "assumed_utc"
        else:
            self.timestamp = self.timestamp.astimezone(timezone.utc)
        if not self.event_id:
            self.event_id = _stable_id({
                "timestamp": self.timestamp.isoformat(),
                "source": self.source,
                "source_path": self.source_path,
                "record_locator": self.record_locator,
                "message": self.message,
            })

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat().replace("+00:00", "Z")
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForensicEvent":
        value = dict(data)
        value["timestamp"], inferred = parse_timestamp(value["timestamp"])
        value.setdefault("time_assumption", inferred)
        return cls(**value)
