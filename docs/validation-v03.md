# Validação v0.3

## Core

A suíte não precisa de internet e cobre:

- SHA-256 e preservação de entrada;
- ingestão CSV/JSONL;
- modelo e proveniência;
- correlação explicável;
- SQLite Case DB;
- dashboard;
- extração determinística;
- grafo de coocorrência;
- Evidence Packet sem `raw`;
- Case Engine;
- análise de raridade.

## Cross-platform

`ci.yml` executa o core em Linux, Windows e macOS.

## EVTX real

`integration-evtx.yml` instala `python-evtx`, baixa uma amostra pública de EVTX-ATTACK-SAMPLES e exige ao menos um evento canônico.

## Backends opcionais

Registry, ForensicArtifacts e Dissect possuem smoke jobs de instalação. GLiNER, Qwen e scikit-learn continuam opcionais para manter o core pequeno.

## Limite atual

Passar nos testes significa que estes contratos observáveis funcionaram nos ambientes declarados. Não significa validação pericial independente nem equivalência integral com ferramentas maduras.
