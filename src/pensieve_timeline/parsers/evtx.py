"""Optional python-evtx adapter."""

import xml.etree.ElementTree as ET
from pensieve_timeline.model import ForensicEvent, parse_timestamp
from pensieve_timeline.parsers.base import Parser

NS={"e":"http://schemas.microsoft.com/win/2004/08/events/event"}
def _text(node): return node.text if node is not None and node.text is not None else None

class EvtxParser(Parser):
    name="python-evtx"; extensions=(".evtx",)
    def parse(self,path):
        try:
            from Evtx.Evtx import Evtx
        except ImportError as exc:
            raise ValueError("parser EVTX opcional ausente; instale pensieve-timeline[evtx]") from exc
        with Evtx(str(path)) as log:
            for index,record in enumerate(log.records(),1):
                root=ET.fromstring(record.xml()); system=root.find("e:System",NS)
                if system is None: continue
                provider_node=system.find("e:Provider",NS)
                provider=provider_node.attrib.get("Name") if provider_node is not None else None
                code=_text(system.find("e:EventID",NS)); channel=_text(system.find("e:Channel",NS)) or "Windows Event Log"
                computer=_text(system.find("e:Computer",NS)); rid=_text(system.find("e:EventRecordID",NS)) or str(index)
                t=system.find("e:TimeCreated",NS)
                if t is None or not t.attrib.get("SystemTime"): continue
                ts,assumption=parse_timestamp(t.attrib["SystemTime"])
                data={}
                ed=root.find("e:EventData",NS)
                if ed is not None:
                    for pos,item in enumerate(ed.findall("e:Data",NS),1):
                        data[item.attrib.get("Name") or f"Data{pos}"]=item.text
                user=data.get("SubjectUserName") or data.get("TargetUserName") or data.get("User")
                pid=data.get("ProcessId") or data.get("NewProcessId") or data.get("ProcessID")
                detail=", ".join(f"{k}={v}" for k,v in data.items() if v not in (None,""))
                yield ForensicEvent(ts,channel,"evtx",f"EventID {code or '?'}" + (f" | {detail}" if detail else ""),
                    host=computer,user=user,event_type="windows_event",provider=provider,event_code=code,pid=pid,
                    record_locator=f"event_record_id:{rid}",source_path=str(path),parser=self.name,parser_version="1",
                    time_assumption=assumption,raw={"event_data":data})
