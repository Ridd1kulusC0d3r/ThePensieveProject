"""Operational runners for the two reference VM profiles."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sys

from pensieve_timeline.correlation import correlate
from pensieve_timeline.integrity import fingerprint
from pensieve_timeline.io import (
    read_jsonl,
    write_csv,
    write_entities,
    write_jsonl,
    write_timesketch_jsonl,
)
from pensieve_timeline.osint.extract import DEFAULT_GLINER_LABELS, extract_entities
from pensieve_timeline.osint.graph import build_evidence_graph
from pensieve_timeline.osint.llm import (
    build_evidence_packet,
    summarize_with_qwen,
)
from pensieve_timeline.pipeline import ingest
from pensieve_timeline.report import build_html
from pensieve_timeline.storage import save_case


DEFAULT_GLINER_MODEL = "urchade/gliner_multi-v2.1"
DEFAULT_QWEN_MODEL = "Qwen/Qwen3-0.6B"


def _safe_case_id(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("case-%Y%m%dT%H%M%SZ")
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    if not clean:
        raise ValueError("case id is empty after sanitization")
    return clean[:100]


def _workspace(root: Path, case_id: str | None) -> Path:
    path = root.expanduser().resolve() / _safe_case_id(case_id)
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_correlations(path: Path, links) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for link in links:
            handle.write(
                json.dumps(
                    link.to_dict(),
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )


def _write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _common_outputs(workspace: Path, events, links, entities=()):
    timeline_jsonl = workspace / "timeline.jsonl"
    timeline_csv = workspace / "timeline.csv"
    timesketch_jsonl = workspace / "timesketch.jsonl"
    correlations_jsonl = workspace / "correlations.jsonl"
    case_db = workspace / "case.db"
    report_html = workspace / "report.html"

    write_jsonl(events, timeline_jsonl)
    write_csv(events, timeline_csv)
    write_timesketch_jsonl(events, timesketch_jsonl)
    _write_correlations(correlations_jsonl, links)
    save_case(case_db, events, links, entities)
    build_html(events, report_html, entities)

    return {
        "timeline_jsonl": str(timeline_jsonl),
        "timeline_csv": str(timeline_csv),
        "timesketch_jsonl": str(timesketch_jsonl),
        "correlations_jsonl": str(correlations_jsonl),
        "case_db": str(case_db),
        "report_html": str(report_html),
    }


def run_forensic(
    input_path: Path,
    *,
    workspace_root: Path,
    case_id: str | None = None,
    extended_parsers: bool = False,
    correlation_window: int = 120,
) -> dict:
    """Run the no-AI forensic profile."""

    input_path = input_path.expanduser().resolve()
    workspace = _workspace(workspace_root, case_id)
    evidence = fingerprint(input_path)

    events = ingest(
        [input_path],
        include_optional=extended_parsers,
    )
    links = correlate(
        events,
        window_seconds=correlation_window,
    )

    outputs = _common_outputs(
        workspace,
        events,
        links,
    )

    manifest = {
        "profile": "forensic",
        "ai_enabled": False,
        "gliner_enabled": False,
        "qwen_enabled": False,
        "case_id": workspace.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": evidence,
        "input_mode": "evidence",
        "event_count": len(events),
        "correlation_count": len(links),
        "extended_parsers": extended_parsers,
        "outputs": outputs,
    }
    _write_json(workspace / "manifest.json", manifest)
    return manifest


def run_ai(
    input_path: Path,
    *,
    workspace_root: Path,
    case_id: str | None = None,
    extended_parsers: bool = False,
    correlation_window: int = 120,
    gliner_enabled: bool = True,
    qwen_enabled: bool = True,
    gliner_model: str = DEFAULT_GLINER_MODEL,
    qwen_model: str = DEFAULT_QWEN_MODEL,
    gliner_threshold: float = 0.45,
    labels=None,
    max_events: int = 40,
    max_message_chars: int = 700,
    canonical_timeline: bool = False,
) -> dict:
    """Run the AI analyst profile.

    GLiNER and Qwen are intentionally enabled by default for this profile.
    """

    input_path = input_path.expanduser().resolve()
    workspace = _workspace(workspace_root, case_id)
    evidence = fingerprint(input_path)

    if canonical_timeline:
        events = read_jsonl(input_path)
        input_mode = "canonical_timeline"
    else:
        events = ingest(
            [input_path],
            include_optional=extended_parsers,
        )
        input_mode = "evidence"

    links = correlate(
        events,
        window_seconds=correlation_window,
    )

    mentions = extract_entities(
        events,
        use_gliner=gliner_enabled,
        model_name=gliner_model,
        labels=labels or DEFAULT_GLINER_LABELS,
        threshold=gliner_threshold,
    )

    entities_jsonl = workspace / "entities.jsonl"
    evidence_graph_json = workspace / "evidence-graph.json"
    packet_json = workspace / "evidence-packet.json"
    intelligence_json = workspace / "intelligence.json"

    write_entities(mentions, entities_jsonl)
    graph = build_evidence_graph(events, mentions, links)
    _write_json(evidence_graph_json, graph)

    packet = build_evidence_packet(
        events,
        mentions,
        max_events=max_events,
        max_message_chars=max_message_chars,
    )
    _write_json(packet_json, packet)

    intelligence = None
    if qwen_enabled:
        intelligence = summarize_with_qwen(
            packet,
            model_name=qwen_model,
        )
        _write_json(intelligence_json, intelligence)

    outputs = _common_outputs(
        workspace,
        events,
        links,
        mentions,
    )
    outputs.update(
        {
            "entities_jsonl": str(entities_jsonl),
            "evidence_graph_json": str(evidence_graph_json),
            "evidence_packet_json": str(packet_json),
            "intelligence_json": (
                str(intelligence_json) if intelligence is not None else None
            ),
        }
    )

    manifest = {
        "profile": "ai",
        "ai_enabled": True,
        "gliner_enabled": gliner_enabled,
        "qwen_enabled": qwen_enabled,
        "gliner_model": gliner_model if gliner_enabled else None,
        "qwen_model": qwen_model if qwen_enabled else None,
        "case_id": workspace.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": evidence,
        "input_mode": input_mode,
        "event_count": len(events),
        "correlation_count": len(links),
        "entity_count": len(mentions),
        "claim_count": (
            len(intelligence.get("claims", []))
            if isinstance(intelligence, dict)
            else 0
        ),
        "extended_parsers": extended_parsers,
        "outputs": outputs,
    }
    _write_json(workspace / "manifest.json", manifest)
    return manifest


def serve_dashboard(
    root: Path,
    *,
    bind: str = "127.0.0.1",
    port: int = 8080,
) -> None:
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    handler = partial(
        SimpleHTTPRequestHandler,
        directory=str(root),
    )
    server = ThreadingHTTPServer((bind, port), handler)

    print(
        f"Pensieve dashboard root: {root}\n"
        f"Listening on http://{bind}:{port}/"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pensieve-ops",
        description="Reference VM workflows for The Pensieve Project.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    forensic = sub.add_parser(
        "forensic",
        help="Run forensic-only analysis with no AI dependencies.",
    )
    forensic.add_argument("input", type=Path)
    forensic.add_argument(
        "--workspace-root",
        type=Path,
        default=Path("/srv/pensieve/cases"),
    )
    forensic.add_argument("--case-id")
    forensic.add_argument("--extended-parsers", action="store_true")
    forensic.add_argument("--window", type=int, default=120)

    ai = sub.add_parser(
        "ai",
        help="Run GLiNER + Qwen workflow. Both are enabled by default.",
    )
    ai.add_argument("input", type=Path)
    ai.add_argument(
        "--workspace-root",
        type=Path,
        default=Path("/srv/pensieve/cases"),
    )
    ai.add_argument("--case-id")
    ai.add_argument("--extended-parsers", action="store_true")
    ai.add_argument("--window", type=int, default=120)
    ai.add_argument("--no-gliner", action="store_true")
    ai.add_argument("--no-qwen", action="store_true")
    ai.add_argument("--gliner-model", default=DEFAULT_GLINER_MODEL)
    ai.add_argument("--qwen-model", default=DEFAULT_QWEN_MODEL)
    ai.add_argument("--gliner-threshold", type=float, default=0.45)
    ai.add_argument("--labels", nargs="*")
    ai.add_argument("--max-events", type=int, default=40)
    ai.add_argument("--max-message-chars", type=int, default=700)
    ai.add_argument(
        "--canonical-timeline",
        action="store_true",
        help="Treat input as an existing Pensieve timeline.jsonl instead of re-ingesting evidence.",
    )

    serve = sub.add_parser(
        "serve",
        help="Serve case directories and HTML reports over local HTTP.",
    )
    serve.add_argument(
        "--root",
        type=Path,
        default=Path("/srv/pensieve/cases"),
    )
    serve.add_argument("--bind", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)

    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)

    try:
        if args.command == "forensic":
            result = run_forensic(
                args.input,
                workspace_root=args.workspace_root,
                case_id=args.case_id,
                extended_parsers=args.extended_parsers,
                correlation_window=args.window,
            )
        elif args.command == "ai":
            result = run_ai(
                args.input,
                workspace_root=args.workspace_root,
                case_id=args.case_id,
                extended_parsers=args.extended_parsers,
                correlation_window=args.window,
                gliner_enabled=not args.no_gliner,
                qwen_enabled=not args.no_qwen,
                gliner_model=args.gliner_model,
                qwen_model=args.qwen_model,
                gliner_threshold=args.gliner_threshold,
                labels=args.labels,
                max_events=args.max_events,
                max_message_chars=args.max_message_chars,
                canonical_timeline=args.canonical_timeline,
            )
        else:
            serve_dashboard(
                args.root,
                bind=args.bind,
                port=args.port,
            )
            return 0

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
