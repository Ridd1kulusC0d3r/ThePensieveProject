# The Pensieve Project

**Reconstruir a história, preservar a evidência e deixar explícito onde começa a inferência.**

A v0.3 une três camadas: **DFIR timeline**, **forensic reasoning** e **OSINT evidence layer**.

!!! success "Core leve"
    CSV, TSV, JSONL, SQLite e dashboard HTML funcionam sem dependências externas. EVTX, Registry, Dissect, GLiNER, Qwen, scikit-learn e ForensicArtifacts são extras.

## Contrato epistemológico

```text
Evento != interpretação
Correlação != causalidade
Entidade extraída != identidade verificada
Anomalia != atividade maliciosa
Hipótese != conclusão
```

| Objetivo | Documento |
| --- | --- |
| Entender GLiNER + Qwen | [OSINT híbrido](osint-hybrid.md) |
| Fazer a primeira investigação guiada | [Academy](academy/index.md) |
| Rodar no navegador | [Google Colab](colab.md) |
| Escolher evidências de laboratório | [Datasets](datasets.md) |
| Conferir o que foi testado | [Validação v0.3](validation-v03.md) |
