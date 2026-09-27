"""Dependency-free interactive HTML report."""
from collections import Counter
from html import escape

def build_html(events, output, entities=()):
    items=list(events); mentions=list(entities)
    artifacts=Counter(e.artifact_type or "(sem tipo)" for e in items)
    labels=Counter(m.label for m in mentions)
    options="".join(f"<option value='{escape(a,quote=True)}'>{escape(a)}</option>" for a in sorted(artifacts))
    rows=[]
    for e in items:
        search=" ".join(str(v or "") for v in [e.timestamp.isoformat(),e.host,e.user,e.event_code,e.artifact_type,e.message,*e.tags]).lower()
        rows.append("<tr data-search='{}' data-artifact='{}' data-risk='{}'><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            escape(search,quote=True),escape(e.artifact_type,quote=True),e.risk_score,
            escape(e.timestamp.isoformat()),escape(e.artifact_type),escape(e.host or ""),escape(e.user or ""),
            escape(e.event_code or ""),e.risk_score,escape(", ".join(e.tags)),escape(e.message)))
    entity_rows=["<tr><td>{}</td><td>{}</td><td>{:.3f}</td><td>{}</td><td>{}</td></tr>".format(
        escape(m.label),escape(m.text),m.score,escape(m.extractor),escape(m.event_id)) for m in mentions]
    html=f"""<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Pensieve Report</title>
<style>body{{font-family:system-ui;margin:0;background:#0d1117;color:#e6edf3}}main{{max-width:1500px;margin:auto;padding:24px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:16px}}.controls{{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px;margin:18px 0}}input,select{{padding:12px;background:#161b22;color:#e6edf3;border:1px solid #30363d;border-radius:8px}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:8px;border-bottom:1px solid #30363d;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#161b22}}.wrap{{overflow:auto;max-height:68vh}}.muted,small{{color:#8b949e}}@media(max-width:800px){{.controls{{grid-template-columns:1fr}}}}</style></head>
<body><main><h1>The Pensieve Project</h1><p class='muted'>Timeline + forensic reasoning + evidence-bounded OSINT. Score e anomalia são triagem, não veredito.</p>
<div class='cards'><div class='card'><b>Eventos</b><div>{len(items)}</div></div><div class='card'><b>Artefatos</b><div>{len(artifacts)}</div></div><div class='card'><b>Entidades</b><div>{len(mentions)}<br><small>{", ".join(f"{escape(k)} ({v})" for k,v in labels.most_common(8)) or "não processado"}</small></div></div></div>
<div class='controls'><input id='q' placeholder='Filtrar eventos'><select id='artifact'><option value=''>Todos os artefatos</option>{options}</select><select id='risk'><option value='0'>Risco ≥ 0</option><option value='10'>Risco ≥ 10</option><option value='25'>Risco ≥ 25</option><option value='50'>Risco ≥ 50</option></select></div>
<div class='wrap'><table><thead><tr><th>UTC</th><th>Artefato</th><th>Host</th><th>Usuário</th><th>Event ID</th><th>Risco</th><th>Tags</th><th>Mensagem</th></tr></thead><tbody id='events'>{"".join(rows)}</tbody></table></div>
<h2>Entidades extraídas</h2><p class='muted'>Trecho encontrado na evidência não é identidade verificada.</p><div class='wrap'><table><thead><tr><th>Tipo</th><th>Valor</th><th>Score</th><th>Extrator</th><th>Event ID</th></tr></thead><tbody>{"".join(entity_rows) or "<tr><td colspan=5>Nenhuma entidade.</td></tr>"}</tbody></table></div>
<script>const q=document.getElementById('q'),a=document.getElementById('artifact'),r=document.getElementById('risk');function apply(){{const v=q.value.toLowerCase(),art=a.value,min=Number(r.value);document.querySelectorAll('#events tr').forEach(x=>{{x.style.display=x.dataset.search.includes(v)&&(!art||x.dataset.artifact===art)&&Number(x.dataset.risk)>=min?'':'none'}})}}[q,a,r].forEach(x=>x.addEventListener('input',apply));</script></main></body></html>"""
    output.write_text(html,encoding="utf-8")
