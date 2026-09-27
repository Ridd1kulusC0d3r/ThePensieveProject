# Trilha OSINT — entidades sem identidade imaginária

Dataset: `examples/first-investigation/osint.csv`

Objetivo: transformar texto em entidades auditáveis, normalizar valores e construir um grafo sem converter coocorrência em “vínculo confirmado”.

## C01/C02 — Preservar e ingerir

```bash
pensieve-timeline hash examples/first-investigation/osint.csv
pensieve-timeline ingest examples/first-investigation/osint.csv -o timeline.jsonl
```

## O01 — Extração determinística

```bash
pensieve-timeline entities timeline.jsonl -o entities.jsonl
```

Observe em cada menção:

- texto original;
- `normalized_value`;
- offsets;
- `event_id`;
- `extractor`;
- `confidence_kind`;
- `evidence_hash`.

**Checkpoint:** explique por que `Ops@Example.ORG` e `ops@example.org` podem ser comparados como o mesmo valor normalizado sem que isso confirme quem controla a conta.

## O02 — Grafo

```bash
pensieve-timeline graph entities.jsonl -o entity-graph.json
```

Uma aresta `co_occurrence` significa que dois valores apareceram no mesmo contexto de evidência.

Ela **não demonstra**:

- propriedade;
- amizade;
- autoria;
- identidade;
- comando e controle;
- causalidade.

**Checkpoint:** selecione uma aresta e descreva somente a afirmação mínima sustentada pelo grafo.

## O03 — GLiNER opcional

Somente depois de compreender a camada determinística:

```bash
python -m pip install '.[osint]'
pensieve-timeline entities timeline.jsonl --gliner \
  --labels person organization "phone number" email domain \
  "social media handle" -o entities-gliner.jsonl
```

Compare `extractor` e `corroborated_by`.

O modelo pode sugerir um rótulo, mas o Pensieve exige que o trecho venha de offsets reais da evidência.

**Checkpoint:** explique por que dois extratores concordarem aumenta a auditabilidade da menção, mas não converte a menção em identidade confirmada.
