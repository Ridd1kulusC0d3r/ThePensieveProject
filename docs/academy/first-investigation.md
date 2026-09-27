# First Investigation — roteiro de 45 a 90 minutos

Este laboratório é o ponto de entrada recomendado para o Pensieve.

## O cenário

Você recebeu um conjunto mínimo de registros sintéticos de um host de laboratório. Dependendo da trilha escolhida, o conjunto contém telemetria de host, registros semelhantes a coleta OSINT, ou ambos.

Você **não recebeu uma conclusão**. Seu trabalho é construir uma.

## Escolha

- **DFIR**: foco em tempo, processo, serviço, host e correlação.
- **OSINT**: foco em entidade, normalização e coocorrência.
- **DFIR + OSINT**: foco em fusão de contexto e Evidence Packet v2.

## Regra de avanço

Não avance só porque uma célula ficou verde.

Para cada missão você precisa responder:

1. O que observei?
2. Qual campo ou `event_id` sustenta isso?
3. O que estou inferindo?
4. O que ainda não sei?
5. Qual próxima evidência reduziria essa incerteza?

## Artefatos produzidos

Dependendo da trilha:

```text
workspace/
├── evidence.csv
├── timeline.jsonl
├── case.db
├── correlations.jsonl       # DFIR
├── entities.jsonl           # OSINT / HYBRID
├── entity-graph.json        # OSINT
├── evidence-graph.json      # HYBRID
├── evidence-packet.json     # HYBRID
├── intelligence.json        # Qwen opcional
├── report.html
└── academy-progress.json
```

## Encerramento

O notebook gera `academy-progress.json`, que registra trilha, missões visitadas, hashes e arquivos produzidos. Isso é progresso de laboratório, não certificação de competência.
