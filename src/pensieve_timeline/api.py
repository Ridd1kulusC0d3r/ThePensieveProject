"""Optional read-only REST API for a Pensieve SQLite case."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Any

DEFAULT_LIMIT = 200
MAX_LIMIT = 2000
PUBLIC_TABLES = ("events", "correlations", "entity_mentions")


def _case_path(value: str | Path | None = None) -> Path:
    raw = value or os.environ.get("PENSIEVE_CASE_DB") or "case.db"
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"case database not found: {path}")
    return path


def _connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _rows(
    path: Path,
    table: str,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    filters: dict[str, Any] | None = None,
    include_raw: bool = False,
) -> list[dict[str, Any]]:
    if table not in PUBLIC_TABLES:
        raise ValueError(f"table not exposed: {table}")
    limit = max(1, min(int(limit), MAX_LIMIT))
    offset = max(0, int(offset))
    filters = {k: v for k, v in (filters or {}).items() if v not in (None, "")}

    with _connect_readonly(path) as connection:
        if not _table_exists(connection, table):
            return []
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        invalid = set(filters) - columns
        if invalid:
            raise ValueError(f"unsupported filter(s): {', '.join(sorted(invalid))}")

        where = ""
        params: list[Any] = []
        if filters:
            where = " WHERE " + " AND ".join(f"{name}=?" for name in filters)
            params.extend(filters.values())

        cursor = connection.execute(
            f"SELECT * FROM {table}{where} ORDER BY rowid LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        rows = [dict(row) for row in cursor.fetchall()]

    if table == "events" and not include_raw:
        for row in rows:
            row.pop("raw_json", None)
    return rows


def _stats(path: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    with _connect_readonly(path) as connection:
        for table in PUBLIC_TABLES:
            if _table_exists(connection, table):
                result[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            else:
                result[table] = 0
    return result


def create_app(db_path: str | Path | None = None):
    """Create the optional FastAPI app.

    The database is always opened read-only. The API never mutates evidence,
    findings, correlations, or derived OSINT data.
    """
    try:
        from fastapi import FastAPI, HTTPException, Query
    except ImportError as exc:
        raise RuntimeError("FastAPI extra missing; install pensieve-timeline[api]") from exc

    path = _case_path(db_path)
    app = FastAPI(
        title="The Pensieve Project API",
        version="0.1",
        description="Read-only access to a local Pensieve case database.",
    )
    app.state.case_db = path

    @app.get("/health")
    def health():
        return {"ok": True, "database": path.name, "mode": "read-only"}

    @app.get("/stats")
    def stats():
        return _stats(path)

    @app.get("/events")
    def events(
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
        offset: int = Query(0, ge=0),
        host: str | None = None,
        artifact_type: str | None = None,
        event_code: str | None = None,
        include_raw: bool = False,
    ):
        return _rows(
            path,
            "events",
            limit=limit,
            offset=offset,
            filters={"host": host, "artifact_type": artifact_type, "event_code": event_code},
            include_raw=include_raw,
        )

    @app.get("/events/{event_id}")
    def event(event_id: str, include_raw: bool = False):
        rows = _rows(
            path,
            "events",
            limit=1,
            filters={"event_id": event_id},
            include_raw=include_raw,
        )
        if not rows:
            raise HTTPException(status_code=404, detail="event not found")
        return rows[0]

    @app.get("/entities")
    def entities(
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
        offset: int = Query(0, ge=0),
        label: str | None = None,
        event_id: str | None = None,
    ):
        return _rows(
            path,
            "entity_mentions",
            limit=limit,
            offset=offset,
            filters={"label": label, "event_id": event_id},
        )

    @app.get("/correlations")
    def correlations(
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
        offset: int = Query(0, ge=0),
        left_event_id: str | None = None,
        right_event_id: str | None = None,
    ):
        return _rows(
            path,
            "correlations",
            limit=limit,
            offset=offset,
            filters={"left_event_id": left_event_id, "right_event_id": right_event_id},
        )

    return app
