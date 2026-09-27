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

These capabilities stay behind `--extended-parsers` and manual integration workflows:

- EVTX via python-evtx
- Registry / AmCache via regipy
- MFT / USN / Prefetch / ShimCache and disk images via Dissect
- E01 / VMDK / VHD / VHDX / RAW
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
