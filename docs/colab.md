# Google Colab

O notebook recomendado é:

**`colab/first_investigation.ipynb`**

Ele foi desenhado para uma primeira investigação completa, não apenas para demonstrar comandos.

## Três trilhas

Na célula de configuração:

```python
TRACK = "HYBRID"  # DFIR, OSINT ou HYBRID
```

Cada trilha baixa um dataset sintético pequeno:

- **DFIR** — processo, rede, serviço e logon;
- **OSINT** — e-mail, domínio, handle, IP, hash e CVE;
- **HYBRID** — host telemetry + menções abertas + Evidence Packet v2.

## Caminho padrão em CPU

O notebook instala apenas o core e executa:

```text
C00 escolher trilha
  ↓
C01 doctor + SHA-256
  ↓
C02 ingest + provenance
  ↓
trilha selecionada
  ↓
dashboard
  ↓
capstone
  ↓
academy-progress.json
```

GLiNER e Qwen são opcionais e começam com:

```python
USE_GLINER = False
USE_QWEN = False
```

Isso mantém o notebook leve e permite ensinar primeiro o raciocínio, antes de pedir ao runtime para baixar modelos.

## Artefatos

O workspace gera uma seleção de:

- `timeline.jsonl`
- `case.db`
- `correlations.jsonl`
- `entities.jsonl`
- `entity-graph.json`
- `evidence-graph.json`
- `evidence-packet.json`
- `intelligence.json` quando Qwen é habilitado
- `report.html`
- `academy-progress.json`

Ao final, o notebook empacota o workspace em ZIP.

## Notebook anterior

`colab/pensieve_dfir_osint.ipynb` permanece no repositório como laboratório compacto/legado. O **First Investigation** é o ponto de entrada da Academy.

## Forks

O notebook usa o repositório GitHub como origem. Em um fork, altere a URL de instalação e a constante `BASE` do dataset.
