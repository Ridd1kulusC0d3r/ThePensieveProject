# Trilha DFIR — primeira timeline

Dataset: `examples/first-investigation/dfir.csv`

Objetivo: sair de um CSV pequeno e chegar a uma hipótese forense auditável sem transformar prioridade de triagem em acusação.

## C00 — Orientação

Leia o contrato epistemológico da Academy. Sua primeira regra é simples:

> uma ferramenta ajuda a organizar evidência; ela não toma a decisão investigativa por você.

## C01 — Preservar

```bash
pensieve-timeline doctor
pensieve-timeline hash examples/first-investigation/dfir.csv
```

**Checkpoint:** registre o SHA-256. Explique: hashing demonstra integridade relativa entre cópias comparadas, mas sozinho não demonstra autoria, origem legítima ou cadeia de custódia completa.

## C02 — Timeline

```bash
pensieve-timeline ingest examples/first-investigation/dfir.csv \
  -o timeline.jsonl --sqlite case.db
```

Abra a primeira linha de `timeline.jsonl` e encontre:

- `event_id`
- `timestamp`
- `artifact_type`
- `source`
- `record_locator`
- `parser`
- `time_assumption`

**Checkpoint:** consiga rastrear um `event_id` de volta ao registro original.

## D01 — Triage sem veredito

Compare os `risk_score` dos eventos.

Pergunta: qual evento você examinaria primeiro?

Agora escreva uma explicação benigna plausível para o mesmo evento. Isso força a separar **prioridade de análise** de **maliciosidade**.

## D02 — Correlação temporal

```bash
pensieve-timeline correlate timeline.jsonl \
  -o correlations.jsonl --window 120
```

Escolha uma correlação e identifique os motivos exatos, por exemplo:

- mesmo host;
- mesmo usuário;
- mesmo PID;
- distância temporal.

**Checkpoint:** descreva a correlação sem usar as palavras “causou”, “atacante” ou “malicioso”, a menos que outra evidência suporte isso.

## D03 — Hipótese concorrente

Produza:

- uma **observação** literal;
- uma **inferência** com `event_id`;
- uma **hipótese** com pelo menos dois `event_id`;
- uma **alternativa plausível**;
- a próxima evidência que você coletaria.

Exemplo de estrutura, não de resposta:

```text
Observação:
  [fato literal]

Inferência:
  [interpretação]
  Evidência: event-...

Hipótese:
  [explicação possível]
  Evidência: event-..., event-...

Alternativa:
  [outra explicação]

Próxima pergunta:
  [evidência que reduziria incerteza]
```

Você concluiu a trilha quando consegue defender cada frase apontando para a evidência correspondente.
