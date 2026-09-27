"""Pensieve CLI: DFIR ingestion, correlation, OSINT and evidence-bounded reasoning."""
import argparse, json, sys
from pathlib import Path
from pensieve_timeline import __version__
from pensieve_timeline.analytics import isolation_forest_analysis, rarity_analysis
from pensieve_timeline.correlation import correlate
from pensieve_timeline.environment import diagnose
from pensieve_timeline.integrity import fingerprint
from pensieve_timeline.io import read_entities, read_jsonl, write_csv, write_entities, write_jsonl, write_timesketch_jsonl
from pensieve_timeline.knowledge import index_artifacts
from pensieve_timeline.osint.extract import DEFAULT_GLINER_LABELS, extract_entities
from pensieve_timeline.osint.graph import build_entity_graph
from pensieve_timeline.osint.llm import build_evidence_packet, summarize_with_qwen
from pensieve_timeline.pipeline import ingest
from pensieve_timeline.report import build_html
from pensieve_timeline.storage import save_case

def _build_parser():
    p=argparse.ArgumentParser(prog="pensieve-timeline",description="DFIR timeline + forensic reasoning + evidence-bounded OSINT.")
    p.add_argument("--version",action="version",version=__version__)
    c=p.add_subparsers(dest="command",required=True)
    c.add_parser("doctor",help="Diagnosticar core e capacidades opcionais")
    x=c.add_parser("hash"); x.add_argument("path",type=Path)
    x=c.add_parser("ingest"); x.add_argument("inputs",type=Path,nargs="+"); x.add_argument("-o","--output",type=Path,default=Path("timeline.jsonl")); x.add_argument("--csv",type=Path); x.add_argument("--sqlite",type=Path); x.add_argument("--timesketch",type=Path); x.add_argument("--correlate-window",type=int,default=120)
    x=c.add_parser("correlate"); x.add_argument("timeline",type=Path); x.add_argument("-o","--output",type=Path,default=Path("correlations.jsonl")); x.add_argument("--window",type=int,default=120); x.add_argument("--min-score",type=int,default=4)
    x=c.add_parser("entities"); x.add_argument("timeline",type=Path); x.add_argument("-o","--output",type=Path,default=Path("entities.jsonl")); x.add_argument("--gliner",action="store_true"); x.add_argument("--model",default="urchade/gliner_multi-v2.1"); x.add_argument("--threshold",type=float,default=.45); x.add_argument("--labels",nargs="*",default=None); x.add_argument("--include-raw",action="store_true"); x.add_argument("--sqlite",type=Path)
    x=c.add_parser("graph"); x.add_argument("entities",type=Path); x.add_argument("-o","--output",type=Path,default=Path("entity-graph.json"))
    x=c.add_parser("analyze"); x.add_argument("timeline",type=Path); x.add_argument("-o","--output",type=Path,default=Path("analysis.jsonl")); x.add_argument("--method",choices=["rarity","isolation-forest"],default="rarity")
    x=c.add_parser("llm-summary"); x.add_argument("timeline",type=Path); x.add_argument("entities",type=Path); x.add_argument("-o","--output",type=Path,default=Path("intelligence.json")); x.add_argument("--model",default="Qwen/Qwen3-0.6B"); x.add_argument("--max-events",type=int,default=40)
    x=c.add_parser("artifacts-index"); x.add_argument("path",type=Path); x.add_argument("-o","--output",type=Path,default=Path("artifact-index.json"))
    x=c.add_parser("report"); x.add_argument("timeline",type=Path); x.add_argument("-o","--output",type=Path,default=Path("report.html")); x.add_argument("--entities",type=Path)
    return p

def _write_rows(path,rows):
    with path.open("w",encoding="utf-8") as h:
        for row in rows: h.write(json.dumps(row,ensure_ascii=False,default=str)+"\n")

def main(argv=None):
    p=_build_parser(); a=p.parse_args(argv)
    try:
        if a.command=="doctor":
            result=diagnose(); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result["ok"] else 1
        if a.command=="hash":
            print(json.dumps(fingerprint(a.path),ensure_ascii=False,indent=2)); return 0
        if a.command=="ingest":
            events=ingest(a.inputs); write_jsonl(events,a.output); links=correlate(events,window_seconds=a.correlate_window)
            if a.csv: write_csv(events,a.csv)
            if a.timesketch: write_timesketch_jsonl(events,a.timesketch)
            if a.sqlite: save_case(a.sqlite,events,links)
            print(json.dumps({"ok":True,"events":len(events),"correlations":len(links),"output":str(a.output)},indent=2)); return 0
        if a.command=="correlate":
            links=correlate(read_jsonl(a.timeline),window_seconds=a.window,min_score=a.min_score); _write_rows(a.output,[x.to_dict() for x in links]); print(json.dumps({"ok":True,"correlations":len(links),"output":str(a.output)},indent=2)); return 0
        if a.command=="entities":
            events=read_jsonl(a.timeline); mentions=extract_entities(events,use_gliner=a.gliner,model_name=a.model,labels=a.labels or DEFAULT_GLINER_LABELS,threshold=a.threshold,include_raw=a.include_raw); write_entities(mentions,a.output)
            if a.sqlite: save_case(a.sqlite,events,correlate(events),mentions)
            print(json.dumps({"ok":True,"entities":len(mentions),"gliner":a.gliner,"output":str(a.output)},indent=2)); return 0
        if a.command=="graph":
            graph=build_entity_graph(read_entities(a.entities)); a.output.write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps({"ok":True,"nodes":len(graph["nodes"]),"edges":len(graph["edges"]),"output":str(a.output)},indent=2)); return 0
        if a.command=="analyze":
            events=read_jsonl(a.timeline); findings=rarity_analysis(events) if a.method=="rarity" else isolation_forest_analysis(events); _write_rows(a.output,[x.to_dict() for x in findings]); print(json.dumps({"ok":True,"method":a.method,"findings":len(findings)},indent=2)); return 0
        if a.command=="llm-summary":
            packet=build_evidence_packet(read_jsonl(a.timeline),read_entities(a.entities),max_events=a.max_events); result=summarize_with_qwen(packet,model_name=a.model); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps({"ok":True,"model":a.model,"output":str(a.output)},indent=2)); return 0
        if a.command=="artifacts-index":
            records=index_artifacts(a.path); a.output.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps({"ok":True,"artifacts":len(records),"output":str(a.output)},indent=2)); return 0
        if a.command=="report":
            events=read_jsonl(a.timeline); mentions=read_entities(a.entities) if a.entities else []; build_html(events,a.output,mentions); print(json.dumps({"ok":True,"events":len(events),"entities":len(mentions),"output":str(a.output)},indent=2)); return 0
    except (OSError,ValueError) as exc:
        print(f"Erro: {exc}",file=sys.stderr); return 2
    return 2
