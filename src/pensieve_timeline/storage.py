"""SQLite case database with evidence and derived layers separated."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from pensieve_timeline.correlation import Correlation
from pensieve_timeline.model import ForensicEvent
from pensieve_timeline.osint.model import EntityMention

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  source TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  event_type TEXT,
  host TEXT,
  user_name TEXT,
  provider TEXT,
  event_code TEXT,
  pid TEXT,
  message TEXT NOT NULL,
  risk_score INTEGER NOT NULL,
  tags_json TEXT NOT NULL,
  source_path TEXT,
  record_locator TEXT,
  parser TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  time_assumption TEXT NOT NULL,
  raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_host ON events(host);
CREATE INDEX IF NOT EXISTS idx_events_event_code ON events(event_code);
CREATE TABLE IF NOT EXISTS correlations (
  left_event_id TEXT NOT NULL,
  right_event_id TEXT NOT NULL,
  delta_seconds REAL NOT NULL,
  score INTEGER NOT NULL,
  reasons_json TEXT NOT NULL,
  PRIMARY KEY(left_event_id, right_event_id)
);
CREATE TABLE IF NOT EXISTS entity_mentions (
  mention_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL,
  text TEXT NOT NULL,
  label TEXT NOT NULL,
  start_offset INTEGER NOT NULL,
  end_offset INTEGER NOT NULL,
  score REAL NOT NULL,
  extractor TEXT NOT NULL,
  source_field TEXT NOT NULL,
  context TEXT NOT NULL,
  FOREIGN KEY(event_id) REFERENCES events(event_id)
);
CREATE INDEX IF NOT EXISTS idx_entity_event ON entity_mentions(event_id);
CREATE INDEX IF NOT EXISTS idx_entity_label ON entity_mentions(label);
"""

def save_case(path: Path, events, correlations=(), entities=()) -> None:
    event_items=list(events)
    correlation_items=list(correlations)
    entity_items=list(entities)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        connection.executemany(
            "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    e.event_id, e.timestamp.isoformat(), e.source, e.artifact_type, e.event_type,
                    e.host, e.user, e.provider, e.event_code, e.pid, e.message, e.risk_score,
                    json.dumps(e.tags, ensure_ascii=False), e.source_path, e.record_locator,
                    e.parser, e.parser_version, e.time_assumption,
                    json.dumps(e.raw, ensure_ascii=False, default=str),
                )
                for e in event_items
            ],
        )
        connection.executemany(
            "INSERT OR REPLACE INTO correlations VALUES (?,?,?,?,?)",
            [
                (c.left_event_id, c.right_event_id, c.delta_seconds, c.score, json.dumps(c.reasons))
                for c in correlation_items
            ],
        )
        connection.executemany(
            "INSERT OR REPLACE INTO entity_mentions VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    m.mention_id, m.event_id, m.text, m.label, m.start, m.end, m.score,
                    m.extractor, m.source_field, m.context,
                )
                for m in entity_items
            ],
        )
        connection.commit()
