# Trilha DFIR + OSINT — investigação integrada

Dataset: `examples/first-investigation/hybrid.csv`

Esta é a trilha de convergência. Ela mantém eventos forenses e entidades OSINT em camadas distintas e conecta apenas relações sustentadas por regras explícitas.

## C01/C02 — Preservar e ingerir

```bash
pensieve-timeline hash examples/first-investigation/hybrid.csv
pensieve-timeline ingest examples/first-investigation/hybrid.csv \
  -o timeline.jsonl --sqlite case.db
```

## H01 — Evidence Graph

```bash
pensieve-timeline entities timeline.jsonl -o entities.jsonl

pensieve-timeline evidence-graph timeline.jsonl entities.jsonl \
  -o evidence-graph.json
```

O grafo mantém dois tipos de nós:

- **event** — ocorrência normalizada da timeline;
- **entity** — valor extraído e normalizado.

E relações diferentes:

- `mentioned_in`;
- `correlated_with`.

**Checkpoint:** encontre um evento e uma entidade que compartilham contexto. Explique por que isso ainda não demonstra causalidade nem controle.

## H02 — Evidence Packet v2

```bash
pensieve-timeline evidence-packet timeline.jsonl \
  --entities entities.jsonl \
  -o evidence-packet.json
```

Inspecione:

- `packet_id`;
- `packet_sha256`;
- `event_digest`;
- política de `raw_excluded`;
- política de `source_path_excluded`.

**Checkpoint:** explique por que uma IA deve receber uma visão limitada e auditável do caso.

## H03 — Qwen opcional

```bash
python -m pip install '.[llm]'

pensieve-timeline reason timeline.jsonl entities.jsonl \
  --packet-output evidence-packet.json \
  -o intelligence.json
```

Revise manualmente cada `evidence_event_ids`.

Compare:

- `reported_confidence`;
- `calibrated_support`.

Nenhum dos dois é “probabilidade de verdade”.

## H04 — Capstone

Entregue uma nota curta contendo:

1. três observações com `event_id`;
2. uma inferência;
3. uma hipótese;
4. uma alternativa;
5. duas incertezas;
6. a próxima coleta que reduziria a maior incerteza.

A qualidade é medida pela rastreabilidade e pelos limites explicitados, não por quão dramática parece a narrativa.
