# Deployment — duas VMs

O Pensieve possui dois perfis oficiais de VM.

| Perfil | IA | Comando principal | Uso |
|---|---|---|---|
| Forensic Core | não | `pensieve-forensic` | evidência, timeline, correlação, SQLite, export e dashboard |
| AI Analyst | GLiNER + Qwen | `pensieve-ai` | entidades, Evidence Graph, Evidence Packet v2 e reasoning |

## Arquitetura recomendada

```text
Evidência original
       |
       v
VM Forensic Core
       |
       | timeline.jsonl
       v
VM AI Analyst
       |
       +-- GLiNER
       +-- Qwen
       +-- Evidence Packet v2
```

O objetivo é evitar que a VM de IA precise receber a evidência original quando a timeline canônica já é suficiente para a análise derivada.

## VM Forensic

```bash
git clone https://github.com/Ridd1kulusC0d3r/ThePensieveProject.git
cd ThePensieveProject
sudo bash deploy/vm/forensic/bootstrap.sh
```

Analise:

```bash
pensieve-forensic /data/evidence.csv --case-id CASE-001
```

A VM não instala GLiNER, Transformers, PyTorch ou Qwen.

## VM AI

```bash
git clone https://github.com/Ridd1kulusC0d3r/ThePensieveProject.git
cd ThePensieveProject
sudo bash deploy/vm/ai/bootstrap.sh
```

GLiNER e Qwen ficam habilitados por padrão e seus snapshots são pré-carregados.

### Receber timeline da VM forense

```bash
pensieve-ai /data/CASE-001.timeline.jsonl \
  --canonical-timeline \
  --case-id CASE-001-AI
```

O modo `--canonical-timeline` lê diretamente os eventos já normalizados e evita uma segunda aplicação das regras de scoring.

### Modo direto

```bash
pensieve-ai /data/evidence.csv --case-id CASE-AI-002
```

## Dashboard

Ambas executam:

```text
pensieve-dashboard.service
127.0.0.1:8080
```

Acesso remoto recomendado:

```bash
ssh -L 8080:127.0.0.1:8080 usuario@vm
```

Depois abra `http://127.0.0.1:8080/`.

## Configuração

Arquivo persistente:

`/etc/pensieve/pensieve.env`

Na VM AI:

```text
PENSIEVE_GLINER_ENABLED=1
PENSIEVE_QWEN_ENABLED=1
PENSIEVE_GLINER_MODEL=urchade/gliner_multi-v2.1
PENSIEVE_QWEN_MODEL=Qwen/Qwen3-0.6B
PENSIEVE_GLINER_THRESHOLD=0.45
```

## Health check

```bash
pensieve-health
```

A documentação completa de provisionamento, cloud-init, outputs e atualização está em `deploy/vm/README.md`.
