"""Local Qwen over a bounded evidence packet."""

import json

SYSTEM_PROMPT="""Você é um assistente de análise forense e OSINT. Use SOMENTE o pacote de evidências.
Não invente pessoas, vínculos, causalidade, identidade ou intenção. Correlação não prova identidade.
Produza JSON com summary, observations, relationships, uncertainties e next_questions.
Cada observation e relationship deve citar evidence_event_ids."""

def build_evidence_packet(events,mentions,*,max_events=40,max_message_chars=700):
    event_map={e.event_id:e for e in events}; grouped={}
    for m in mentions: grouped.setdefault(m.event_id,[]).append(m)
    rows=[]
    for event_id in list(grouped)[:max_events]:
        e=event_map.get(event_id)
        if not e: continue
        rows.append({"event_id":e.event_id,"timestamp":e.timestamp.isoformat(),"source":e.source,"artifact_type":e.artifact_type,
          "host":e.host,"user":e.user,"event_code":e.event_code,"message":e.message[:max_message_chars],
          "entities":[{"text":m.text,"label":m.label,"score":round(m.score,4),"extractor":m.extractor} for m in grouped[event_id]]})
    return {"policy":{"scope":"evidence-bounded","rule":"do not infer identity or causality solely from co-occurrence","external_enrichment":False},"events":rows}

def _json(text):
    a,b=text.find("{"),text.rfind("}")
    if a<0 or b<=a:return {"parse_error":"model did not return JSON","raw_response":text}
    try:return json.loads(text[a:b+1])
    except json.JSONDecodeError as exc:return {"parse_error":str(exc),"raw_response":text}

def summarize_with_qwen(packet,*,model_name="Qwen/Qwen3-0.6B",max_new_tokens=768):
    try:
        from transformers import AutoModelForCausalLM,AutoTokenizer
    except ImportError as exc: raise ValueError("Qwen local opcional ausente; instale pensieve-timeline[llm]") from exc
    tok=AutoTokenizer.from_pretrained(model_name); model=AutoModelForCausalLM.from_pretrained(model_name,torch_dtype="auto",device_map="auto")
    messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":json.dumps(packet,ensure_ascii=False)}]
    try: prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
    except TypeError: prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    inputs=tok([prompt],return_tensors="pt").to(model.device); generated=model.generate(**inputs,max_new_tokens=max_new_tokens,do_sample=False)
    text=tok.batch_decode(generated[:,inputs.input_ids.shape[1]:],skip_special_tokens=True)[0]
    result=_json(text); result["model"]=model_name; result["evidence_event_count"]=len(packet.get("events",[])); return result
