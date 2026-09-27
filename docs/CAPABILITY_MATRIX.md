# Capability Matrix

Pensieve separates capabilities by validation state so an experimental backend cannot block the stable analysis path.

## GREEN — default path

These capabilities are expected to work without optional forensic dependencies:

- CSV / TSV / JSONL ingestion
- canonical `ForensicEvent`
- timestamp normalization and provenance
- SHA-256 evidence fingerprinting
- explainable triage scoring
- temporal/entity correlation
- SQLite case storage
- local HTML report
- deterministic evidence-bound OSINT extraction
- JSONL / CSV / Timesketch-style export

The default CLI registry contains only lightweight parsers.

## YELLOW — opt-in research capability

These features are useful but remain optional because they add models, larger dependencies or extra validation requirements:

- GLiNER zero-shot NER
- Qwen / Transformers evidence-packet summarization
- Isolation Forest
- ForensicArtifacts knowledge indexing

Requirements:

1. preserve source text or event IDs;
2. never mutate canonical evidence;
3. distinguish extracted entity from verified identity;
4. keep model output separate from investigator conclusions.

## RED / LAB — isolated forensic backend validation

These capabilities stay behind `--extended-parsers` and isolated integration workflows:

- EVTX via python-evtx — real public EVTX fixture validated; independent cross-parser comparison still pending
- Registry / AmCache via regipy
- MFT / USN / Prefetch / ShimCache and disk images via Dissect
- E01 / VMDK / VHD / VHDX / RAW — E01/EWF container opening is regression-tested; full filesystem/artifact extraction remains unvalidated
- large public corpus downloads

### Alternatives

| Problem | Primary alternative | Secondary alternative |
|---|---|---|
| EVTX parsing | Dissect or python-evtx adapter | Plaso comparison |
| NTFS MFT / USN | Dissect Target | Plaso/log2timeline |
| Registry / AmCache | Dissect Target or regipy | Plaso |
| Prefetch / ShimCache | Dissect Target | Plaso |
| E01/VMDK/VHDX | Dissect Target | Plaso storage/media stack |
| corpus validation | small pinned fixtures | full corpus manual/scheduled lab |

## Promotion rule

A RED capability becomes YELLOW or GREEN only after:

1. representative public/synthetic fixtures are pinned;
2. parsing succeeds deterministically;
3. normalized output is compared with documented ground truth or an independent implementation;
4. failures produce explicit errors rather than silent partial output;
5. the capability has tests that do not require unrelated modules.

Importing a package successfully is not validation.

## Current validation evidence

| Capability | Evidence | Status boundary |
|---|---|---|
| python-evtx | pinned public EVTX, fixed SHA-256, 7 canonical events / Event IDs 1 and 10 | parser path validated; cross-parser equivalence pending |
| Dissect E01/EWF | official `small.E01` fixture, fixed SHA-256, expected logical payload | container + Pensieve routing validated; Windows filesystem/artifact extraction pending |

The matrix records the **narrowest claim actually demonstrated by CI**.
