"""Ingestion pipeline with an explicit capability gate for optional forensic parsers."""

from pensieve_timeline.parsers import default_registry, extended_registry
from pensieve_timeline.scoring import score_event


def ingest(paths, include_optional=False):
    registry = extended_registry() if include_optional else default_registry()
    events = []
    for path in paths:
        if not path.exists():
            raise ValueError(f"entrada inexistente: {path}")
        parser = registry.resolve(path)
        events.extend(score_event(event) for event in parser.parse(path))
    events.sort(key=lambda event: event.timestamp)
    return events
