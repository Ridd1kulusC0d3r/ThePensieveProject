# The Pensieve Project

[![CI](https://github.com/Ridd1kulusC0d3r/ThePensieveProject/actions/workflows/ci.yml/badge.svg)](https://github.com/Ridd1kulusC0d3r/ThePensieveProject/actions/workflows/ci.yml)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Ridd1kulusC0d3r/ThePensieveProject/blob/main/colab/pensieve_dfir_osint.ipynb)


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
- optional local Qwen analysis over an evidence packet, not raw case data;
- Google Colab path for labs and demonstrations;
- Academy for first-time investigators and machine-readable guidance for AI tutors.

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

Qwen is also opt-in and receives a bounded Evidence Packet with event IDs:

```bash
pensieve-timeline llm-summary timeline.jsonl entities.jsonl \
  --model Qwen/Qwen3-0.6B -o intelligence.json
```

## Google Colab

Open `colab/pensieve_dfir_osint.ipynb` in Google Colab. The default route installs only the project core. GLiNER and Qwen are toggles in later cells so the same notebook works on free CPU sessions.

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
         Evidence Packet ---> optional local Qwen
```

OSINT-derived data lives separately from the canonical event table so models can be re-run without mutating evidence. Equivalent regex/GLiNER detections are deduplicated while preserving extractor provenance.

## Validation

Core tests run on Linux, Windows and macOS. Heavy forensic backends are classified as LAB capabilities and their integration workflows are manual-only until representative fixtures and cross-tool comparisons are stable. See [`docs/CAPABILITY_MATRIX.md`](docs/CAPABILITY_MATRIX.md).

Local v0.3 development validation before publication: **19 tests passed** and the synthetic end-to-end lab produced 3 events, 6 entity mentions, a 6-node/4-edge graph, SQLite case data and a standalone HTML report.

## Datasets and references

See `datasets/catalog.json` and the documentation. The catalog starts with NIST CFReDS, OTRF Security-Datasets, EVTX-ATTACK-SAMPLES, ForensicArtifacts, Plaso and Dissect. Dataset licensing and redistribution terms must be checked per source.

## Licensing

Pensieve source code is MIT. Optional third-party backends keep their own licenses. In particular, Dissect is an optional integration boundary and its license must be respected by downstream users.

## Status

**v0.3.0-dev2**: research/development release. It is suitable for labs, parser validation, teaching and controlled analysis. It is not yet a substitute for independently validated forensic tooling in legal proceedings.
