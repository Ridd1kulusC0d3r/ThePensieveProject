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
            edge=edges.setdefault(ids,{"source":ids[0],"target":ids[1],"type":"co_occurrence","event_ids":[],"weight":0})
            edge["event_ids"].append(event_id); edge["weight"]+=1
    return {"semantics":"co-occurrence is evidence of shared context, not proof of identity or relationship","nodes":list(nodes.values()),"edges":list(edges.values())}

def build_evidence_graph(events,mentions,correlations=()):
    """Create a provenance-first graph with event and entity nodes kept distinct."""
    entity_graph=build_entity_graph(mentions)
    nodes={node["id"]:dict(node) for node in entity_graph["nodes"]}
    for event in events:
        nodes[event.event_id]={
            "id":event.event_id,"type":"event","timestamp":event.timestamp.isoformat(),
            "artifact_type":event.artifact_type,"source":event.source,"host":event.host,
            "event_code":event.event_code,"message":event.message,
        }
    edges=[]
    seen=set()
    for mention in mentions:
        entity_id=_id(*_key(mention))
        key=(entity_id,mention.event_id,"mentioned_in",mention.mention_id)
        if key in seen: continue
        seen.add(key)
        edges.append({
            "source":entity_id,"target":mention.event_id,"type":"mentioned_in",
            "mention_id":mention.mention_id,"source_field":mention.source_field,
            "extractor":mention.extractor,"confidence":mention.score,
        })
    for link in correlations:
        edges.append({
            "source":link.left_event_id,"target":link.right_event_id,"type":"correlated_with",
            "score":link.score,"delta_seconds":link.delta_seconds,"reasons":list(link.reasons),
        })
    return {
        "semantics":{
            "mentioned_in":"the entity text was extracted from this event",
            "correlated_with":"events met explicit correlation rules; this does not prove causality",
            "identity_rule":"entity nodes are normalized mentions, not verified real-world identities",
        },
        "nodes":list(nodes.values()),"edges":edges,
    }
