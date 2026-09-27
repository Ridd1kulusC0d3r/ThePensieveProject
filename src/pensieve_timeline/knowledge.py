from pathlib import Path

def index_artifacts(path:Path):
    try: import yaml
    except ImportError as exc: raise ValueError("instale pensieve-timeline[knowledge]") from exc
    files=(sorted(path.rglob("*.yaml"))+sorted(path.rglob("*.yml"))) if path.is_dir() else [path]; records=[]
    for file in files:
        if not file.is_file():continue
        try: docs=list(yaml.safe_load_all(file.read_text(encoding="utf-8",errors="replace")))
        except Exception as exc: records.append({"source_file":str(file),"parse_error":str(exc)});continue
        for d in docs:
            if isinstance(d,dict):records.append({"name":d.get("name"),"doc":d.get("doc"),"sources":d.get("sources",[]),"supported_os":d.get("supported_os",[]),"urls":d.get("urls",[]),"source_file":str(file)})
    return records
