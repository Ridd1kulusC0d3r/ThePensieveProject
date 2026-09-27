from collections import defaultdict
import hashlib
from itertools import combinations

def _key(m): return m.label," ".join(m.text.casefold().split())
def _id(label,value): return "entity:"+hashlib.sha256(f"{label}\0{value}".encode()).hexdigest()[:20]

def build_entity_graph(mentions):
    nodes={}; by_event=defaultdict(set)
    for m in mentions:
        key=_key(m)
        node=nodes.setdefault(key,{"id":_id(*key),"type":"entity","label":m.label,"value":m.text,"normalized":key[1],"mention_ids":[],"event_ids":[]})
        node["mention_ids"].append(m.mention_id)
        if m.event_id not in node["event_ids"]: node["event_ids"].append(m.event_id)
        by_event[m.event_id].add(key)
    edges={}
    for event_id,keys in by_event.items():
        for left,right in combinations(sorted(keys),2):
            ids=tuple(sorted((_id(*left),_id(*right))))
            e=edges.setdefault(ids,{"source":ids[0],"target":ids[1],"type":"co_occurrence","event_ids":[],"weight":0})
            e["event_ids"].append(event_id); e["weight"]+=1
    return {"semantics":"co-occurrence is evidence of shared context, not proof of identity or relationship","nodes":list(nodes.values()),"edges":list(edges.values())}
