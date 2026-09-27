"""Pensieve CLI: DFIR ingestion, correlation, OSINT and evidence-bounded reasoning."""

import argparse
import json
import sys
from pathlib import Path

from pensieve_timeline import __version__
from pensieve_timeline.analytics import isolation_forest_analysis, rarity_analysis
from pensieve_timeline.correlation import correlate
from pensieve_timeline.environment import diagnose
from pensieve_timeline.integrity import fingerprint
from pensieve_timeline.io import (
    read_entities,
    read_jsonl,
    write_csv,
    write_entities,
    write_jsonl,
    write_timesketch_jsonl,
)
from pensieve_timeline.knowledge import index_artifacts
from pensieve_timeline.osint.extract import DEFAULT_GLINER_LABELS, extract_entities
from pensieve_timeline.osint.graph import build_entity_graph, build_evidence_graph
from pensieve_timeline.osint.llm import build_evidence_packet, summarize_with_qwen
from pensieve_timeline.pipeline import ingest
from pensieve_timeline.report import build_html
from pensieve_timeline.storage import save_case


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="pensieve-timeline",
        description="DFIR timeline + forensic reasoning + evidence-bounded OSINT.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Diagnosticar core e capacidades opcionais")

    cmd = commands.add_parser("hash")
    cmd.add_argument("path", type=Path)

    cmd = commands.add_parser("ingest")
    cmd.add_argument("inputs", type=Path, nargs="+")
    cmd.add_argument("-o", "--output", type=Path, default=Path("timeline.jsonl"))
    cmd.add_argument("--csv", type=Path)
    cmd.add_argument("--sqlite", type=Path)
    cmd.add_argument("--timesketch", type=Path)
    cmd.add_argument("--correlate-window", type=int, default=120)\n    cmd.add_argument("--extended-parsers", action="store_true", help="Enable LAB parsers: EVTX, Registry and Dissect targets")

    cmd = commands.add_parser("correlate")
    cmd.add_argument("timeline", type=Path)
    cmd.add_argument("-o", "--output", type=Path, default=Path("correlations.jsonl"))
    cmd.add_argument("--window", type=int, default=120)
    cmd.add_argument("--min-score", type=int, default=4)

    cmd = commands.add_parser("entities")
    cmd.add_argument("timeline", type=Path)
    cmd.add_argument("-o", "--output", type=Path, default=Path("entities.jsonl"))
    cmd.add_argument("--gliner", action="store_true")
    cmd.add_argument("--model", default="urchade/gliner_multi-v2.1")
    cmd.add_argument("--threshold", type=float, default=0.45)
    cmd.add_argument("--labels", nargs="*", default=None)
    cmd.add_argument("--include-raw", action="store_true")
    cmd.add_argument("--sqlite", type=Path)

    cmd = commands.add_parser("graph")
    cmd.add_argument("entities", type=Path)
    cmd.add_argument("-o", "--output", type=Path, default=Path("entity-graph.json"))

    cmd = commands.add_parser("evidence-graph")
    cmd.add_argument("timeline", type=Path)
    cmd.add_argument("entities", type=Path)
    cmd.add_argument("-o", "--output", type=Path, default=Path("evidence-graph.json"))
    cmd.add_argument("--window", type=int, default=120)

    cmd = commands.add_parser("analyze")
    cmd.add_argument("timeline", type=Path)
    cmd.add_argument("-o", "--output", type=Path, default=Path("analysis.jsonl"))
    cmd.add_argument("--method", choices=["rarity", "isolation-forest"], default="rarity")

    cmd = commands.add_parser("llm-summary")
    cmd.add_argument("timeline", type=Path)
    cmd.add_argument("entities", type=Path)
    cmd.add_argument("-o", "--output", type=Path, default=Path("intelligence.json"))
    cmd.add_argument("--model", default="Qwen/Qwen3-0.6B")
    cmd.add_argument("--max-events", type=int, default=40)

    cmd = commands.add_parser("artifacts-index")
    cmd.add_argument("path", type=Path)
    cmd.add_argument("-o", "--output", type=Path, default=Path("artifact-index.json"))

    cmd = commands.add_parser("report")
    cmd.add_argument("timeline", type=Path)
    cmd.add_argument("-o", "--output", type=Path, default=Path("report.html"))
    cmd.add_argument("--entities", type=Path)

    return parser


