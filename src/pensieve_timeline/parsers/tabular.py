"""CSV/TSV/JSONL parsers with common Hayabusa/Timeline Explorer aliases."""

import csv, json
from pathlib import Path
from typing import Any, Iterable
from pensieve_timeline.model import ForensicEvent, parse_timestamp
from pensieve_timeline.parsers.base import Parser

ALIASES = {
 "timestamp":("datetime","timestamp","timecreated","eventtime","date_time","@timestamp"),
 "host":("computer","hostname","host","machine","computername"),
 "user":("user","username","subjectusername","accountname","user_name"),
 "event_code":("eventid","event_id","eventcode","id"),
 "provider":("provider","providername","source_name"),
 "message":("message","details","ruletitle","description","event_data"),
 "pid":("processid","process_id","pid","newprocessid"),
 "source":("channel","logname","source","source_type"),
}

def _pick(row: dict[str,Any], name: str):
    mapping={k.lower().replace(" ","").replace("-",""):k for k in row}
    for alias in ALIASES[name]:
        key=alias.lower().replace(" ","").replace("-","")
        if key in mapping and row.get(mapping[key]) not in (None,""): return row[mapping[key]]
    return None

def normalize_row(row, *, path, locator, parser_name):
    raw_ts=_pick(row,"timestamp")
    if raw_ts is None: raise ValueError(f"registro {locator} sem campo de tempo reconhecido")
    ts, assumption=parse_timestamp(str(raw_ts))
    code, provider=_pick(row,"event_code"), _pick(row,"provider")
    return ForensicEvent(
        timestamp=ts, source=str(_pick(row,"source") or provider or path.suffix.lstrip(".")),
        artifact_type="event_log" if code else "tabular",
        message=str(_pick(row,"message") or f"Evento {code or 'sem código'}"),
        host=str(_pick(row,"host")) if _pick(row,"host") is not None else None,
        user=str(_pick(row,"user")) if _pick(row,"user") is not None else None,
        event_type="windows_event" if code else "row",
        provider=str(provider) if provider is not None else None,
        event_code=str(code) if code is not None else None,
        pid=str(_pick(row,"pid")) if _pick(row,"pid") is not None else None,
        record_locator=locator, source_path=str(path), parser=parser_name, parser_version="1",
        time_assumption=assumption, raw={str(k):v for k,v in row.items()},
    )

class DelimitedParser(Parser):
    name="delimited"; extensions=(".csv",".tsv")
    def parse(self,path):
        delimiter="	" if path.suffix.lower()==".tsv" else ","
        with path.open("r",encoding="utf-8-sig",newline="",errors="replace") as h:
            reader=csv.DictReader(h,delimiter=delimiter)
            for n,row in enumerate(reader,start=2):
                yield normalize_row(row,path=path,locator=f"line:{n}",parser_name=self.name)

class JsonlParser(Parser):
    name="jsonl"; extensions=(".jsonl",".ndjson")
    def parse(self,path):
        with path.open("r",encoding="utf-8",errors="replace") as h:
            for n,line in enumerate(h,start=1):
                if not line.strip(): continue
                row=json.loads(line)
                if "event_id" in row and "artifact_type" in row and "parser" in row: yield ForensicEvent.from_dict(row)
                else: yield normalize_row(row,path=path,locator=f"line:{n}",parser_name=self.name)
