"""Portable JSONL/CSV exporters and JSONL readers."""
import csv, json
from pathlib import Path
from typing import Iterable
from pensieve_timeline.model import ForensicEvent
from pensieve_timeline.osint.model import EntityMention

CORE_COLUMNS=["timestamp","event_id","source","artifact_type","event_type","host","user","provider","event_code","pid","message","risk_score","tags","source_path","record_locator","parser","parser_version","time_assumption"]

def write_jsonl(events:Iterable[ForensicEvent],path:Path)->None:
    with path.open("w",encoding="utf-8") as h:
        for e in events:h.write(json.dumps(e.to_dict(),ensure_ascii=False,default=str)+"\n")
def read_jsonl(path:Path)->list[ForensicEvent]:
    out=[]
    with path.open("r",encoding="utf-8") as h:
        for n,line in enumerate(h,1):
            if not line.strip():continue
            try:obj=json.loads(line)
            except json.JSONDecodeError as exc:raise ValueError(f"{path}:{n}: JSON inválido") from exc
            out.append(ForensicEvent.from_dict(obj))
    return out
def write_entities(entities:Iterable[EntityMention],path:Path)->None:
    with path.open("w",encoding="utf-8") as h:
        for e in entities:h.write(json.dumps(e.to_dict(),ensure_ascii=False,default=str)+"\n")
def read_entities(path:Path)->list[EntityMention]:
    out=[]
    with path.open("r",encoding="utf-8") as h:
        for n,line in enumerate(h,1):
            if not line.strip():continue
            try:value=json.loads(line)
            except json.JSONDecodeError as exc:raise ValueError(f"{path}:{n}: JSON inválido") from exc
            out.append(EntityMention.from_dict(value))
    return out
def write_csv(events:Iterable[ForensicEvent],path:Path)->None:
    with path.open("w",encoding="utf-8",newline="") as h:
        writer=csv.DictWriter(h,fieldnames=CORE_COLUMNS);writer.writeheader()
        for e in events:
            row=e.to_dict();row["tags"]=";".join(e.tags);writer.writerow({k:row.get(k) for k in CORE_COLUMNS})
def write_timesketch_jsonl(events:Iterable[ForensicEvent],path:Path)->None:
    with path.open("w",encoding="utf-8") as h:
        for e in events:
            row=e.to_dict();row["datetime"]=row["timestamp"];row["timestamp_desc"]=e.artifact_type
            h.write(json.dumps(row,ensure_ascii=False,default=str)+"\n")
