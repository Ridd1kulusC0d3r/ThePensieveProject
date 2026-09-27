"""Transparent triage rules. A score prioritizes review; it is not a verdict."""

from pensieve_timeline.model import ForensicEvent

EVENT_RULES = {
    "4625": (15, "failed-logon"), "4688": (10, "process-created"),
    "7045": (35, "service-installed"), "1": (10, "sysmon-process-create"),
    "11": (5, "sysmon-file-create"),
}

def score_event(event: ForensicEvent) -> ForensicEvent:
    if event.event_code in EVENT_RULES:
        points, tag = EVENT_RULES[event.event_code]
        event.risk_score = min(100, event.risk_score + points)
        if tag not in event.tags: event.tags.append(tag)
    if "registry-autorun" in event.tags: event.risk_score = min(100, event.risk_score + 15)
    if "registry-service" in event.tags: event.risk_score = min(100, event.risk_score + 10)
    return event
