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
  normalized_value TEXT NOT NULL DEFAULT '',
  confidence_kind TEXT NOT NULL DEFAULT '',
  evidence_hash TEXT NOT NULL DEFAULT '',
  corroborated_by_json TEXT NOT NULL DEFAULT '[]',
  FOREIGN KEY(event_id) REFERENCES events(event_id)
);
CREATE INDEX IF NOT EXISTS idx_entity_event ON entity_mentions(event_id);
CREATE INDEX IF NOT EXISTS idx_entity_label ON entity_mentions(label);
"""


ENTITY_COLUMN_MIGRATIONS = {
    "normalized_value": "TEXT NOT NULL DEFAULT ''",
    "confidence_kind": "TEXT NOT NULL DEFAULT ''",
    "evidence_hash": "TEXT NOT NULL DEFAULT ''",
    "corroborated_by_json": "TEXT NOT NULL DEFAULT '[]'",
}


def _ensure_entity_columns(connection: sqlite3.Connection) -> None:
    existing = {
        row[1]
        for row in connection.execute("PRAGMA table_info(entity_mentions)")
    }
    for name, declaration in ENTITY_COLUMN_MIGRATIONS.items():
        if name not in existing:
            connection.execute(
                f"ALTER TABLE entity_mentions ADD COLUMN {name} {declaration}"
            )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_normalized "
        "ON entity_mentions(label, normalized_value)"
    )


def save_case(path: Path, events, correlations=(), entities=()) -> None:
    event_items = list(events)
    correlation_items = list(correlations)
    entity_items = list(entities)

    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
        _ensure_entity_columns(connection)

        connection.executemany(
            "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    event.event_id,
                    event.timestamp.isoformat(),
                    event.source,
                    event.artifact_type,
                    event.event_type,
                    event.host,
                    event.user,
                    event.provider,
                    event.event_code,
                    event.pid,
                    event.message,
                    event.risk_score,
                    json.dumps(event.tags, ensure_ascii=False),
                    event.source_path,
                    event.record_locator,
                    event.parser,
                    event.parser_version,
                    event.time_assumption,
                    json.dumps(event.raw, ensure_ascii=False, default=str),
                )
                for event in event_items
            ],
        )

        connection.executemany(
            "INSERT OR REPLACE INTO correlations VALUES (?,?,?,?,?)",
            [
                (
                    item.left_event_id,
                    item.right_event_id,
                    item.delta_seconds,
                    item.score,
                    json.dumps(item.reasons),
                )
                for item in correlation_items
            ],
        )

        connection.executemany(
            """
            INSERT OR REPLACE INTO entity_mentions (
              mention_id, event_id, text, label, start_offset, end_offset,
              score, extractor, source_field, context, normalized_value,
              confidence_kind, evidence_hash, corroborated_by_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    mention.mention_id,
                    mention.event_id,
                    mention.text,
                    mention.label,
                    mention.start,
                    mention.end,
                    mention.score,
                    mention.extractor,
                    mention.source_field,
                    mention.context,
                    mention.normalized_value,
                    mention.confidence_kind,
                    mention.evidence_hash,
                    json.dumps(
                        mention.corroborated_by,
                        ensure_ascii=False,
                    ),
                )
                for mention in entity_items
            ],
        )

        connection.commit()
