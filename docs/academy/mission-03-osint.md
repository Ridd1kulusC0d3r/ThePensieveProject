# Missão 3 — Extrair entidades sem inventar vínculos

## Objetivo

Transformar texto já presente nos eventos em entidades auditáveis e aprender por que **menção**, **coocorrência** e **identidade** não são sinônimos.

## 1. Ingerir o laboratório

```bash
pensieve-timeline ingest examples/lab02/hybrid-osint.csv -o timeline.jsonl
```

## 2. Extração determinística

```bash
pensieve-timeline entities timeline.jsonl -o entities.jsonl
```

Confira `event_id`, `text`, `label`, offsets e `extractor`.

## 3. GLiNER opcional

```bash
pip install '.[osint]'
pensieve-timeline entities timeline.jsonl --gliner \
  --labels person organization "phone number" email domain "social media handle" \
  -o entities-gliner.jsonl
```

## 4. Grafo

```bash
pensieve-timeline graph entities.jsonl -o entity-graph.json
```

Uma aresta significa coocorrência em pelo menos um evento. Não significa propriedade, amizade, autoria ou controle.

## 5. Raciocínio

Registre separadamente:

- **Observação**: o que está literalmente presente.
- **Inferência**: interpretação sustentada pelos eventos.
- **Hipótese alternativa**: outra explicação plausível.

A missão termina quando você consegue explicar por que “entidade encontrada”, “entidades correlacionadas” e “mesma pessoa/infraestrutura” são afirmações diferentes.
