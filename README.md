# The Pensieve Project

[![CI](https://github.com/Ridd1kulusC0d3r/ThePensieveProject/actions/workflows/ci.yml/badge.svg)](https://github.com/Ridd1kulusC0d3r/ThePensieveProject/actions/workflows/ci.yml)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ridd1kulusC0d3r/ThePensieveProject/blob/main/colab/first_investigation.ipynb)


> Cross-platform DFIR timeline, forensic reasoning and evidence-bounded OSINT in Python.

The Pensieve Project turns heterogeneous forensic evidence into a canonical timeline and keeps a hard boundary between **evidence**, **correlation**, **inference** and **hypothesis**.

## Why this is not just another Timeline Explorer clone

- lightweight Python core: CSV, TSV, JSONL, SQLite and HTML use the standard library;
- lightweight default ingestion for CSV/TSV/JSONL;
- EVTX, Registry/AmCache and disk-image parsers kept behind the explicit `--extended-parsers` LAB gate;
- explainable temporal correlation and transparent triage scores;
- deterministic IOC/entity extraction before ML;
- canonical entity normalization, evidence hashes and multi-extractor deduplication;
- optional multilingual GLiNER zero-shot NER grounded to source-text offsets;
- Evidence Packet v2 with per-event and packet SHA-256 integrity;
- optional local Qwen reasoning with mandatory `event_id` citations and fail-closed validation;
- transparent calibrated support that never treats model confidence as probability;
- Google Colab **First Investigation** with selectable DFIR, OSINT and DFIR + OSINT tracks;
- progressive Academy missions, synthetic micro-datasets and machine-readable progress for human/AI tutors.

## Epistemic contract

```text
Event != interpretation
Correlation != causation
Extracted entity != verified identity
Anomaly != malicious activity
Hypothesis != conclusion
```

The graph means co-occurrence unless a stronger relation is supported by evidence.

## Install

```bash
python -m pip install .
pensieve-timeline doctor
```

Optional capabilities are independent. Heavy forensic parsers are installed separately and are not enabled by default:

```bash
python -m pip install '.[evtx]'
python -m pip install '.[registry]'
python -m pip install '.[dissect]'
python -m pip install '.[osint]'      # GLiNER
python -m pip install '.[llm]'        # Qwen / Transformers
python -m pip install '.[ml]'         # Isolation Forest
python -m pip install '.[knowledge]'  # ForensicArtifacts YAML
```

## Five-minute lab

```bash
pensieve-timeline ingest examples/lab02/hybrid-osint.csv -o timeline.jsonl --sqlite case.db
pensieve-timeline entities timeline.jsonl -o entities.jsonl
pensieve-timeline graph entities.jsonl -o entity-graph.json
pensieve-timeline analyze timeline.jsonl -o analysis.jsonl
pensieve-timeline report timeline.jsonl --entities entities.jsonl -o report.html
```

The deterministic entity layer extracts text already present in evidence. GLiNER is opt-in:

```bash
pensieve-timeline entities timeline.jsonl --gliner \
  --labels person organization "phone number" email domain "social media handle" \
  -o entities-gliner.jsonl
```

For EVTX, Registry or disk-image ingestion, explicitly enable the LAB registry after installing the matching extra:

```bash
pensieve-timeline ingest sample.evtx --extended-parsers -o timeline.jsonl
```

Qwen is also opt-in. Audit the exact model input first:

```bash
pensieve-timeline evidence-packet timeline.jsonl \
  --entities entities.jsonl -o evidence-packet.json
```

Then run evidence-bounded reasoning:

```bash
pensieve-timeline reason timeline.jsonl entities.jsonl \
  --model Qwen/Qwen3-0.6B \
  --packet-output evidence-packet.json \
  -o intelligence.json
```

Every claim must cite valid `event_id` values from the packet. Hypotheses require alternatives, and model self-confidence is stored separately from Pensieve's structural support calibration.

## Dual-VM deployment

Pensieve now ships two reference Ubuntu VM profiles:

```text
VM 1 — Forensic Core
  raw evidence
  timeline
  correlation
  SQLite
  Timesketch export
  HTML dashboard
  GLiNER = not installed
  Qwen   = not installed

             timeline.jsonl
                   |
                   v

VM 2 — AI Analyst
  GLiNER = enabled by default
  Qwen   = enabled by default
  EntityMention
  Evidence Graph
  Evidence Packet v2
  validated AI reasoning
  HTML dashboard
```

Provision:

```bash
sudo bash deploy/vm/forensic/bootstrap.sh
sudo bash deploy/vm/ai/bootstrap.sh
```

Run:

```bash
pensieve-forensic /data/evidence.csv --case-id CASE-001

pensieve-ai /data/CASE-001.timeline.jsonl \
  --canonical-timeline \
  --case-id CASE-001-AI
```

The recommended trust boundary keeps original evidence on the forensic VM and hands only the canonical timeline to the AI VM. Both profiles serve case reports locally on `127.0.0.1:8080`.

See `deploy/vm/README.md` and `docs/deployment-vms.md`.

## Colab frontend

A lightweight web workbench is available directly inside Google Colab:

```text
colab/pensieve_frontend.ipynb
```

It serves the Pensieve UI on port `3000` and lets you:

- upload evidence;
- choose **Forensic Core** or **AI Analyst**;
- inspect timeline, entities, AI reasoning and generated files;
- keep GLiNER + Qwen enabled by default in AI mode;
- hand a canonical `timeline.jsonl` from the forensic VM to the AI pipeline without re-ingestion.

Launch manually:

```bash
python -m pip install -e '.[ui,osint,llm]'
pensieve-web --host 0.0.0.0 --port 3000
```

Then expose the kernel port through Colab. See `docs/colab-frontend.md`.

## Google Colab — First Investigation

Open `colab/first_investigation.ipynb` or use the badge at the top.

Choose one track:

```python
TRACK = "DFIR"    # timeline + triage + correlation
TRACK = "OSINT"   # entities + normalization + co-occurrence graph
TRACK = "HYBRID"  # DFIR + OSINT + Evidence Packet v2
```

All three start with the same core: environment check, SHA-256, ingestion and provenance. GLiNER and Qwen are disabled by default so the first investigation remains usable on a normal Colab CPU runtime.

The notebook produces `academy-progress.json` and a ZIP of the workspace so the investigation can be resumed or reviewed.

## Academy learning paths

The Academy now has a shared core plus three progressive tracks:

```text
C00 Orientation
  ↓
C01 Preserve + hash
  ↓
C02 Canonical timeline
  ├── DFIR  → D01 triage → D02 correlation → D03 competing hypothesis
  ├── OSINT → O01 entities → O02 graph → O03 optional GLiNER
  └── HYBRID → H01 evidence graph → H02 packet → H03 optional Qwen → H04 capstone
```

Small synthetic datasets live in `examples/first-investigation/`. The human curriculum is under `docs/academy/`, while `academy/catalog.json` and `academy/ai-manifest.json` expose the same structure to AI tutors.

## Architecture

```text
Evidence / logs / disk targets
        |
        v
Parser + Adapter Registry
        |
        v
Canonical ForensicEvent  ---> hash/provenance
        |
        +--> correlation ---> Case DB
        +--> triage -------> findings
        +--> dashboard ----> local HTML
        |
        +--> deterministic entities
               |
               +--> optional GLiNER
               |
               v
          EntityMention ---> co-occurrence graph
               |
               v
      Evidence Packet v2 ---> optional local Qwen
               |                     |
               |                     v
               +------------> strict citation validator
                                      |
                                      v
                             calibrated AI report
```

OSINT-derived data lives separately from the canonical event table so models can be re-run without mutating evidence. Equivalent regex/GLiNER detections are deduplicated while preserving extractor provenance.

## Validation

Core tests run on Linux, Windows and macOS. Heavy forensic backends are classified as LAB capabilities and their integration workflows are manual-only until representative fixtures and cross-tool comparisons are stable. See [`docs/CAPABILITY_MATRIX.md`](docs/CAPABILITY_MATRIX.md).

CI is the validation authority for the current branch. Core, OSINT and AI-reasoning contracts are tested without requiring model downloads; heavyweight model/backend integrations remain optional.

## Datasets and references

See `datasets/catalog.json` and the documentation. The catalog starts with NIST CFReDS, OTRF Security-Datasets, EVTX-ATTACK-SAMPLES, ForensicArtifacts, Plaso and Dissect. Dataset licensing and redistribution terms must be checked per source.

## Licensing

Pensieve source code is MIT. Optional third-party backends keep their own licenses. In particular, Dissect is an optional integration boundary and its license must be respected by downstream users.

## Status

**v0.3.0-dev7**: research/development release. It is suitable for labs, parser validation, teaching and controlled analysis. It is not yet a substitute for independently validated forensic tooling in legal proceedings.


## AI reasoning contracts

Machine-readable contracts are published in:

- `schemas/evidence-packet-v2.schema.json`
- `schemas/ai-reasoning-payload-v2.schema.json`

See `docs/ai-reasoning.md` for the evidence immutability and confidence-calibration model.
