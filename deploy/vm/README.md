# Pensieve dual-VM reference deployment

The project ships two independent Ubuntu VM profiles.

## Architecture

```text
               RAW EVIDENCE
                    |
                    v
        +-------------------------+
        | VM 1 — FORENSIC CORE    |
        |                         |
        | no GLiNER               |
        | no Qwen                 |
        | timeline                |
        | correlation             |
        | SQLite                  |
        | Timesketch export       |
        | HTML dashboard          |
        +------------+------------+
                     |
                     | preferred handoff:
                     | timeline.jsonl
                     v
        +-------------------------+
        | VM 2 — AI ANALYST       |
        |                         |
        | GLiNER = ON             |
        | Qwen = ON               |
        | EntityMention           |
        | Evidence Graph          |
        | Evidence Packet v2      |
        | validated AI reasoning  |
        | HTML dashboard          |
        +-------------------------+
```

The recommended design keeps original evidence on the forensic VM and sends only the canonical timeline to the AI VM.

## Reference OS

The bootstrap scripts target a current Ubuntu Server installation with systemd and Python 3.10+.

They are intentionally ordinary shell scripts rather than a provider-specific image, so the same profile can be used on local virtualization or common cloud VM providers.

---

# VM 1 — Forensic Core

No AI packages are installed.

## Bootstrap

Clone the repository and run:

```bash
sudo bash deploy/vm/forensic/bootstrap.sh
```

Or use `deploy/vm/forensic/cloud-init.yaml` as VM user-data.

## Run a case

```bash
pensieve-forensic /data/evidence.csv \
  --case-id CASE-001
```

Output:

```text
/srv/pensieve/cases/CASE-001/
├── manifest.json
├── timeline.jsonl
├── timeline.csv
├── timesketch.jsonl
├── correlations.jsonl
├── case.db
└── report.html
```

The manifest explicitly records:

```json
{
  "profile": "forensic",
  "ai_enabled": false,
  "gliner_enabled": false,
  "qwen_enabled": false
}
```

## Dashboard

The bootstrap enables a local systemd service:

```bash
systemctl status pensieve-dashboard
```

It listens only on:

```text
127.0.0.1:8080
```

For a remote VM:

```bash
ssh -L 8080:127.0.0.1:8080 user@FORENSIC_VM
```

Then open:

```text
http://127.0.0.1:8080/
```

Select the case directory and open `report.html`.

---

# VM 2 — AI Analyst

This profile installs:

- Pensieve core;
- GLiNER;
- Transformers;
- PyTorch;
- Accelerate;
- Qwen support.

Default models:

```text
GLiNER: urchade/gliner_multi-v2.1
Qwen:   Qwen/Qwen3-0.6B
```

Both are enabled by default.

## Bootstrap

```bash
sudo bash deploy/vm/ai/bootstrap.sh
```

Or use:

`deploy/vm/ai/cloud-init.yaml`

By default the bootstrap prefetches both model snapshots into:

```text
/var/cache/pensieve/models
```

Disable prefetch only when building an image without network access:

```bash
sudo PENSIEVE_PREFETCH_MODELS=0 \
  bash deploy/vm/ai/bootstrap.sh
```

## Recommended handoff from the forensic VM

On VM 1:

```bash
pensieve-forensic /data/evidence.csv --case-id CASE-001
```

Copy only the canonical timeline:

```bash
scp /srv/pensieve/cases/CASE-001/timeline.jsonl \
  user@AI_VM:/data/CASE-001.timeline.jsonl
```

On VM 2:

```bash
pensieve-ai /data/CASE-001.timeline.jsonl \
  --canonical-timeline \
  --case-id CASE-001-AI
```

GLiNER and Qwen run automatically.

Output:

```text
/srv/pensieve/cases/CASE-001-AI/
├── manifest.json
├── timeline.jsonl
├── timeline.csv
├── timesketch.jsonl
├── correlations.jsonl
├── entities.jsonl
├── evidence-graph.json
├── evidence-packet.json
├── intelligence.json
├── case.db
└── report.html
```

## Direct evidence mode

The AI VM can also ingest a supported input directly:

```bash
pensieve-ai /data/evidence.csv --case-id CASE-AI-002
```

This is useful for labs. For sensitive investigations, canonical-timeline handoff is the recommended boundary.

## Disable a model for one run

Although the VM defaults to both models enabled:

```bash
pensieve-ai timeline.jsonl \
  --canonical-timeline \
  --no-qwen \
  --case-id ENTITY-ONLY
```

or:

```bash
pensieve-ai timeline.jsonl \
  --canonical-timeline \
  --no-gliner \
  --case-id QWEN-WITH-DETERMINISTIC-ENTITIES
```

## Persistent configuration

Edit:

```text
/etc/pensieve/pensieve.env
```

AI defaults:

```text
PENSIEVE_GLINER_ENABLED=1
PENSIEVE_QWEN_ENABLED=1
PENSIEVE_GLINER_MODEL=urchade/gliner_multi-v2.1
PENSIEVE_QWEN_MODEL=Qwen/Qwen3-0.6B
PENSIEVE_GLINER_THRESHOLD=0.45
```

## Health check

Both VMs install:

```bash
pensieve-health
```

It prints the Pensieve version, optional capabilities and dashboard service status.

---

# Updating

Both profiles keep the repository at:

```text
/opt/pensieve/app
```

Re-running the profile bootstrap updates the checkout and Python environment.

For reproducible deployments you can pin a tag, branch or commit before bootstrap:

```bash
sudo PENSIEVE_REF=v0.3.0 \
  bash deploy/vm/forensic/bootstrap.sh
```

The same variable works on the AI profile.

---

# Trust boundary

Recommended:

```text
VM Forensic
  owns original evidence
        |
        | canonical timeline only
        v
VM AI
  owns derived ML/LLM analysis
```

This does not magically make model output trustworthy. It makes the boundary visible and auditable, which is considerably more useful.
