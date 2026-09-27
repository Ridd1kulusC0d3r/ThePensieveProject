"""Optional Dissect Target adapter for images, collections and artefacts."""

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pensieve_timeline.model import ForensicEvent, parse_timestamp
from pensieve_timeline.parsers.base import Parser

TARGET_EXTENSIONS=(".e01",".vmdk",".vhd",".vhdx",".qcow",".qcow2",".img",".dd",".raw",".vmx",".tar")
DEFAULT_FUNCTIONS=["evtx","prefetch","amcache.applications","amcache.applaunches","amcache.general","shimcache","runkeys","mft","mft.body","usnjrnl"]
TIMESTAMP_KEYS=("timestamp","ts","mtime","atime","ctime","btime","birth_time","last_modified","modified","created","accessed","last_run","last_execution_time","date")

def _record_dict(record):
    if isinstance(record,dict): return dict(record)
    if is_dataclass(record): return asdict(record)
    method=getattr(record,"_asdict",None)
    if callable(method): return dict(method())
    return {"record":str(record)}

def _resolve(target,dotted):
    current=target
    for part in dotted.split("."): current=getattr(current,part)
    return current

def _timestamps(row):
    out=[]
    for key in TIMESTAMP_KEYS:
        value=row.get(key)
        if value in (None,""): continue
        try: dt,assumption=parse_timestamp(value if isinstance(value,datetime) else str(value))
        except ValueError: continue
        out.append((key,dt,assumption))
    return out

def iter_target_events(path, functions=DEFAULT_FUNCTIONS):
    try:
        from dissect.target import Target
    except ImportError as exc:
        raise ValueError("Dissect opcional ausente; instale pensieve-timeline[dissect]") from exc
    target=Target.open(str(path)); hostname=str(getattr(target,"hostname","") or "") or None
    for fn in functions:
        try: function=_resolve(target,fn)
        except (AttributeError,TypeError): continue
        if not callable(function): continue
        try: records=function()
        except Exception: continue
        if isinstance(records,(str,bytes,dict)): records=[records]
        try: iterator=iter(records)
        except TypeError: continue
        for index,record in enumerate(iterator,1):
            row=_record_dict(record)
            for ts_field,ts,assumption in _timestamps(row):
                source_path=row.get("source") or row.get("source_path") or row.get("path") or str(path)
                code=row.get("event_id") or row.get("eventid") or row.get("event_code")
                user=row.get("user") or row.get("username") or row.get("user_name")
                pid=row.get("pid") or row.get("process_id") or row.get("processid")
                preferred=[f"{k}={row[k]}" for k in ("name","path","command","commandline","exe","filename") if row.get(k) not in (None,"")]
                yield ForensicEvent(ts,f"Dissect:{fn}",fn.split(".",1)[0],f"{fn}: " + (", ".join(preferred[:5]) if preferred else "record"),
                    host=hostname,user=str(user) if user not in (None,"") else None,
                    event_code=str(code) if code not in (None,"") else None,pid=str(pid) if pid not in (None,"") else None,
                    event_type=f"{fn}:{ts_field}",record_locator=f"{fn}:record:{index}:{ts_field}",
                    source_path=str(source_path),parser="dissect.target",parser_version="1",
                    time_assumption=assumption,raw={str(k):v for k,v in row.items()})

class DissectTargetParser(Parser):
    name="dissect.target"; extensions=TARGET_EXTENSIONS
    def supports(self,path): return path.is_dir() or path.suffix.lower() in self.extensions
    def parse(self,path): yield from iter_target_events(path)
