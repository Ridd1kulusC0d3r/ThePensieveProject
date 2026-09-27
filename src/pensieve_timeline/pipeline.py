from pensieve_timeline.parsers import default_registry
from pensieve_timeline.scoring import score_event

def ingest(paths):
    registry=default_registry(); events=[]
    for path in paths:
        if not path.exists(): raise ValueError(f"entrada inexistente: {path}")
        parser=registry.resolve(path)
        events.extend(score_event(e) for e in parser.parse(path))
    events.sort(key=lambda e:e.timestamp)
    return events
