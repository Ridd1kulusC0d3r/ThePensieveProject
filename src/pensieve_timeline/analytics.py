from collections import Counter
from dataclasses import asdict, dataclass
from math import log1p

@dataclass(slots=True)
class AnomalyFinding:
    event_id:str; method:str; score:float; reasons:list[str]
    def to_dict(self): return asdict(self)

def rarity_analysis(events):
    items=list(events)
    if not items:return []
    fields={"event_code":Counter(e.event_code or "" for e in items),"provider":Counter(e.provider or "" for e in items),"user":Counter(e.user or "" for e in items),"artifact_type":Counter(e.artifact_type or "" for e in items)}
    total=len(items); out=[]
    for e in items:
        vals={"event_code":e.event_code or "","provider":e.provider or "","user":e.user or "","artifact_type":e.artifact_type or ""}
        parts=[]; reasons=[]
        for field,value in vals.items():
            if not value:continue
            count=fields[field][value]; parts.append(1-(log1p(count)/log1p(total+1)))
            if count==1:reasons.append(f"unique_{field}")
        out.append(AnomalyFinding(e.event_id,"rarity",round(sum(parts)/len(parts) if parts else 0,6),reasons))
    return sorted(out,key=lambda x:(-x.score,x.event_id))

def isolation_forest_analysis(events):
    items=list(events)
    if len(items)<8: raise ValueError("Isolation Forest requer pelo menos 8 eventos")
    try: from sklearn.ensemble import IsolationForest
    except ImportError as exc: raise ValueError("instale pensieve-timeline[ml]") from exc
    ec=Counter(e.event_code or "" for e in items); uc=Counter(e.user or "" for e in items); pc=Counter(e.provider or "" for e in items)
    vectors=[[e.timestamp.hour+e.timestamp.minute/60,e.risk_score,ec[e.event_code or ""],uc[e.user or ""],pc[e.provider or ""]] for e in items]
    model=IsolationForest(random_state=42,contamination="auto").fit(vectors); raw=model.score_samples(vectors); lo,hi=min(raw),max(raw); span=hi-lo or 1
    return sorted([AnomalyFinding(e.event_id,"isolation_forest",round(1-((float(v)-lo)/span),6),["multivariate_outlier"]) for e,v in zip(items,raw)],key=lambda x:-x.score)
