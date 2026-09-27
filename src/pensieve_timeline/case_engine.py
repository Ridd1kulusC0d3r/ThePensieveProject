from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
import hashlib,json

LEVELS={"observation","inference","hypothesis"}

@dataclass(slots=True)
class InvestigativeFinding:
    level:str; statement:str; evidence_event_ids:list[str]; rationale:str
    alternatives:list[str]=field(default_factory=list); confidence:float=.5; status:str="open"; created_at:str=""; finding_id:str=""
    def __post_init__(self):
        if self.level not in LEVELS:raise ValueError(f"level inválido: {self.level}")
        if not 0<=self.confidence<=1:raise ValueError("confidence deve estar entre 0 e 1")
        if not self.created_at:self.created_at=datetime.now(timezone.utc).isoformat()
        if not self.finding_id:self.finding_id=hashlib.sha256(json.dumps([self.level,self.statement,sorted(self.evidence_event_ids),self.rationale],ensure_ascii=False).encode()).hexdigest()[:24]
    def validate(self,events):
        valid={e.event_id for e in events}; missing=sorted(set(self.evidence_event_ids)-valid)
        if missing:raise ValueError(f"finding referencia event_ids inexistentes: {', '.join(missing)}")
        if self.level=="observation" and self.alternatives:raise ValueError("observation não deve conter alternativas")
    def to_dict(self):return asdict(self)
