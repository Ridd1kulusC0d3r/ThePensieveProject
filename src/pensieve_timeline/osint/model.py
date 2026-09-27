from dataclasses import asdict, dataclass
import hashlib, json

def _id(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]

@dataclass(slots=True)
class EntityMention:
    event_id:str; text:str; label:str; start:int; end:int; score:float; extractor:str
    source_field:str="message"; context:str=""; mention_id:str=""
    def __post_init__(self):
        self.label=self.label.strip().lower().replace(" ","_")
        if not self.mention_id:
            self.mention_id=_id({"event_id":self.event_id,"text":self.text,"label":self.label,"start":self.start,"end":self.end,"source_field":self.source_field,"extractor":self.extractor})
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls,data): return cls(**data)
