"""Deterministic indicators first; optional GLiNER for open labels."""

import ipaddress, json, re
from pensieve_timeline.osint.model import EntityMention

DEFAULT_GLINER_LABELS=["person","organization","location","phone number","email","domain","ip address","url","username","social media handle","cryptocurrency wallet"]
PATTERNS=[
 ("email",re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",re.I)),
 ("url",re.compile(r"https?://[^\s<>\"']+",re.I)),
 ("ipv4",re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")),
 ("phone",re.compile(r"(?<!\d)(?:\+?55[\s.-]?)?(?:\(?\d{2}\)?[\s.-]?)?(?:9?\d{4})[\s.-]?\d{4}(?!\d)")),
 ("social_handle",re.compile(r"(?<![\w@])@[A-Za-z0-9_][A-Za-z0-9_.-]{1,31}")),
 ("ethereum_wallet",re.compile(r"(?<![A-Fa-f0-9])0x[A-Fa-f0-9]{40}(?![A-Fa-f0-9])")),
 ("bitcoin_wallet",re.compile(r"(?<![A-Za-z0-9])(?:bc1[a-zA-HJ-NP-Z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})(?![A-Za-z0-9])")),
 ("domain",re.compile(r"(?<![@\w.-])(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}(?![\w.-])"))
]

def _context(text,start,end,radius=90): return text[max(0,start-radius):min(len(text),end+radius)].strip()
def _valid(label,value):
    if label=="ipv4":
        try: return isinstance(ipaddress.ip_address(value),ipaddress.IPv4Address)
        except ValueError: return False
    if label=="phone": return 10 <= len(re.sub(r"\D","",value)) <= 13
    return True

def extract_patterns(event_id,text,source_field="message"):
    out=[]; protected=[]
    for label,rx in PATTERNS:
        for m in rx.finditer(text):
            value=m.group(0).rstrip(".,;:)"); end=m.start()+len(value)
            if not _valid(label,value): continue
            if label=="domain" and any(m.start()>=a and end<=b for a,b in protected): continue
            out.append(EntityMention(event_id,value,label,m.start(),end,1.0,"regex",source_field,_context(text,m.start(),end)))
            if label in {"email","url"}: protected.append((m.start(),end))
    return out

class GlinerExtractor:
    def __init__(self,model_name="urchade/gliner_multi-v2.1",threshold=.45):
        try:
            from gliner import GLiNER
        except ImportError as exc: raise ValueError("GLiNER opcional ausente; instale pensieve-timeline[osint]") from exc
        self.model_name=model_name; self.threshold=threshold; self.model=GLiNER.from_pretrained(model_name)
    def extract(self,event_id,text,labels,source_field="message"):
        out=[]
        for e in self.model.predict_entities(text,labels,threshold=self.threshold):
            start=int(e.get("start",0)); end=int(e.get("end",start+len(e.get("text",""))))
            out.append(EntityMention(event_id,str(e.get("text",text[start:end])),str(e.get("label","entity")),start,end,float(e.get("score",0)),f"gliner:{self.model_name}",source_field,_context(text,start,end)))
        return out

def extract_entities(events,*,use_gliner=False,model_name="urchade/gliner_multi-v2.1",labels=None,threshold=.45,include_raw=False):
    gliner=GlinerExtractor(model_name,threshold) if use_gliner else None; output={}
    for event in events:
        fields=[("message",event.message)]
        if include_raw and event.raw: fields.append(("raw",json.dumps(event.raw,ensure_ascii=False,default=str)[:8000]))
        for field,text in fields:
            for m in extract_patterns(event.event_id,text,field): output[m.mention_id]=m
            if gliner:
                for m in gliner.extract(event.event_id,text,labels or DEFAULT_GLINER_LABELS,field): output[m.mention_id]=m
    return sorted(output.values(),key=lambda m:(m.event_id,m.start,m.label))
