"""Small self-contained web frontend for Colab and local Pensieve labs."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import threading
import uuid

from pensieve_timeline import __version__
from pensieve_timeline.environment import diagnose
from pensieve_timeline.ops import (
    DEFAULT_GLINER_MODEL,
    DEFAULT_QWEN_MODEL,
    run_ai,
    run_forensic,
)


DEFAULT_CASE_ROOT = Path("/content/pensieve-cases")
DEFAULT_UPLOAD_ROOT = Path("/content/pensieve-uploads")

_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
_EXECUTOR = ThreadPoolExecutor(max_workers=2)


def _safe_name(value: str, fallback: str = "case") -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip()).strip("-")
    return (clean or fallback)[:100]


def _safe_filename(value: str) -> str:
    name = Path(str(value or "evidence.bin")).name
    stem = _safe_name(Path(name).stem, "evidence")
    suffix = re.sub(r"[^A-Za-z0-9.]+", "", Path(name).suffix)[:12]
    return f"{stem}{suffix}"


def _case_dir(root: Path, case_id: str) -> Path:
    root = root.expanduser().resolve()
    case = (root / _safe_name(case_id)).resolve()
    if case.parent != root:
        raise ValueError("invalid case path")
    return case


def _json_file(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl_rows(path: Path, *, limit: int = 500) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def _case_summary(case: Path) -> dict:
    manifest = _json_file(case / "manifest.json", {}) or {}
    return {
        "case_id": case.name,
        "profile": manifest.get("profile", "unknown"),
        "event_count": manifest.get("event_count", 0),
        "correlation_count": manifest.get("correlation_count", 0),
        "entity_count": manifest.get("entity_count", 0),
        "claim_count": manifest.get("claim_count", 0),
        "created_at": manifest.get("created_at"),
        "gliner_enabled": manifest.get("gliner_enabled", False),
        "qwen_enabled": manifest.get("qwen_enabled", False),
    }


def _set_job(job_id: str, **updates) -> None:
    with _JOBS_LOCK:
        _JOBS.setdefault(job_id, {}).update(updates)


def _run_analysis_job(
    job_id: str,
    *,
    upload_path: Path,
    profile: str,
    case_root: Path,
    case_id: str,
    gliner_enabled: bool,
    qwen_enabled: bool,
    canonical_timeline: bool,
) -> None:
    _set_job(
        job_id,
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        message="Processando evidência...",
    )
    try:
        if profile == "ai":
            manifest = run_ai(
                upload_path,
                workspace_root=case_root,
                case_id=case_id,
                gliner_enabled=gliner_enabled,
                qwen_enabled=qwen_enabled,
                gliner_model=DEFAULT_GLINER_MODEL,
                qwen_model=DEFAULT_QWEN_MODEL,
                canonical_timeline=canonical_timeline,
            )
        else:
            manifest = run_forensic(
                upload_path,
                workspace_root=case_root,
                case_id=case_id,
            )

        _set_job(
            job_id,
            status="done",
            finished_at=datetime.now(timezone.utc).isoformat(),
            case_id=manifest["case_id"],
            manifest=manifest,
            message="Análise concluída.",
        )
    except Exception as exc:  # boundary for a user-facing job
        _set_job(
            job_id,
            status="error",
            finished_at=datetime.now(timezone.utc).isoformat(),
            error=f"{type(exc).__name__}: {exc}",
            message="A análise falhou.",
        )
    finally:
        try:
            upload_path.unlink(missing_ok=True)
        except OSError:
            pass


def _ui_html() -> str:
    return r'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Pensieve Project</title>
<style>
:root{
  --bg:#07090b;--panel:#0d1115;--panel2:#11171c;--line:#202932;
  --text:#f5f7f8;--muted:#8d98a4;--soft:#b8c2cc;--accent:#d7ff64;
  --cyan:#6ce5e8;--red:#ff7b7b;--radius:16px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
button,input,select{font:inherit}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.shell{min-height:100vh}
header{position:sticky;top:0;z-index:20;background:rgba(7,9,11,.93);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}
.top{display:flex;align-items:center;gap:22px;padding:14px 28px}
.brand{display:flex;align-items:center;gap:12px;min-width:320px}
.logo{width:42px;height:42px;border:1px solid #394550;border-radius:11px;display:grid;place-items:center;background:#f4f6f7;color:#050607;font-weight:900}
.brand strong{font-size:18px;letter-spacing:.02em}.brand small{display:block;color:var(--muted);margin-top:2px}
.nav{display:flex;gap:6px;flex:1}
.nav button{border:0;background:transparent;color:var(--muted);padding:9px 13px;border-radius:9px;cursor:pointer}
.nav button.active,.nav button:hover{color:var(--text);background:#141a20}
.statusbar{display:flex;align-items:center;gap:10px}
.pill{border:1px solid var(--line);border-radius:999px;padding:7px 11px;color:var(--soft);font-size:12px;background:#0b0f12}
.pill.ai{border-color:#3d5526;color:var(--accent)}
main{max-width:1500px;margin:auto;padding:28px}
.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:20px;margin-bottom:22px}
.heroCard,.panel{background:linear-gradient(180deg,#0d1115,#0a0d10);border:1px solid var(--line);border-radius:var(--radius)}
.heroCard{padding:30px}
.eyebrow{color:var(--muted);letter-spacing:.24em;text-transform:uppercase;font-size:11px;font-weight:700}
h1{font-size:clamp(40px,5vw,76px);line-height:.96;letter-spacing:-.055em;margin:20px 0}
.hero p{color:var(--muted);font-size:16px;line-height:1.65;max-width:830px}
.upload{padding:22px;display:flex;flex-direction:column;gap:14px}
label{font-size:12px;color:var(--muted);display:block;margin-bottom:6px}
input[type=file],input[type=text],select{width:100%;background:#090c0f;border:1px solid var(--line);color:var(--text);border-radius:10px;padding:11px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.switches{display:flex;gap:10px;flex-wrap:wrap}
.switch{display:flex;align-items:center;gap:8px;padding:9px 11px;border:1px solid var(--line);border-radius:10px;color:var(--soft);font-size:13px}
.primary{border:0;background:var(--text);color:#050607;padding:12px 14px;border-radius:10px;font-weight:800;cursor:pointer}
.primary:hover{opacity:.9}.primary:disabled{opacity:.4;cursor:not-allowed}
.job{min-height:22px;color:var(--muted);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
.card .n{font-size:32px;font-weight:800;letter-spacing:-.04em}.card .k{color:var(--muted);font-size:12px;margin-top:4px}
.casebar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:20px 0 10px}
.casebar h2{margin:0;font-size:17px}.casebar .actions{display:flex;gap:8px}
.secondary{background:#10151a;color:var(--soft);border:1px solid var(--line);padding:8px 10px;border-radius:8px;cursor:pointer;text-decoration:none;font-size:12px}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--line);margin-top:10px}
.tabs button{border:0;background:transparent;color:var(--muted);padding:13px 16px;cursor:pointer;border-bottom:2px solid transparent}
.tabs button.active{color:var(--text);border-bottom-color:var(--text)}
.view{display:none;padding:18px 0}.view.active{display:block}
.tableWrap{overflow:auto;border:1px solid var(--line);border-radius:12px;max-height:620px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{text-align:left;padding:10px 11px;border-bottom:1px solid #182028;vertical-align:top}
th{position:sticky;top:0;background:#10151a;color:#aab5c0;z-index:2}
td{color:#d6dde3}.muted{color:var(--muted)}
.claim{border:1px solid var(--line);background:var(--panel);border-radius:12px;padding:16px;margin-bottom:10px}
.claimHead{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}
.level{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--cyan)}
.support{font-size:11px;color:var(--muted)}
.cites{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}.cite{font-size:10px;border:1px solid #2b3740;border-radius:999px;padding:4px 7px;color:#b8c2cc}
pre{white-space:pre-wrap;word-break:break-word;background:#080b0e;border:1px solid var(--line);border-radius:10px;padding:14px;color:#cbd5dd;max-height:500px;overflow:auto}
.empty{border:1px dashed #26313a;border-radius:12px;padding:40px;text-align:center;color:var(--muted)}
.fileGrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}.file{border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:13px}
@media(max-width:900px){.hero{grid-template-columns:1fr}.top{flex-wrap:wrap}.brand{min-width:auto}.cards{grid-template-columns:1fr 1fr}.nav{order:3;width:100%;overflow:auto}.row{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="shell">
<header>
  <div class="top">
    <div class="brand">
      <div class="logo">Ψ</div>
      <div><strong>The Pensieve Project</strong><small class="mono">Forensic Investigation Workbench</small></div>
    </div>
    <div class="nav" id="topNav">
      <button class="active" data-tab="overview">Visão geral</button>
      <button data-tab="timeline">Timeline</button>
      <button data-tab="entities">Entidades</button>
      <button data-tab="ai">AI</button>
      <button data-tab="files">Arquivos</button>
    </div>
    <div class="statusbar">
      <span class="pill mono" id="versionPill">Pensieve</span>
      <span class="pill ai mono" id="capPill">checando...</span>
    </div>
  </div>
</header>

<main>
<section class="hero">
  <div class="heroCard">
    <div class="eyebrow mono">Evidence first · inference bounded</div>
    <h1>Observe.<br>Correlacione.<br>Explique.</h1>
    <p>Uma interface simples sobre o pipeline do Pensieve. O perfil Forensic mantém IA fora da análise. O perfil AI usa GLiNER para entidades e Qwen somente sobre o Evidence Packet v2.</p>
  </div>
  <div class="panel upload">
    <div>
      <label>Arquivo de entrada</label>
      <input id="fileInput" type="file">
    </div>
    <div class="row">
      <div>
        <label>Perfil</label>
        <select id="profile">
          <option value="forensic">Forensic Core · sem IA</option>
          <option value="ai" selected>AI Analyst · GLiNER + Qwen</option>
        </select>
      </div>
      <div>
        <label>Case ID</label>
        <input id="caseId" type="text" placeholder="CASE-001">
      </div>
    </div>
    <div class="switches" id="aiOptions">
      <label class="switch"><input id="gliner" type="checkbox" checked> GLiNER</label>
      <label class="switch"><input id="qwen" type="checkbox" checked> Qwen</label>
      <label class="switch"><input id="canonical" type="checkbox"> timeline.jsonl já canônica</label>
    </div>
    <button class="primary" id="runBtn">Executar investigação</button>
    <div class="job mono" id="jobStatus">Aguardando arquivo.</div>
  </div>
</section>

<section class="cards">
  <div class="card"><div class="n" id="eventsN">0</div><div class="k mono">EVENTOS</div></div>
  <div class="card"><div class="n" id="corrN">0</div><div class="k mono">CORRELAÇÕES</div></div>
  <div class="card"><div class="n" id="entitiesN">0</div><div class="k mono">ENTIDADES</div></div>
  <div class="card"><div class="n" id="claimsN">0</div><div class="k mono">CLAIMS AI</div></div>
</section>

<section class="casebar">
  <h2 id="caseTitle">Nenhum caso carregado</h2>
  <div class="actions">
    <a class="secondary" id="reportLink" target="_blank" style="display:none">Abrir relatório HTML</a>
    <button class="secondary" id="refreshBtn">Atualizar</button>
  </div>
</section>

<div class="tabs" id="tabs">
  <button class="active" data-tab="overview">Resumo</button>
  <button data-tab="timeline">Timeline</button>
  <button data-tab="entities">Entidades</button>
  <button data-tab="ai">AI Reasoning</button>
  <button data-tab="files">Arquivos</button>
</div>

<div id="overview" class="view active"><div class="empty">Execute uma investigação para carregar o resumo.</div></div>
<div id="timeline" class="view"><div class="empty">Timeline ainda não carregada.</div></div>
<div id="entities" class="view"><div class="empty">Entidades ainda não carregadas.</div></div>
<div id="ai" class="view"><div class="empty">AI reasoning ainda não carregado.</div></div>
<div id="files" class="view"><div class="empty">Nenhum artefato gerado.</div></div>
</main>
</div>

<script>
let currentCase = null;
let pollTimer = null;

const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function activate(tab){
  document.querySelectorAll('[data-tab]').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === tab));
}
document.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => activate(b.dataset.tab)));

$('profile').addEventListener('change', () => {
  const ai = $('profile').value === 'ai';
  $('aiOptions').style.opacity = ai ? '1' : '.35';
  $('aiOptions').style.pointerEvents = ai ? 'auto' : 'none';
});

async function api(url, opts){
  const r = await fetch(url, opts);
  if(!r.ok){
    let msg = await r.text();
    try { msg = JSON.parse(msg).detail || msg; } catch(e){}
    throw new Error(msg);
  }
  return r.json();
}

async function loadConfig(){
  try{
    const c = await api('/api/config');
    $('versionPill').textContent = 'v' + c.version;
    const caps = c.capabilities.optional_capabilities || {};
    $('capPill').textContent = (caps.gliner ? 'GLiNER ' : '') + (caps.qwen_transformers ? '+ Qwen' : 'Core');
  }catch(e){ $('capPill').textContent='offline'; }
}

$('runBtn').addEventListener('click', async () => {
  const file = $('fileInput').files[0];
  if(!file){ $('jobStatus').textContent = 'Selecione um arquivo.'; return; }

  const fd = new FormData();
  fd.append('file', file);
  fd.append('profile', $('profile').value);
  fd.append('case_id', $('caseId').value);
  fd.append('gliner', $('gliner').checked);
  fd.append('qwen', $('qwen').checked);
  fd.append('canonical_timeline', $('canonical').checked);

  $('runBtn').disabled = true;
  $('jobStatus').textContent = 'Enviando arquivo...';

  try{
    const job = await api('/api/analyze', {method:'POST', body:fd});
    $('jobStatus').textContent = 'Job ' + job.job_id + ' iniciado.';
    pollJob(job.job_id);
  }catch(e){
    $('jobStatus').textContent = 'Erro: ' + e.message;
    $('runBtn').disabled = false;
  }
});

async function pollJob(jobId){
  clearTimeout(pollTimer);
  try{
    const j = await api('/api/jobs/' + encodeURIComponent(jobId));
    $('jobStatus').textContent = (j.status || '') + ' · ' + (j.message || '');
    if(j.status === 'done'){
      $('runBtn').disabled = false;
      currentCase = j.case_id;
      await loadCase(currentCase);
      return;
    }
    if(j.status === 'error'){
      $('runBtn').disabled = false;
      $('jobStatus').textContent = 'Falhou: ' + (j.error || 'erro desconhecido');
      return;
    }
  }catch(e){
    $('jobStatus').textContent='Erro consultando job: ' + e.message;
  }
  pollTimer = setTimeout(() => pollJob(jobId), 1200);
}

async function loadCase(caseId){
  currentCase = caseId;
  const [m,t,e,i,f] = await Promise.all([
    api('/api/cases/'+encodeURIComponent(caseId)+'/manifest'),
    api('/api/cases/'+encodeURIComponent(caseId)+'/timeline?limit=500'),
    api('/api/cases/'+encodeURIComponent(caseId)+'/entities?limit=500'),
    api('/api/cases/'+encodeURIComponent(caseId)+'/intelligence'),
    api('/api/cases/'+encodeURIComponent(caseId)+'/files')
  ]);

  $('caseTitle').textContent = caseId + ' · ' + (m.profile || 'unknown');
  $('eventsN').textContent = m.event_count || 0;
  $('corrN').textContent = m.correlation_count || 0;
  $('entitiesN').textContent = m.entity_count || 0;
  $('claimsN').textContent = m.claim_count || 0;
  $('reportLink').href = '/cases/'+encodeURIComponent(caseId)+'/report';
  $('reportLink').style.display = 'inline-block';

  renderOverview(m);
  renderTimeline(t.rows || []);
  renderEntities(e.rows || []);
  renderAI(i);
  renderFiles(f.files || []);
}

function renderOverview(m){
  $('overview').innerHTML = `
    <div class="panel" style="padding:20px">
      <div class="eyebrow mono">CASE MANIFEST</div>
      <h3 style="font-size:28px;margin:12px 0 8px">${esc(m.case_id || currentCase)}</h3>
      <p class="muted">Perfil <b>${esc(m.profile)}</b> · input <b>${esc(m.input_mode || 'evidence')}</b> · GLiNER <b>${m.gliner_enabled?'ON':'OFF'}</b> · Qwen <b>${m.qwen_enabled?'ON':'OFF'}</b></p>
      <pre>${esc(JSON.stringify(m,null,2))}</pre>
    </div>`;
}

function renderTimeline(rows){
  if(!rows.length){ $('timeline').innerHTML='<div class="empty">Sem eventos.</div>'; return; }
  const body = rows.map(r => `<tr>
    <td class="mono">${esc(r.timestamp)}</td>
    <td>${esc(r.artifact_type)}</td>
    <td>${esc(r.host)}</td>
    <td>${esc(r.user)}</td>
    <td class="mono">${esc(r.provider || '')}</td>
    <td class="mono">${esc(r.event_code || '')}</td>
    <td>${esc(r.risk_score)}</td>
    <td>${esc(r.message)}</td>
    <td class="mono">${esc(r.event_id)}</td>
  </tr>`).join('');
  $('timeline').innerHTML = `<div class="tableWrap"><table>
    <thead><tr><th>UTC</th><th>Artefato</th><th>Host</th><th>Usuário</th><th>Provider</th><th>ID</th><th>Risk</th><th>Mensagem</th><th>event_id</th></tr></thead>
    <tbody>${body}</tbody></table></div>`;
}

function renderEntities(rows){
  if(!rows.length){ $('entities').innerHTML='<div class="empty">Nenhuma entidade processada. No perfil Forensic isso é esperado.</div>'; return; }
  const body = rows.map(r => `<tr>
    <td>${esc(r.label)}</td><td>${esc(r.text)}</td><td>${esc(r.normalized_value)}</td>
    <td>${esc(r.score)}</td><td class="mono">${esc(r.extractor)}</td>
    <td>${esc((r.corroborated_by||[]).join(', '))}</td><td class="mono">${esc(r.event_id)}</td>
  </tr>`).join('');
  $('entities').innerHTML = `<div class="tableWrap"><table>
    <thead><tr><th>Tipo</th><th>Observado</th><th>Normalizado</th><th>Score</th><th>Extrator</th><th>Corroborado por</th><th>event_id</th></tr></thead>
    <tbody>${body}</tbody></table></div>`;
}

function renderAI(data){
  if(!data || !data.claims){
    $('ai').innerHTML='<div class="empty">Sem relatório de IA. No perfil Forensic ou com Qwen desligado isso é esperado.</div>'; return;
  }
  const claims = data.claims.map(c => `<div class="claim">
    <div class="claimHead"><span class="level mono">${esc(c.level)}</span><span class="support mono">${esc(c.calibrated_support?.label || '')} · ${esc(c.calibrated_support?.score ?? '')}</span></div>
    <div style="font-size:17px;font-weight:700">${esc(c.statement)}</div>
    <p class="muted">${esc(c.rationale)}</p>
    ${c.alternatives?.length ? '<div class="muted"><b>Alternativas:</b> '+c.alternatives.map(esc).join(' · ')+'</div>' : ''}
    <div class="cites">${(c.evidence_event_ids||[]).map(x=>'<span class="cite mono">'+esc(x)+'</span>').join('')}</div>
  </div>`).join('');
  $('ai').innerHTML = `<div class="panel" style="padding:20px"><div class="eyebrow mono">AI REASONING REPORT</div><h3>${esc(data.summary||'')}</h3><p class="muted">Claims citam apenas event_id presentes no Evidence Packet. Support não é probabilidade de verdade.</p>${claims}</div>`;
}

function renderFiles(files){
  if(!files.length){ $('files').innerHTML='<div class="empty">Nenhum arquivo.</div>'; return; }
  $('files').innerHTML='<div class="fileGrid">'+files.map(f => `<div class="file"><div class="mono">${esc(f.name)}</div><div class="muted" style="margin-top:6px">${esc(f.size_bytes)} bytes</div></div>`).join('')+'</div>';
}

$('refreshBtn').addEventListener('click', () => currentCase && loadCase(currentCase));
loadConfig();
</script>
</body></html>'''


def create_app(
    *,
    case_root: Path = DEFAULT_CASE_ROOT,
    upload_root: Path = DEFAULT_UPLOAD_ROOT,
):
    try:
        from fastapi import FastAPI, File, Form, HTTPException, UploadFile
        from fastapi.responses import FileResponse, HTMLResponse
    except ImportError as exc:
        raise RuntimeError(
            "Frontend opcional ausente; instale pensieve-timeline[ui]"
        ) from exc

    case_root = case_root.expanduser().resolve()
    upload_root = upload_root.expanduser().resolve()
    case_root.mkdir(parents=True, exist_ok=True)
    upload_root.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="The Pensieve Project",
        version=__version__,
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/", response_class=HTMLResponse)
    def home():
        return _ui_html()

    @app.get("/api/config")
    def config():
        return {
            "version": __version__,
            "defaults": {
                "profile": "ai",
                "gliner": True,
                "qwen": True,
                "gliner_model": DEFAULT_GLINER_MODEL,
                "qwen_model": DEFAULT_QWEN_MODEL,
            },
            "capabilities": diagnose(),
        }

    @app.get("/api/cases")
    def cases():
        items = []
        for path in sorted(case_root.iterdir(), reverse=True):
            if path.is_dir() and (path / "manifest.json").exists():
                items.append(_case_summary(path))
        return {"cases": items}

    @app.post("/api/analyze")
    async def analyze(
        file: UploadFile = File(...),
        profile: str = Form("ai"),
        case_id: str = Form(""),
        gliner: bool = Form(True),
        qwen: bool = Form(True),
        canonical_timeline: bool = Form(False),
    ):
        profile = profile.casefold().strip()
        if profile not in {"forensic", "ai"}:
            raise HTTPException(status_code=400, detail="profile must be forensic or ai")

        resolved_case = _safe_name(
            case_id,
            fallback="case-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        )
        final_case = resolved_case
        if _case_dir(case_root, final_case).exists():
            final_case = f"{resolved_case}-{uuid.uuid4().hex[:6]}"

        upload_name = f"{uuid.uuid4().hex}-{_safe_filename(file.filename or 'evidence.bin')}"
        upload_path = (upload_root / upload_name).resolve()
        if upload_path.parent != upload_root:
            raise HTTPException(status_code=400, detail="invalid upload path")

        try:
            with upload_path.open("wb") as handle:
                while chunk := await file.read(1024 * 1024):
                    handle.write(chunk)
        finally:
            await file.close()

        job_id = uuid.uuid4().hex[:12]
        _set_job(
            job_id,
            status="queued",
            profile=profile,
            case_id=final_case,
            filename=file.filename,
            message="Na fila.",
        )
        _EXECUTOR.submit(
            _run_analysis_job,
            job_id,
            upload_path=upload_path,
            profile=profile,
            case_root=case_root,
            case_id=final_case,
            gliner_enabled=bool(gliner) if profile == "ai" else False,
            qwen_enabled=bool(qwen) if profile == "ai" else False,
            canonical_timeline=bool(canonical_timeline) if profile == "ai" else False,
        )
        return {"job_id": job_id, "case_id": final_case}

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        with _JOBS_LOCK:
            value = dict(_JOBS.get(job_id, {}))
        if not value:
            raise HTTPException(status_code=404, detail="job not found")
        return value

    def require_case(case_id: str) -> Path:
        path = _case_dir(case_root, case_id)
        if not path.is_dir():
            raise HTTPException(status_code=404, detail="case not found")
        return path

    @app.get("/api/cases/{case_id}/manifest")
    def manifest(case_id: str):
        case = require_case(case_id)
        value = _json_file(case / "manifest.json")
        if not value:
            raise HTTPException(status_code=404, detail="manifest not found")
        return value

    @app.get("/api/cases/{case_id}/timeline")
    def timeline(case_id: str, limit: int = 500):
        case = require_case(case_id)
        return {
            "rows": _jsonl_rows(
                case / "timeline.jsonl",
                limit=max(1, min(limit, 2000)),
            )
        }

    @app.get("/api/cases/{case_id}/entities")
    def entities(case_id: str, limit: int = 500):
        case = require_case(case_id)
        return {
            "rows": _jsonl_rows(
                case / "entities.jsonl",
                limit=max(1, min(limit, 2000)),
            )
        }

    @app.get("/api/cases/{case_id}/intelligence")
    def intelligence(case_id: str):
        case = require_case(case_id)
        return _json_file(case / "intelligence.json", {}) or {}

    @app.get("/api/cases/{case_id}/files")
    def files(case_id: str):
        case = require_case(case_id)
        return {
            "files": [
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                }
                for path in sorted(case.iterdir())
                if path.is_file()
            ]
        }

    @app.get("/cases/{case_id}/report")
    def report(case_id: str):
        case = require_case(case_id)
        path = case / "report.html"
        if not path.exists():
            raise HTTPException(status_code=404, detail="report not found")
        return FileResponse(path, media_type="text/html")

    return app


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pensieve-web",
        description="Small Pensieve frontend for Colab/local labs.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("--case-root", type=Path, default=DEFAULT_CASE_ROOT)
    parser.add_argument("--upload-root", type=Path, default=DEFAULT_UPLOAD_ROOT)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "Frontend opcional ausente; instale pensieve-timeline[ui]"
        ) from exc

    app = create_app(
        case_root=args.case_root,
        upload_root=args.upload_root,
    )
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
