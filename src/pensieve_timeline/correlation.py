"""Explainable correlation using a bounded temporal window."""

from collections import deque
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Iterable
from pensieve_timeline.model import ForensicEvent

@dataclass(slots=True)
class Correlation:
    left_event_id: str
    right_event_id: str
    delta_seconds: float
    score: int
    reasons: list[str]
    def to_dict(self): return asdict(self)

def correlate(events: Iterable[ForensicEvent], window_seconds: int = 120, min_score: int = 4) -> list[Correlation]:
    ordered = sorted(events, key=lambda e: e.timestamp)
    active, result = deque(), []
    window = timedelta(seconds=window_seconds)
    for current in ordered:
        while active and current.timestamp - active[0].timestamp > window:
            active.popleft()
        for previous in reversed(active):
            reasons, score = [], 0
            if current.host and previous.host:
                if current.host != previous.host: continue
                score += 1; reasons.append("same_host")
            if current.user and current.user == previous.user:
                score += 2; reasons.append("same_user")
            if current.pid and current.pid == previous.pid:
                score += 5; reasons.append("same_pid")
            if current.event_code and current.event_code == previous.event_code:
                score += 1; reasons.append("same_event_code")
            delta = (current.timestamp - previous.timestamp).total_seconds()
            if delta <= 10: score += 2; reasons.append("within_10s")
            elif delta <= 60: score += 1; reasons.append("within_60s")
            if score >= min_score:
                result.append(Correlation(previous.event_id, current.event_id, delta, score, reasons))
        active.append(current)
    return result