def _write_rows(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = diagnose()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 1

        if args.command == "hash":
            print(json.dumps(fingerprint(args.path), ensure_ascii=False, indent=2))
            return 0

        if args.command == "ingest":
            events = ingest(args.inputs, include_optional=args.extended_parsers)
            write_jsonl(events, args.output)
            links = correlate(events, window_seconds=args.correlate_window)
            if args.csv:
                write_csv(events, args.csv)
            if args.timesketch:
                write_timesketch_jsonl(events, args.timesketch)
            if args.sqlite:
                save_case(args.sqlite, events, links)
            print(json.dumps({"ok": True, "events": len(events), "correlations": len(links), "output": str(args.output)}, indent=2))
            return 0

        if args.command == "correlate":
            events = read_jsonl(args.timeline)
            links = correlate(events, window_seconds=args.window, min_score=args.min_score)
            _write_rows(args.output, [link.to_dict() for link in links])
            print(json.dumps({"ok": True, "correlations": len(links), "output": str(args.output)}, indent=2))
            return 0

        if args.command == "entities":
            events = read_jsonl(args.timeline)
            mentions = extract_entities(
                events,
                use_gliner=args.gliner,
                model_name=args.model,
                labels=args.labels or DEFAULT_GLINER_LABELS,
                threshold=args.threshold,
                include_raw=args.include_raw,
            )
            write_entities(mentions, args.output)
            if args.sqlite:
                save_case(args.sqlite, events, correlate(events), mentions)
            print(json.dumps({"ok": True, "entities": len(mentions), "gliner": args.gliner, "output": str(args.output)}, indent=2))
            return 0

        if args.command == "graph":
            graph = build_entity_graph(read_entities(args.entities))
            args.output.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"ok": True, "nodes": len(graph["nodes"]), "edges": len(graph["edges"]), "output": str(args.output)}, indent=2))
            return 0

        if args.command == "evidence-graph":
            events = read_jsonl(args.timeline)
            mentions = read_entities(args.entities)
            graph = build_evidence_graph(events, mentions, correlate(events, window_seconds=args.window))
            args.output.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"ok": True, "nodes": len(graph["nodes"]), "edges": len(graph["edges"]), "output": str(args.output)}, indent=2))
            return 0

        if args.command == "analyze":
            events = read_jsonl(args.timeline)
            findings = rarity_analysis(events) if args.method == "rarity" else isolation_forest_analysis(events)
            _write_rows(args.output, [finding.to_dict() for finding in findings])
            print(json.dumps({"ok": True, "method": args.method, "findings": len(findings)}, indent=2))
            return 0

        if args.command == "llm-summary":
            packet = build_evidence_packet(read_jsonl(args.timeline), read_entities(args.entities), max_events=args.max_events)
            result = summarize_with_qwen(packet, model_name=args.model)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"ok": True, "model": args.model, "output": str(args.output)}, indent=2))
            return 0

        if args.command == "artifacts-index":
            records = index_artifacts(args.path)
            args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"ok": True, "artifacts": len(records), "output": str(args.output)}, indent=2))
            return 0

        if args.command == "report":
            events = read_jsonl(args.timeline)
            mentions = read_entities(args.entities) if args.entities else []
            build_html(events, args.output, mentions)
            print(json.dumps({"ok": True, "events": len(events), "entities": len(mentions), "output": str(args.output)}, indent=2))
            return 0

    except (OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    return 2
